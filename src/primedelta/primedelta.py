from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from eth_account.messages import encode_defunct
from siwe import SiweMessage
from web3 import Web3
from web3.contract.contract import ContractFunction

from primedelta.contracts import Contracts
from primedelta.dex.handlers import (
    _AMMPoolHandler,
    _DclexPoolHandler,
    _RouterSwapHandler,
)
from primedelta.dex.params import (
    AddLiquidityParams,
    AMMAddLiquidity,
    AMMRemoveLiquidity,
    PoolType,
    PriceFeedAddLiquidity,
    PriceFeedRemoveLiquidity,
    RemoveLiquidityParams,
    SwapSide,
)
from primedelta.primedelta_client import APIError, PrimeDeltaClient, NotLoggedIn
from primedelta.settings import (
    PRIMEDELTA_APP_URL,
    SIWE_DOMAIN,
    SIWE_MESSAGE,
    SIWE_URI,
)
from primedelta.types import (
    AccountStatus,
    ClaimableWithdrawal,
    Distribution,
    Order,
    OrderSide,
    OrderStatus,
    Portfolio,
    Stock,
    Transfer,
)


class NotEnoughFunds(Exception):
    pass


class AccountNotVerified(Exception):
    pass


class DigitalIdentityAlreadyClaimed(Exception):
    pass


class WithdrawalNotFound(Exception):
    pass


