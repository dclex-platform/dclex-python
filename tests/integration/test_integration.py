"""
Integration tests for PrimeDelta SDK.

These tests require a real environment setup:
1. Copy .env.example to .env
2. Fill in PRIMEDELTA_TEST_PRIVATE_KEY and PRIMEDELTA_PROVIDER_URL
3. Ensure the test account is verified and has funds

Run with: uv run pytest tests/integration/ -v
"""

import pytest

from primedelta.types import AccountStatus


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
