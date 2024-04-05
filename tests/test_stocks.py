from datetime import datetime
from decimal import Decimal

import pytest

from dclex import AccountNotVerified


def test_stocks_returns_dictionary_of_available_stocks(dclex_unverified):
    dclex_unverified.login()

    stocks = dclex_unverified.stocks()

    apple_stock = stocks["AAPL"]
    assert apple_stock.symbol == "AAPL"
    assert apple_stock.name == "Apple Inc"
    assert apple_stock.cusip == "037833100"
    assert apple_stock.contract_address == "0x642E483D383da06Bc419Bd9de2D2Bf9167Ad3e4e"
    assert apple_stock.number_of_tokens_in_circulation == Decimal(0)


def test_market_prices_returns_dictionary_of_current_market_prices(dclex):
    dclex.login()

    prices = dclex.market_prices()

    apple_price = prices["AAPL"]
    assert apple_price.symbol == "AAPL"
    assert isinstance(apple_price.last_price, Decimal)
    assert apple_price.last_price > 0
    assert isinstance(apple_price.timestamp, datetime)
    assert isinstance(apple_price.percentage_change, Decimal)


def test_market_prices_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.market_prices()


def test_prices_stream(dclex):
    dclex.login()

    prices_stream = dclex.prices_stream()

    price = next(prices_stream)
    assert isinstance(price.symbol, str)
    assert isinstance(price.last_price, Decimal)
    assert price.last_price > 0
    assert isinstance(price.timestamp, datetime)
    assert isinstance(price.percentage_change, Decimal)
