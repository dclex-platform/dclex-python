"""Live dex integration tests against a running backend + chain.

Requires:
- PRIMEDELTA_TEST_PRIVATE_KEY: verified + DID-minted account, has gas + USDC + stock
- PRIMEDELTA_PROVIDER_URL, PRIMEDELTA_BASE_URL, PRIMEDELTA_APP_URL set in .env
- /contracts/ endpoint deployed on the target backend
- Pools registered for PRIMEDELTA_TEST_SYMBOL (default AAPL)

Run: uv run pytest tests/integration/test_dex_integration.py -v -m integration
"""
from decimal import Decimal

import pytest

from primedelta import (
    AccountNotVerified,
    PriceFeedAddLiquidity,
    PriceFeedRemoveLiquidity,
    SwapSide,
)
from primedelta.contracts import Contracts
from primedelta.types import AccountStatus

from .conftest import wait_for_transaction


def _skip_if_no_stock(primedelta_logged_in, symbol: str) -> None:
    """Skip when the test account has no on-chain balance of `symbol`."""
    contracts = primedelta_logged_in._get_contracts()
    pool_info = contracts.pools.get(symbol)
    if pool_info is None:
        pytest.skip(f"Pool info missing for {symbol}")
    stock_addr = primedelta_logged_in._web3.to_checksum_address(
        pool_info.stock_token_address
    )
    erc20 = primedelta_logged_in._web3.eth.contract(
        address=stock_addr,
        abi=[
            {
                "name": "balanceOf",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "owner", "type": "address"}],
                "outputs": [{"name": "", "type": "uint256"}],
            }
        ],
    )
    balance = erc20.functions.balanceOf(
        primedelta_logged_in._account.address
    ).call()
    if balance == 0:
        pytest.skip(f"Test account has no {symbol} balance — fund it to run this test")


@pytest.mark.integration
class TestContractsEndpoint:
    def test_contracts_payload_parses(self, primedelta):
        payload = primedelta._primedelta_client.get_contracts()
        contracts = Contracts.from_dict(payload)
        assert contracts.chain_id > 0
        assert contracts.core.usdc.address.startswith("0x")
        assert contracts.core.factory.address.startswith("0x")
        assert contracts.core.digital_identity.address.startswith("0x")
        # Router and NPM are optional but should be present once deployed
        if contracts.core.dex_router is not None:
            assert contracts.core.dex_router.address.startswith("0x")

    def test_lazy_load_caches(self, primedelta):
        first = primedelta._get_contracts()
        second = primedelta._get_contracts()
        assert first is second


@pytest.mark.integration
class TestVerificationFlow:
    def test_verification_url_returns_app_url(self, primedelta):
        url = primedelta.verification_url()
        assert url.startswith(("http://", "https://"))

    def test_account_status_for_verified_test_account(self, primedelta_logged_in):
        status = primedelta_logged_in.get_account_status()
        assert status == AccountStatus.DID_MINTED, (
            f"Test account must be DID_MINTED, got {status}. "
            "Verify and mint DID via the web app, then retry."
        )


@pytest.mark.integration
class TestDIDRequiredErrors:
    """Verify DID-gated actions raise AccountNotVerified for non-verified accounts."""

    def test_swap_raises_without_did(self, unverified_primedelta_logged_in, test_symbol):
        with pytest.raises(AccountNotVerified):
            unverified_primedelta_logged_in.swap_exact_input(
                test_symbol,
                SwapSide.USDC_TO_STOCK,
                amount_in=Decimal("1"),
                min_amount_out=Decimal("0"),
            )

    def test_add_liquidity_raises_without_did(
        self, unverified_primedelta_logged_in, test_symbol
    ):
        with pytest.raises(AccountNotVerified):
            unverified_primedelta_logged_in.add_liquidity(
                PriceFeedAddLiquidity(
                    symbol=test_symbol,
                    liquidity_amount=Decimal("1"),
                    max_stock_amount=Decimal("1"),
                    max_usdc_amount=Decimal("100"),
                )
            )

    def test_collect_fees_raises_without_did(self, unverified_primedelta_logged_in):
        with pytest.raises(AccountNotVerified):
            unverified_primedelta_logged_in.collect_fees(1)


@pytest.mark.integration
@pytest.mark.dex
class TestSwapLive:
    """Real on-chain swap via DclexRouter. Tiny amounts, won't move the market."""

    def test_buy_small_amount_of_stock(
        self, primedelta_logged_in, test_symbol, provider_url
    ):
        contracts = primedelta_logged_in._get_contracts()
        if contracts.core.dex_router is None:
            pytest.skip("DCLEX router not deployed on target backend")
        if test_symbol not in contracts.pools:
            pytest.skip(f"Pool not registered for {test_symbol}")

        tx_hash = primedelta_logged_in.swap_exact_input(
            test_symbol,
            SwapSide.USDC_TO_STOCK,
            amount_in=Decimal("1"),  # 1 USDC
            min_amount_out=Decimal("0"),  # accept any output for the test
        )
        assert tx_hash.startswith("0x")
        wait_for_transaction(tx_hash, provider_url)

    def test_sell_small_amount_of_stock(
        self, primedelta_logged_in, test_symbol, provider_url
    ):
        contracts = primedelta_logged_in._get_contracts()
        if contracts.core.dex_router is None:
            pytest.skip("DCLEX router not deployed on target backend")
        if test_symbol not in contracts.pools:
            pytest.skip(f"Pool not registered for {test_symbol}")
        _skip_if_no_stock(primedelta_logged_in, test_symbol)

        tx_hash = primedelta_logged_in.swap_exact_input(
            test_symbol,
            SwapSide.STOCK_TO_USDC,
            amount_in=Decimal("0.001"),  # tiny stock fraction
            min_amount_out=Decimal("0"),
        )
        assert tx_hash.startswith("0x")
        wait_for_transaction(tx_hash, provider_url)


@pytest.mark.integration
@pytest.mark.dex
class TestLiquidityLive:
    """Add liquidity then remove what was added — round-trip."""

    def test_add_then_remove_pricefeed_liquidity(
        self, primedelta_logged_in, test_symbol, provider_url
    ):
        contracts = primedelta_logged_in._get_contracts()
        if contracts.core.dex_router is None:
            pytest.skip("DCLEX router not deployed on target backend")
        if test_symbol not in contracts.pools:
            pytest.skip(f"Pool not registered for {test_symbol}")
        _skip_if_no_stock(primedelta_logged_in, test_symbol)

        liquidity_amount = Decimal(10**15)  # 0.001 LP shares (assuming 18-dec)

        add_tx = primedelta_logged_in.add_liquidity(
            PriceFeedAddLiquidity(
                symbol=test_symbol,
                liquidity_amount=liquidity_amount,
                max_stock_amount=Decimal("1"),
                max_usdc_amount=Decimal("1000"),
            )
        )
        assert add_tx.startswith("0x")
        wait_for_transaction(add_tx, provider_url)

        remove_tx = primedelta_logged_in.remove_liquidity(
            PriceFeedRemoveLiquidity(
                symbol=test_symbol,
                liquidity_amount=liquidity_amount,
            )
        )
        assert remove_tx.startswith("0x")
        wait_for_transaction(remove_tx, provider_url)
