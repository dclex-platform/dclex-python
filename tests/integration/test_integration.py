"""
Integration tests for PrimeDelta SDK.

These tests require a real environment setup:
1. Copy .env.example to .env
2. Fill in PRIMEDELTA_TEST_PRIVATE_KEY and PRIMEDELTA_PROVIDER_URL
3. Ensure the test account is verified and has funds

Run with: uv run pytest tests/integration/ -v
"""
from decimal import Decimal

import pytest

from primedelta import SwapSide
from primedelta.types import AccountStatus

from .conftest import wait_for_condition, wait_for_transaction


@pytest.mark.integration
class TestLoginIntegration:
    def test_login_and_logout(self, primedelta):
        assert not primedelta.logged_in()

        primedelta.login()
        assert primedelta.logged_in()

        primedelta.logout()
        assert not primedelta.logged_in()

    def test_get_account_status(self, primedelta_logged_in):
        status = primedelta_logged_in.get_account_status()
        assert status in [
            AccountStatus.NOT_VERIFIED,
            AccountStatus.VERIFIED,
            AccountStatus.DID_MINTED,
        ]


@pytest.mark.integration
class TestPortfolioIntegration:
    def test_get_portfolio(self, primedelta_logged_in):
        portfolio = primedelta_logged_in.portfolio()
        assert portfolio.buying_power is not None
        assert portfolio.total_equity is not None


@pytest.mark.integration
class TestStocksIntegration:
    def test_get_stocks(self, primedelta_logged_in):
        stocks = primedelta_logged_in.stocks()
        assert len(stocks) > 0
        assert "AAPL" in stocks or len(stocks) > 0  # At least some stocks available


@pytest.mark.integration
class TestOrdersIntegration:
    def test_get_open_orders(self, primedelta_logged_in):
        orders = primedelta_logged_in.open_orders()
        assert isinstance(orders, list)

    def test_get_closed_orders(self, primedelta_logged_in):
        orders = primedelta_logged_in.closed_orders()
        assert isinstance(orders, list)

    def test_is_market_open(self, primedelta):
        # This doesn't require login
        result = primedelta.is_market_open()
        assert isinstance(result, bool)


@pytest.mark.integration
class TestOrderPlacementIntegration:
    """Tests for order placement and cancellation.

    These tests place real orders but use unrealistic prices
    to ensure they won't execute.
    """

    def test_place_and_cancel_limit_buy_order(self, primedelta_logged_in):
        """Place a limit buy order at a very low price, then cancel it."""
        import time
        from decimal import Decimal
        from primedelta.types import OrderSide, OrderStatus

        # Place limit buy at $1 (unrealistically low, won't execute)
        order_id = primedelta_logged_in.send_limit_order(
            side=OrderSide.BUY,
            stock_symbol="AAPL",
            amount=1,
            price_limit=Decimal("1.00"),
        )

        assert order_id is not None
        assert isinstance(order_id, int)

        # Check order status is pending
        status = primedelta_logged_in.get_order_status(order_id)
        assert status == OrderStatus.PENDING

        # Cancel the order
        primedelta_logged_in.cancel_order(order_id)

        # Wait for cancellation to process and verify — backend can take
        # several seconds to flip the order's state on dev.
        for _ in range(60):
            time.sleep(0.5)
            status = primedelta_logged_in.get_order_status(order_id)
            if status == OrderStatus.CANCELED:
                break

        assert status == OrderStatus.CANCELED, (
            f"order {order_id} did not reach CANCELED within 30s, last status={status}"
        )


@pytest.mark.integration
class TestTransfersIntegration:
    def test_get_pending_transfers(self, primedelta_logged_in):
        transfers = primedelta_logged_in.pending_transfers()
        assert isinstance(transfers, list)

    def test_get_closed_transfers(self, primedelta_logged_in):
        transfers = primedelta_logged_in.closed_transfers()
        assert isinstance(transfers, list)

    def test_get_claimable_withdrawals(self, primedelta_logged_in):
        withdrawals = primedelta_logged_in.claimable_withdrawals()
        assert isinstance(withdrawals, list)


