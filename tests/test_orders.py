import math
from datetime import date, timedelta
from decimal import Decimal
from time import sleep

import pytest

from primedelta.primedelta import NotEnoughFunds
from primedelta.types import Order, OrderSide, OrderStatus

from .conftest import wait_for_transaction


def test_send_buy_and_sell_limit_order(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(200))
    wait_for_transaction(tx_hash, provider_url)

    aapl_available_balance_before = primedelta.get_stock_available_balance("AAPL")
    aapl_total_balance_before = primedelta.get_stock_total_balance("AAPL")

    order_id = primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    assert primedelta.get_order_status(order_id) == OrderStatus.PENDING
    sleep(30)

    assert (
        primedelta.get_stock_available_balance("AAPL") - aapl_available_balance_before == 1
    )
    assert primedelta.get_stock_total_balance("AAPL") - aapl_total_balance_before == 1

    primedelta.send_limit_order(
        OrderSide.SELL, "AAPL", 1, Decimal(190), date.today() + timedelta(days=10)
    )
    sleep(30)

    assert primedelta.get_stock_available_balance("AAPL") == aapl_available_balance_before
    assert primedelta.get_stock_total_balance("AAPL") == aapl_total_balance_before


def test_send_buy_and_sell_limit_order_raises_when_not_enough_funds_for_order(primedelta):
    primedelta.login()
    price = next(
        price_info.last_price
        for price_info in primedelta.prices_stream()
        if price_info.symbol == "AAPL"
    )
    usdc_available_balance = primedelta.get_usdc_available_balance()
    stocks_quantity = math.ceil(usdc_available_balance / price) + 1

    with pytest.raises(NotEnoughFunds):
        primedelta.send_limit_order(OrderSide.BUY, "AAPL", stocks_quantity, price)


def test_send_sell_market_order(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(200))
    wait_for_transaction(tx_hash, provider_url)

    aapl_available_balance_before = primedelta.get_stock_available_balance("AAPL")
    aapl_total_balance_before = primedelta.get_stock_total_balance("AAPL")

    primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    assert (
        primedelta.get_stock_available_balance("AAPL") - aapl_available_balance_before == 1
    )
    assert primedelta.get_stock_total_balance("AAPL") - aapl_total_balance_before == 1

    primedelta.send_sell_market_order("AAPL", 1)
    sleep(30)

    assert primedelta.get_stock_available_balance("AAPL") == aapl_available_balance_before
    assert primedelta.get_stock_total_balance("AAPL") == aapl_total_balance_before


def test_send_sell_market_order_raises_when_not_enough_funds_for_order(primedelta):
    primedelta.login()
    available_balance = primedelta.get_stock_available_balance("AAPL")

    with pytest.raises(NotEnoughFunds):
        primedelta.send_sell_market_order("AAPL", available_balance + 1)


def test_cancelling_orders(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(200))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    usdc_available_balance_before = primedelta.get_usdc_available_balance()
    usdc_total_balance_before = primedelta.get_usdc_total_balance()
    aapl_available_balance_before = primedelta.get_stock_available_balance("AAPL")
    aapl_total_balance_before = primedelta.get_stock_total_balance("AAPL")

    order_id = primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    primedelta.cancel_order(order_id)
    sleep(30)

    assert primedelta.get_usdc_available_balance() == usdc_available_balance_before
    assert primedelta.get_usdc_total_balance() == usdc_total_balance_before
    assert primedelta.get_stock_available_balance("AAPL") == aapl_available_balance_before
    assert primedelta.get_stock_total_balance("AAPL") == aapl_total_balance_before


def test_open_orders(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(600))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    order_id_1 = primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    order_id_2 = primedelta.send_limit_order(
        OrderSide.BUY, "AMZN", 2, Decimal(170), date.today() + timedelta(days=10)
    )

    open_orders = primedelta.open_orders()
    assert len(open_orders) == 2
    assert open_orders[0] == Order(
        id=order_id_1,
        order_side=OrderSide.BUY,
        type="LIMIT",
        symbol="AAPL",
        quantity=1,
        price=Decimal(190),
        status=OrderStatus.PENDING,
        date_of_cancellation=None,
    )
    assert open_orders[1] == Order(
        id=order_id_2,
        order_side=OrderSide.BUY,
        type="LIMIT",
        symbol="AMZN",
        quantity=2,
        price=Decimal(170),
        status=OrderStatus.PENDING,
        date_of_cancellation=date.today() + timedelta(days=10),
    )

    primedelta.cancel_order(order_id_2)
    sleep(30)
    assert primedelta.open_orders() == []


def test_closed_orders(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(600))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)
    closed_orders_len_before = len(primedelta.closed_orders())

    order_id_1 = primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    order_id_2 = primedelta.send_limit_order(
        OrderSide.BUY, "AMZN", 2, Decimal(170), date.today() + timedelta(days=10)
    )

    closed_orders_id = {order.id for order in primedelta.closed_orders()}
    assert order_id_1 not in closed_orders_id
    assert order_id_2 not in closed_orders_id

    primedelta.cancel_order(order_id_2)
    sleep(30)

    closed_orders = {order.id: order for order in primedelta.closed_orders()}
    assert len(closed_orders) == closed_orders_len_before + 2
    assert closed_orders[order_id_1] == Order(
        id=order_id_1,
        order_side=OrderSide.BUY,
        type="LIMIT",
        symbol="AAPL",
        quantity=1,
        price=Decimal(190),
        status=OrderStatus.EXECUTED,
        date_of_cancellation=None,
    )
    assert closed_orders[order_id_2] == Order(
        id=order_id_2,
        order_side=OrderSide.BUY,
        type="LIMIT",
        symbol="AMZN",
        quantity=2,
        price=Decimal(170),
        status=OrderStatus.CANCELED,
        date_of_cancellation=date.today() + timedelta(days=10),
    )


def test_is_market_open_returns_if_market_is_currently_open(primedelta, provider_url):
    result = primedelta.is_market_open()
    assert isinstance(result, bool)
