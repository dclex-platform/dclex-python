from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from eth_account.messages import encode_defunct
from siwe import SiweMessage
from web3 import Web3
from web3.contract.contract import ContractFunction

from dclex.dclex_client import APIError, AuthorizationError, DclexClient, NotLoggedIn
from dclex.settings import (
    BLOCKCHAIN_FALSE_VALUE,
    CHAIN_ID,
    DIGITAL_IDENTITY_CONTRACT_ABI,
    DIGITAL_IDENTITY_CONTRACT_ADDRESS,
    FACTORY_CONTRACT_ABI,
    FACTORY_CONTRACT_ADDRESS,
    SIWE_DOMAIN,
    SIWE_MESSAGE,
    SIWE_URI,
    USDC_CONTRACT_ABI,
    USDC_CONTRACT_ADDRESS,
    VAULT_CONTRACT_ABI,
    VAULT_CONTRACT_ADDRESS,
)
from dclex.types import (
    AccountStatus,
    ClaimableWithdrawal,
    Order,
    OrderSide,
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


class Dclex:
    def __init__(self, private_key: str, web3_provider_url: str) -> None:
        self._account = Web3().eth.account.from_key(private_key)
        self._web3 = Web3(Web3.HTTPProvider(web3_provider_url))
        self._dclex_client = DclexClient()

    def login(self) -> None:
        nonce = self._dclex_client.get_nonce()
        issued_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        message = SiweMessage(
            {
                "domain": SIWE_DOMAIN,
                "address": self._account.address,
                "statement": SIWE_MESSAGE,
                "uri": SIWE_URI,
                "version": "1",
                "chain_id": CHAIN_ID,
                "nonce": nonce,
                "issued_at": issued_at,
            }
        ).prepare_message()
        signature = self._account.sign_message(
            encode_defunct(text=message),
        ).signature.hex()
        self._dclex_client.login(message=message, signature=signature, nonce=nonce)

    def logged_in(self) -> bool:
        try:
            self.get_account_status()
        except NotLoggedIn:
            return False
        return True

    def logout(self) -> None:
        self._dclex_client.logout()

    def claim_digital_identity(self) -> str:
        account_status = self._dclex_client.get_account_status()
        if account_status == AccountStatus.DID_MINTED:
            raise DigitalIdentityAlreadyClaimed()
        if account_status != AccountStatus.VERIFIED:
            raise AccountNotVerified()

        signature = self._dclex_client.create_digital_identity_signature()

        digital_identity_contract_address = self._web3.to_checksum_address(
            DIGITAL_IDENTITY_CONTRACT_ADDRESS
        )
        digital_identity_contract = self._web3.eth.contract(
            address=digital_identity_contract_address, abi=DIGITAL_IDENTITY_CONTRACT_ABI
        )
        return self._build_and_send_transaction(
            digital_identity_contract.functions.mint(
                {
                    "account": self._account.address,
                    "nonce": int.from_bytes(bytes.fromhex(signature.nonce), "big"),
                    "isPro": BLOCKCHAIN_FALSE_VALUE,
                    "data": bytes.fromhex(signature.nationality),
                },
                bytes.fromhex(signature.signature),
            )
        )

    def get_account_status(self) -> AccountStatus:
        return self._dclex_client.get_account_status()

    def deposit_usdc(self, amount: Decimal) -> str:
        account_status = self._dclex_client.get_account_status()
        if account_status not in [AccountStatus.VERIFIED, AccountStatus.DID_MINTED]:
            raise AccountNotVerified()

        usdc_contract_address = self._web3.to_checksum_address(USDC_CONTRACT_ADDRESS)
        usdc_contract = self._web3.eth.contract(
            address=usdc_contract_address, abi=USDC_CONTRACT_ABI
        )
        return self._build_and_send_transaction(
            usdc_contract.functions.transfer(
                VAULT_CONTRACT_ADDRESS, int(amount * Decimal(10**6))
            )
        )

    def withdraw_usdc(self, amount: Decimal) -> str:
        account_status = self._dclex_client.get_account_status()
        if account_status not in [AccountStatus.VERIFIED, AccountStatus.DID_MINTED]:
            raise AccountNotVerified()

        try:
            withdrawal_id = self._dclex_client.initialize_usdc_withdrawal(amount=amount)
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()
        signature = self._dclex_client.get_withdraw_signature(
            withdrawal_id=withdrawal_id,
        )

        vault_contract_address = self._web3.to_checksum_address(VAULT_CONTRACT_ADDRESS)
        vault_contract = self._web3.eth.contract(
            address=vault_contract_address, abi=VAULT_CONTRACT_ABI
        )
        return self._build_and_send_transaction(
            vault_contract.functions.withdraw(
                {
                    "token": USDC_CONTRACT_ADDRESS,
                    "account": VAULT_CONTRACT_ADDRESS,
                    "to": self._account.address,
                    "amount": int(amount * Decimal(10**6)),
                    "nonce": withdrawal_id,
                },
                bytes.fromhex(signature),
            )
        )

    def deposit_stock_token(self, stock_symbol: str, amount: int) -> str:
        account_status = self._dclex_client.get_account_status()
        if account_status != AccountStatus.DID_MINTED:
            raise AccountNotVerified()

        signature = self._dclex_client.get_deposit_stocks_signature(
            amount=amount,
            symbol=stock_symbol,
        )

        factory_contract_address = self._web3.to_checksum_address(
            FACTORY_CONTRACT_ADDRESS
        )
        factory_contract = self._web3.eth.contract(
            address=factory_contract_address, abi=FACTORY_CONTRACT_ABI
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

    def withdraw_stock_token(self, stock_symbol: str, amount: int) -> str:
        account_status = self._dclex_client.get_account_status()
        if account_status != AccountStatus.DID_MINTED:
            raise AccountNotVerified()

        try:
            withdrawal_id = self._dclex_client.initialize_stock_withdrawal(
                amount=amount,
                asset_type=stock_symbol,
            )
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()
        signature = self._dclex_client.get_withdraw_signature(
            withdrawal_id=withdrawal_id,
        )

        factory_contract_address = self._web3.to_checksum_address(
            FACTORY_CONTRACT_ADDRESS
        )
        factory_contract = self._web3.eth.contract(
            address=factory_contract_address, abi=FACTORY_CONTRACT_ABI
        )
        return self._build_and_send_transaction(
            factory_contract.functions.mintStocks(
                {
                    "symbol": stock_symbol,
                    "amount": int(amount * Decimal(10**18)),
                    "account": self._account.address,
                    "nonce": withdrawal_id,
                },
                bytes.fromhex(signature),
            )
        )

    def pending_transfers(self) -> list[Transfer]:
        return self._dclex_client.get_pending_transfers()

    def closed_transfers(self) -> list[Transfer]:
        return self._dclex_client.get_closed_transfers()

    def get_usdc_available_balance(self) -> Decimal:
        return self._dclex_client.portfolio().available

    def get_usdc_ledger_balance(self) -> Decimal:
        return self._dclex_client.portfolio().funds

    def get_stock_available_balance(self, symbol: str) -> Decimal:
        for stock_item in self._dclex_client.portfolio().positions:
            if stock_item.symbol == symbol:
                return stock_item.total_owned
        return Decimal(0)

    def get_stock_ledger_balance(self, symbol: str) -> Decimal:
        for stock_item in self._dclex_client.portfolio().positions:
            if stock_item.symbol == symbol:
                return stock_item.available_to_sell
        return Decimal(0)

    def portfolio(self) -> Portfolio:
        try:
            return self._dclex_client.portfolio()
        except APIError as exc:
            if exc.error_code == "ACCOUNT_NOT_FOUND":
                raise AccountNotVerified()
            raise

    def claimable_withdrawals(self) -> list[ClaimableWithdrawal]:
        return self._dclex_client.claimable_withdrawals()

    def create_limit_order(
        self,
        side: OrderSide,
        stock_symbol: str,
        amount: int,
        price_limit: Decimal,
        date_of_cancellation: Optional[date] = None,
    ) -> int:
        try:
            return self._dclex_client.create_limit_order(
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

    def create_sell_market_order(self, stock_symbol: str, amount: int) -> int:
        try:
            return self._dclex_client.create_sell_market_order(
                amount=amount,
                asset_type=stock_symbol,
            )
        except APIError as exc:
            if exc.error_code == "INSUFFICIENT_FUNDS":
                raise NotEnoughFunds()
            raise

    def cancel_order(self, order_id: int) -> None:
        return self._dclex_client.cancel_order(order_id)

    def open_orders(self) -> list[Order]:
        return self._dclex_client.open_orders()

    def closed_orders(self) -> list[Order]:
        return self._dclex_client.closed_orders()

    def stocks(self) -> dict[str, Stock]:
        return self._dclex_client.stocks()

    def market_prices(self):
        try:
            return self._dclex_client.market_prices()
        except AuthorizationError:
            raise AccountNotVerified()

    def prices_stream(self):
        prices_stream_access_token = self._dclex_client.prices_stream_access_token()
        return self._dclex_client.prices_stream(prices_stream_access_token)

    def _build_and_send_transaction(self, contract_function: ContractFunction) -> str:
        transaction = contract_function.build_transaction(
            {
                "from": self._account.address,
                "gasPrice": self._web3.eth.gas_price,
                "nonce": self._web3.eth.get_transaction_count(
                    self._web3.to_checksum_address(self._account.address),
                ),
            }
        )
        signed_transaction = self._account.sign_transaction(transaction)
        return self._web3.eth.send_raw_transaction(
            signed_transaction.rawTransaction
        ).hex()