@pytest.mark.integration
class TestStablecoinLifecycle:
    """End-to-end stablecoin deposit -> request withdrawal -> claim, with
    assertions that the backend indexer + on-chain state both reflect each step.

    Reproduces the scenario Copilot flagged as missing in the mock-heavy unit
    suite: real transfer round-trip with state-transition checks.
    """

    def test_deposit_then_claim_round_trip(self, primedelta_logged_in, provider_url):
        amount = Decimal("1")  # 1 unit — tiny, won't move anything meaningful

        wallet_before = primedelta_logged_in.get_onchain_stablecoin_balance()
        backend_before = primedelta_logged_in.get_stablecoin_total_balance()

        deposit_tx = primedelta_logged_in.deposit_stablecoin(amount)
        assert deposit_tx.startswith("0x")
        wait_for_transaction(deposit_tx, provider_url)

        # On-chain: wallet's stablecoin dropped by `amount` after the deposit mined.
        wallet_after_deposit = primedelta_logged_in.get_onchain_stablecoin_balance()
        assert wallet_before - wallet_after_deposit >= amount - Decimal("0.000001"), (
            f"wallet stablecoin didn't drop by {amount}: "
            f"before={wallet_before}, after={wallet_after_deposit}"
        )

        # Backend: indexer eventually credits the deposit.
        wait_for_condition(
            lambda: primedelta_logged_in.get_stablecoin_total_balance() >= backend_before
            + amount
            - Decimal("0.01"),
            f"backend stablecoin balance to reflect +{amount} deposit",
            timeout_s=60,
        )

        withdrawal_id = primedelta_logged_in.request_stablecoin_withdrawal(amount)
        assert isinstance(withdrawal_id, int)

        # Backend marks withdrawal claimable after its worker processes it.
        wait_for_condition(
            lambda: any(
                w.withdrawal_id == withdrawal_id
                for w in primedelta_logged_in.claimable_withdrawals()
            ),
            f"withdrawal {withdrawal_id} to appear in claimable_withdrawals()",
            timeout_s=120,
        )

        claim_tx = primedelta_logged_in.claim_stablecoin_withdrawal(withdrawal_id)
        assert claim_tx.startswith("0x")
        wait_for_transaction(claim_tx, provider_url)

        # On-chain: wallet's stablecoin came back (modulo tx gas in native,
        # stablecoin is whole; should equal pre-deposit ± rounding).
        wallet_after_claim = primedelta_logged_in.get_onchain_stablecoin_balance()
        assert wallet_after_claim >= wallet_before - Decimal("0.000001"), (
            f"wallet stablecoin didn't return after claim: "
            f"before={wallet_before}, after_claim={wallet_after_claim}"
        )


