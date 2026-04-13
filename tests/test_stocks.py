from datetime import datetime
from decimal import Decimal

import pytest

from primedelta import AccountNotVerified


def test_stocks_returns_dictionary_of_available_stocks(primedelta_unverified):
    primedelta_unverified.login()

    stocks = primedelta_unverified.stocks()

    apple_stock = stocks["AAPL"]
    assert apple_stock.symbol == "AAPL"
    assert apple_stock.name == "Apple Inc"
    assert apple_stock.cusip == "037833100"
    assert apple_stock.contract_address == "0x642E483D383da06Bc419Bd9de2D2Bf9167Ad3e4e"
    assert apple_stock.number_of_tokens_in_circulation == Decimal(0)


def test_prices_stream_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.prices_stream()


def test_prices_stream(primedelta):
    primedelta.login()

    prices_stream = primedelta.prices_stream()

    price = next(prices_stream)
    assert isinstance(price.symbol, str)
    assert isinstance(price.last_price, Decimal)
    assert price.last_price > 0
    assert isinstance(price.timestamp, datetime)
    assert isinstance(price.percentage_change, Decimal)
