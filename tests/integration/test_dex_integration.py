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
from primedelta.types import AccountStatus

from .conftest import wait_for_transaction


def _ensure_stock_balance(primedelta_logged_in, symbol: str, fallback_usdc: Decimal) -> None:
    """Buy a small amount of `symbol` if the wallet has none."""
    balance = primedelta_logged_in.get_onchain_stock_balance(symbol)
    if balance > 0:
        return
    primedelta_logged_in.swap_exact_input(
        symbol,
        SwapSide.USDC_TO_STOCK,
        amount_in=fallback_usdc,
        min_amount_out=Decimal("0"),
    )


@pytest.mark.integration
class TestContractsRegistry:
    def test_bundled_dev_config_is_complete(self, primedelta):
        contracts = primedelta._get_contracts()
        assert contracts.chain_id > 0
        assert contracts.core.usdc.address.startswith("0x")
        assert contracts.core.factory.address.startswith("0x")
        assert contracts.core.digital_identity.address.startswith("0x")
        assert contracts.core.dex_router is not None
        assert contracts.core.position_manager is not None
        # Pool ABIs the DEX flow needs:
        for key in ("erc20", "univ3_factory", "dclex_pool", "univ3_pool"):
            assert key in contracts.pool_abis, f"missing pool ABI: {key}"

    def test_get_contracts_returns_same_instance(self, primedelta):
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
        # Ensure the wallet has something to sell — auto-fund via swap.
        _ensure_stock_balance(
            primedelta_logged_in, test_symbol, fallback_usdc=Decimal("2")
        )

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
        # Pool needs the wallet to hold both legs; top up stock side via swap.
        _ensure_stock_balance(
            primedelta_logged_in, test_symbol, fallback_usdc=Decimal("30")
        )

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