@pytest.mark.integration
class TestStockLifecycle:
    """Stock-token deposit -> request withdrawal -> claim round-trip. Pre-funds
    the wallet via DEX swap so the test is self-contained.
    """

    SYMBOL = "AAPL"
    DEPOSIT_AMOUNT = 1  # whole stock-token units (deposit_stock_token takes int)

    def _ensure_stock_units(self, primedelta_logged_in, units: int) -> None:
        balance = primedelta_logged_in.get_onchain_stock_balance(self.SYMBOL)
        if balance >= units:
            return
        # Buy enough to cover with comfortable headroom (AAPL ~ $300, so 5
        # units ~ 0.016 AAPL — for `units >= 1` we need a sizeable buy).
        primedelta_logged_in.swap_exact_input(
            self.SYMBOL,
            SwapSide.STABLECOIN_TO_STOCK,
            amount_in=Decimal(units * 400),  # ~price * units + slack
            min_amount_out=Decimal("0"),
        )

    def test_deposit_then_claim_round_trip(self, primedelta_logged_in, provider_url):
        self._ensure_stock_units(primedelta_logged_in, self.DEPOSIT_AMOUNT)

        wallet_before = primedelta_logged_in.get_onchain_stock_balance(self.SYMBOL)
        backend_before = primedelta_logged_in.get_stock_total_balance(self.SYMBOL)

        deposit_tx = primedelta_logged_in.deposit_stock_token(
            self.SYMBOL, self.DEPOSIT_AMOUNT
        )
        assert deposit_tx.startswith("0x")
        wait_for_transaction(deposit_tx, provider_url)

        # On-chain: stock balance dropped by the deposited unit count.
        wallet_after_deposit = primedelta_logged_in.get_onchain_stock_balance(self.SYMBOL)
        assert wallet_before - wallet_after_deposit >= Decimal(self.DEPOSIT_AMOUNT) - Decimal(
            "0.000001"
        ), (
            f"{self.SYMBOL} wallet balance didn't drop by {self.DEPOSIT_AMOUNT}: "
            f"before={wallet_before}, after={wallet_after_deposit}"
        )

        # Backend: indexer credits the deposit on the user's position.
        wait_for_condition(
            lambda: primedelta_logged_in.get_stock_total_balance(self.SYMBOL)
            >= backend_before + Decimal(self.DEPOSIT_AMOUNT) - Decimal("0.000001"),
            f"backend {self.SYMBOL} position to reflect +{self.DEPOSIT_AMOUNT}",
            timeout_s=60,
        )

        withdrawal_id = primedelta_logged_in.request_stock_withdrawal(
            self.SYMBOL, self.DEPOSIT_AMOUNT
        )
        assert isinstance(withdrawal_id, int)

        wait_for_condition(
            lambda: any(
                w.withdrawal_id == withdrawal_id
                for w in primedelta_logged_in.claimable_withdrawals()
            ),
            f"stock withdrawal {withdrawal_id} to appear in claimable_withdrawals()",
            timeout_s=120,
        )

        claim_tx = primedelta_logged_in.claim_stock_withdrawal(withdrawal_id)
        assert claim_tx.startswith("0x")
        wait_for_transaction(claim_tx, provider_url)

        wallet_after_claim = primedelta_logged_in.get_onchain_stock_balance(self.SYMBOL)
        assert wallet_after_claim >= wallet_before - Decimal("0.000001"), (
            f"{self.SYMBOL} wallet balance didn't return after claim: "
            f"before={wallet_before}, after_claim={wallet_after_claim}"
        )


@pytest.mark.integration
class TestPriceStreamingIntegration:
    def test_pyth_prices_stream_when_not_logged_in(self, primedelta):
        """Pyth stream works without login."""
        from decimal import Decimal
        from primedelta.types import Price

        assert not primedelta.logged_in()

        stream = primedelta.pyth_prices_stream(["AAPL"])
        price = next(stream)

        assert isinstance(price, Price)
        assert price.symbol == "AAPL"
        assert isinstance(price.last_price, Decimal)
        assert price.last_price > 0

    def test_prices_stream_uses_pyth_when_not_logged_in(self, primedelta):
        """prices_stream() auto-switches to Pyth when not logged in."""
        from decimal import Decimal
        from primedelta.types import Price

        assert not primedelta.logged_in()

        stream = primedelta.prices_stream(["AAPL"])
        price = next(stream)

        assert isinstance(price, Price)
        assert price.symbol == "AAPL"
        assert isinstance(price.last_price, Decimal)
        assert price.last_price > 0

    def test_prices_stream_uses_broker_when_logged_in(self, primedelta_logged_in):
        """prices_stream() uses broker API when logged in."""
        from decimal import Decimal
        from primedelta.types import Price

        assert primedelta_logged_in.logged_in()

        stream = primedelta_logged_in.prices_stream()
        price = next(stream)

        assert isinstance(price, Price)
        assert isinstance(price.symbol, str)
        assert isinstance(price.last_price, Decimal)
        assert price.last_price > 0