class PrimeDelta:
    def __init__(self, private_key: str, web3_provider_url: str) -> None:
        self._account = Web3().eth.account.from_key(private_key)
        self._web3 = Web3(Web3.HTTPProvider(web3_provider_url))
        self._primedelta_client = PrimeDeltaClient()
        self._contracts: Optional[Contracts] = None
        self._dclex_handler = _DclexPoolHandler(
            web3=self._web3,
            account=self._account,
            contracts_provider=self._get_contracts,
            send_tx=self._build_and_send_transaction,
        )
        self._amm_handler = _AMMPoolHandler(
            web3=self._web3,
            account=self._account,
            contracts_provider=self._get_contracts,
            send_tx=self._build_and_send_transaction,
        )
        self._router_swapper = _RouterSwapHandler(
            web3=self._web3,
            account=self._account,
            contracts_provider=self._get_contracts,
            signed_prices_fetcher=self._primedelta_client.get_signed_price_updates,
            send_tx=self._build_and_send_transaction,
        )

    def _get_contracts(self) -> Contracts:
        if self._contracts is None:
            self._contracts = Contracts.from_dict(
                self._primedelta_client.get_contracts()
            )
        return self._contracts

    def login(self) -> None:
        nonce = self._primedelta_client.get_nonce()
        issued_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        message = SiweMessage(
            {
                "domain": SIWE_DOMAIN,
                "address": self._account.address,
                "statement": SIWE_MESSAGE,
                "uri": SIWE_URI,
                "version": "1",
                "chain_id": self._get_contracts().chain_id,
                "nonce": nonce,
                "issued_at": issued_at,
            }
        ).prepare_message()
        signature = self._account.sign_message(
            encode_defunct(text=message),
        ).signature.hex()
        self._primedelta_client.login(message=message, signature=signature, nonce=nonce)

    def logged_in(self) -> bool:
        try:
            self.get_account_status()
        except NotLoggedIn:
            return False
        return True

    def logout(self) -> None:
        self._primedelta_client.logout()

    def claim_digital_identity(self) -> str:
        account_status = self._primedelta_client.get_account_status()
        if account_status == AccountStatus.DID_MINTED:
            raise DigitalIdentityAlreadyClaimed()
        if account_status != AccountStatus.VERIFIED:
            raise AccountNotVerified()

        signature = self._primedelta_client.create_digital_identity_signature()

        digital_identity = self._get_contracts().core.digital_identity
        digital_identity_contract_address = self._web3.to_checksum_address(
            digital_identity.address
        )
        digital_identity_contract = self._web3.eth.contract(
            address=digital_identity_contract_address, abi=digital_identity.abi
        )
        return self._build_and_send_transaction(
            digital_identity_contract.functions.mint(
                {
                    "account": self._account.address,
                    "nonce": int.from_bytes(bytes.fromhex(signature.nonce), "big"),
                    "isPro": signature.is_pro,
                    "data": bytes.fromhex(signature.data),
                },
                bytes.fromhex(signature.signature),
            )
        )

    def get_account_status(self) -> AccountStatus:
        return self._primedelta_client.get_account_status()

    def verification_url(self) -> str:
        """Return the URL of the web page where the user completes KYC.

        Verification (uploading ID, taking a selfie, etc.) is performed in the
        web app, not via the SDK. After verification completes there, the
        backend marks the account as VERIFIED and the SDK can call
        `claim_digital_identity()` to mint the on-chain DID NFT.
        """
        return PRIMEDELTA_APP_URL

    def open_verification_page(self) -> str:
        """Open the verification web page in the user's default browser.

        Returns the URL that was opened, so callers can fall back to printing
        it if `webbrowser.open` returned False (headless environments).
        """
        import webbrowser

        url = self.verification_url()
        webbrowser.open(url)
        return url

    def deposit_usdc(self, amount: Decimal) -> str:
        account_status = self._primedelta_client.get_account_status()
        if account_status not in [AccountStatus.VERIFIED, AccountStatus.DID_MINTED]:
            raise AccountNotVerified()

        contracts = self._get_contracts()
        usdc_contract_address = self._web3.to_checksum_address(contracts.core.usdc.address)
        usdc_contract = self._web3.eth.contract(
            address=usdc_contract_address, abi=contracts.core.usdc.abi
        )
        return self._build_and_send_transaction(
            usdc_contract.functions.transfer(
                contracts.core.vault.address, int(amount * Decimal(10**6))
            )
        )

    def request_usdc_withdrawal(self, amount: Decimal):
        account_status = self._primedelta_client.get_account_status()
        if account_status not in [AccountStatus.VERIFIED, AccountStatus.DID_MINTED]:
            raise AccountNotVerified()

        try:
            return self._primedelta_client.request_usdc_withdrawal(amount=amount)
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()

    def claim_usdc_withdrawal(self, withdrawal_id: int) -> str:
        withdrawal = self._get_claimable_withdrawal(withdrawal_id)
        signature = self._primedelta_client.get_withdraw_signature(
            withdrawal_id=withdrawal_id,
        )

        contracts = self._get_contracts()
        vault_contract_address = self._web3.to_checksum_address(contracts.core.vault.address)
        vault_contract = self._web3.eth.contract(
            address=vault_contract_address, abi=contracts.core.vault.abi
        )
        return self._build_and_send_transaction(
            vault_contract.functions.withdraw(
                {
                    "token": contracts.core.usdc.address,
                    "account": contracts.core.vault.address,
                    "to": self._account.address,
                    "amount": int(withdrawal.amount * Decimal(10**6)),
                    "nonce": withdrawal_id,
                },
                bytes.fromhex(signature),
            )
        )

    def deposit_stock_token(self, stock_symbol: str, amount: int) -> str:
        account_status = self._primedelta_client.get_account_status()
        if account_status != AccountStatus.DID_MINTED:
            raise AccountNotVerified()

        signature = self._primedelta_client.get_deposit_stocks_signature(
            amount=amount,
            symbol=stock_symbol,
        )

        factory = self._get_contracts().core.factory
        factory_contract_address = self._web3.to_checksum_address(factory.address)
        factory_contract = self._web3.eth.contract(
            address=factory_contract_address, abi=factory.abi
        )
        return self._build_and_send_transaction(
            factory_contract.functions.burnStocks(
                {
                    "symbol": stock_symbol,
                    "amount": int(amount * Decimal(10**18)),
                    "account": self._account.address,
                    "nonce": int.from_bytes(bytes.fromhex(signature.nonce[2:]), "big"),
                },
                bytes.fromhex(signature.signature),
            )
        )

    def request_stock_withdrawal(self, stock_symbol: str, amount: int):
        account_status = self._primedelta_client.get_account_status()
        if account_status != AccountStatus.DID_MINTED:
            raise AccountNotVerified()

        try:
            return self._primedelta_client.request_stock_withdrawal(
                amount=amount,
                asset_type=stock_symbol,
            )
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()

    def claim_stock_withdrawal(self, withdrawal_id: int) -> str:
        withdrawal = self._get_claimable_withdrawal(withdrawal_id)
        signature = self._primedelta_client.get_withdraw_signature(
            withdrawal_id=withdrawal_id,
        )

        factory = self._get_contracts().core.factory
        factory_contract_address = self._web3.to_checksum_address(factory.address)
        factory_contract = self._web3.eth.contract(
            address=factory_contract_address, abi=factory.abi
        )
        return self._build_and_send_transaction(
            factory_contract.functions.mintStocks(
                {
                    "symbol": withdrawal.asset_type,
                    "amount": int(withdrawal.amount * Decimal(10**18)),
                    "account": self._account.address,
                    "nonce": withdrawal_id,
                },
                bytes.fromhex(signature),
            )
        )

    def _get_claimable_withdrawal(self, withdrawal_id: int) -> ClaimableWithdrawal:
        claimable_withdrawals = self._primedelta_client.claimable_withdrawals()
        matching_withdrawals = [
            withdrawal
            for withdrawal in claimable_withdrawals
            if withdrawal.withdrawal_id == withdrawal_id
        ]
        if len(matching_withdrawals) == 0:
            raise WithdrawalNotFound()
        if len(matching_withdrawals) > 1:
            raise RuntimeError(
                "Received multiple claimable withdrawals with the same id"
            )
        return matching_withdrawals[0]

    def pending_transfers(
        self, page_number: int = 1, page_size: int = 1000
    ) -> list[Transfer]:
        return self._primedelta_client.get_pending_transfers(page_number, page_size)

    def closed_transfers(
        self, page_number: int = 1, page_size: int = 1000
    ) -> list[Transfer]:
        return self._primedelta_client.get_closed_transfers(page_number, page_size)

    def distributions(
        self, page_number: int = 1, page_size: int = 1000
    ) -> list[Distribution]:
        return self._primedelta_client.get_distributions(page_number, page_size)

    def get_usdc_available_balance(self) -> Decimal:
        return self._primedelta_client.portfolio().buying_power

    def get_usdc_total_balance(self) -> Decimal:
        return self._primedelta_client.portfolio().total_funds

    def get_stock_available_balance(self, symbol: str) -> Decimal:
        for stock_item in self._primedelta_client.portfolio().positions:
            if stock_item.symbol == symbol:
                return stock_item.total_owned
        return Decimal(0)

    def get_stock_total_balance(self, symbol: str) -> Decimal:
        for stock_item in self._primedelta_client.portfolio().positions:
            if stock_item.symbol == symbol:
                return stock_item.available_to_sell
        return Decimal(0)

    def portfolio(self) -> Portfolio:
        try:
            return self._primedelta_client.portfolio()
        except APIError as exc:
            if exc.error_code == "ACCOUNT_NOT_FOUND":
                raise AccountNotVerified()
            raise

    def claimable_withdrawals(self) -> list[ClaimableWithdrawal]:
        return self._primedelta_client.claimable_withdrawals()

    def send_limit_order(
        self,
        side: OrderSide,
        stock_symbol: str,
        amount: int,
        price_limit: Decimal,
        date_of_cancellation: Optional[date] = None,
    ) -> int:
        try:
            return self._primedelta_client.send_limit_order(
                amount=amount,
                asset_type=stock_symbol,
                order_side=side,
                price_limit=price_limit,
                date_of_cancellation=date_of_cancellation,
            )
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()
            raise

    def send_sell_market_order(self, stock_symbol: str, amount: int) -> int:
        try:
            return self._primedelta_client.send_sell_market_order(
                amount=amount,
                asset_type=stock_symbol,
            )
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()
            raise

    def cancel_order(self, order_id: int) -> None:
        return self._primedelta_client.cancel_order(order_id)

    def get_order_status(self, order_id: int) -> OrderStatus:
        return self._primedelta_client.get_order_status(order_id)

    def open_orders(self, page_number: int = 1, page_size: int = 1000) -> list[Order]:
        return self._primedelta_client.open_orders(page_number, page_size)

    def closed_orders(self, page_number: int = 1, page_size: int = 1000) -> list[Order]:
        return self._primedelta_client.closed_orders(page_number, page_size)

    def stocks(self) -> dict[str, Stock]:
        return self._primedelta_client.stocks()

    def prices_stream(self, symbols: Optional[list[str]] = None):
        """Stream real-time price updates.

        When logged in, uses the broker's authenticated price stream.
        When not logged in, uses Pyth Hermes API for public price feeds.

        Args:
            symbols: List of stock symbols to stream prices for.
                     Only used when not logged in (Pyth stream).
                     If None, streams all available stocks.

        Raises:
            AccountNotVerified: If logged in but account is not verified.
                                Use pyth_prices_stream() or verify at https://app.primedelta.io
        """
        if self.logged_in():
            account_status = self._primedelta_client.get_account_status()
            if account_status not in [AccountStatus.VERIFIED, AccountStatus.DID_MINTED]:
                raise AccountNotVerified(
                    "Account not verified. Use pyth_prices_stream() for public prices "
                    "or verify your account at https://app.primedelta.io"
                )
            prices_stream_access_token = self._primedelta_client.prices_stream_access_token()
            return self._primedelta_client.prices_stream(prices_stream_access_token)
        else:
            if symbols is None:
                symbols = list(self.stocks().keys())
            return self._primedelta_client.pyth_prices_stream(symbols)

    def pyth_prices_stream(self, symbols: Optional[list[str]] = None):
        """Stream prices from Pyth Hermes API.

        This method does not require authentication and can be used when not logged in.

        Args:
            symbols: List of stock symbols to stream prices for.
                     If None, streams all available stocks.
        """
        if symbols is None:
            symbols = list(self.stocks().keys())
        return self._primedelta_client.pyth_prices_stream(symbols)

    def swap_exact_input(
        self,
        symbol: str,
        side: SwapSide,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline_seconds: int = 600,
        pyth_value: int = 0,
    ) -> str:
        self._require_logged_in_and_did_minted()
        return self._router_swapper.swap_exact_input(
            symbol, side, amount_in, min_amount_out, deadline_seconds, pyth_value
        )

    def swap_exact_output(
        self,
        symbol: str,
        side: SwapSide,
        amount_out: Decimal,
        max_amount_in: Decimal,
        deadline_seconds: int = 600,
        pyth_value: int = 0,
    ) -> str:
        self._require_logged_in_and_did_minted()
        return self._router_swapper.swap_exact_output(
            symbol, side, amount_out, max_amount_in, deadline_seconds, pyth_value
        )

    def add_liquidity(self, params: AddLiquidityParams) -> str:
        self._require_logged_in_and_did_minted()
        return self._handler_for(params.pool_type).add_liquidity(params)

    def remove_liquidity(self, params: RemoveLiquidityParams) -> str:
        return self._handler_for(params.pool_type).remove_liquidity(params)

    def collect_fees(self, position_id: int) -> str:
        self._require_logged_in_and_did_minted()
        return self._amm_handler.collect_fees(position_id)

    def _handler_for(self, pool_type: PoolType):
        if pool_type == PoolType.PRICE_FEED:
            return self._dclex_handler
        if pool_type == PoolType.AMM:
            return self._amm_handler
        raise ValueError(f"Unknown pool type: {pool_type}")

    def _require_logged_in_and_did_minted(self) -> None:
        account_status = self._primedelta_client.get_account_status()
        if account_status != AccountStatus.DID_MINTED:
            raise AccountNotVerified()

    def _build_and_send_transaction(
        self, contract_function: ContractFunction, value: int = 0
    ) -> str:
        transaction = contract_function.build_transaction(
            {
                "from": self._account.address,
                "gasPrice": self._web3.eth.gas_price,
                "nonce": self._web3.eth.get_transaction_count(
                    self._web3.to_checksum_address(self._account.address),
                ),
                "value": value,
            }
        )
        signed_transaction = self._account.sign_transaction(transaction)
        return self._web3.eth.send_raw_transaction(
            signed_transaction.rawTransaction
        ).hex()

    def is_market_open(self) -> bool:
        return self._primedelta_client.is_market_open()
