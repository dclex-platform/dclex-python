from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from primedelta import PrimeDelta
from primedelta.primedelta import NotEnoughFunds
from primedelta.primedelta_client import APIError
from primedelta.types import Order, OrderSide, OrderStatus


class TestLimitOrders:
    def test_send_buy_limit_order(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "send_limit_order",
            return_value=123,
        ) as mock_send:
            order_id = primedelta.send_limit_order(
                OrderSide.BUY, "AAPL", 10, Decimal("150.00")
            )

        assert order_id == 123
        mock_send.assert_called_once_with(
            amount=10,
            asset_type="AAPL",
            order_side=OrderSide.BUY,
            price_limit=Decimal("150.00"),
            date_of_cancellation=None,
        )

    def test_send_sell_limit_order_with_cancellation_date(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        cancellation_date = date.today() + timedelta(days=10)

        with patch.object(
            primedelta._primedelta_client,
            "send_limit_order",
            return_value=456,
        ) as mock_send:
            order_id = primedelta.send_limit_order(
                OrderSide.SELL, "AAPL", 5, Decimal("160.00"), cancellation_date
            )

        assert order_id == 456
        mock_send.assert_called_once_with(
            amount=5,
            asset_type="AAPL",
            order_side=OrderSide.SELL,
            price_limit=Decimal("160.00"),
            date_of_cancellation=cancellation_date,
        )

    def test_send_limit_order_raises_when_not_enough_funds(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "send_limit_order",
            side_effect=APIError("INSUFFICIENT_FUNDS"),
        ):
            with pytest.raises(NotEnoughFunds):
                primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1000, Decimal("200.00"))


class TestMarketOrders:
    def test_send_sell_market_order(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "send_sell_market_order",
            return_value=789,
        ) as mock_send:
            order_id = primedelta.send_sell_market_order("AAPL", 5)

        assert order_id == 789
        mock_send.assert_called_once_with(amount=5, asset_type="AAPL")

    def test_send_sell_market_order_raises_when_not_enough_funds(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "send_sell_market_order",
            side_effect=APIError("INSUFFICIENT_FUNDS"),
        ):
            with pytest.raises(NotEnoughFunds):
                primedelta.send_sell_market_order("AAPL", 100)


class TestCancelOrder:
    def test_cancel_order(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client, "cancel_order"
        ) as mock_cancel:
            primedelta.cancel_order(123)

        mock_cancel.assert_called_once_with(123)


class TestOrderStatus:
    def test_get_order_status(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "get_order_status",
            return_value=OrderStatus.PENDING,
        ):
            status = primedelta.get_order_status(123)

        assert status == OrderStatus.PENDING


class TestOpenOrders:
    def test_open_orders(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_orders = [
            Order(
                id=1,
                order_side=OrderSide.BUY,
                type="LIMIT",
                symbol="AAPL",
                quantity=10,
                price=Decimal("150.00"),
                status=OrderStatus.PENDING,
                date_of_cancellation=None,
            ),
            Order(
                id=2,
                order_side=OrderSide.SELL,
                type="LIMIT",
                symbol="TSLA",
                quantity=5,
                price=Decimal("200.00"),
                status=OrderStatus.PENDING,
                date_of_cancellation=date.today() + timedelta(days=10),
            ),
        ]

        with patch.object(
            primedelta._primedelta_client, "open_orders", return_value=mock_orders
        ):
            orders = primedelta.open_orders()

        assert len(orders) == 2
        assert orders[0].symbol == "AAPL"
        assert orders[1].symbol == "TSLA"


class TestClosedOrders:
    def test_closed_orders(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_orders = [
            Order(
                id=1,
                order_side=OrderSide.BUY,
                type="LIMIT",
                symbol="AAPL",
                quantity=10,
                price=Decimal("150.00"),
                status=OrderStatus.EXECUTED,
                date_of_cancellation=None,
            ),
            Order(
                id=2,
                order_side=OrderSide.BUY,
                type="LIMIT",
                symbol="AMZN",
                quantity=5,
                price=Decimal("170.00"),
                status=OrderStatus.CANCELED,
                date_of_cancellation=date.today() + timedelta(days=10),
            ),
        ]

        with patch.object(
            primedelta._primedelta_client, "closed_orders", return_value=mock_orders
        ):
            orders = primedelta.closed_orders()

        assert len(orders) == 2
        assert orders[0].status == OrderStatus.EXECUTED
        assert orders[1].status == OrderStatus.CANCELED


class TestMarketStatus:
    def test_is_market_open(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client, "is_market_open", return_value=True
        ):
            assert primedelta.is_market_open() is True

        with patch.object(
            primedelta._primedelta_client, "is_market_open", return_value=False
        ):
            assert primedelta.is_market_open() is False
