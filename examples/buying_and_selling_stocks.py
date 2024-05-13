from datetime import date, timedelta
from decimal import Decimal

from dclex import Dclex, OrderSide

my_private_key = "0x"
web3_provider_url = "https://eth-sepolia.g.alchemy.com/v2/{your_api_key}"

dclex = Dclex(private_key=my_private_key, web3_provider_url=web3_provider_url)
dclex.login()

limit_buy_order_id = dclex.create_limit_order(
    OrderSide.BUY, "AAPL", 5, Decimal("185.50")
)
cancellation_date = date.today() + timedelta(days=10)
limit_sell_order_id = dclex.create_limit_order(
    OrderSide.SELL, "AAPL", 5, Decimal("185.50"), cancellation_date
)

market_sell_order_id = dclex.create_sell_market_order("AAPL", 5)
dclex.cancel_order(market_sell_order_id)

open_orders = dclex.open_orders()
closed_orders = dclex.closed_orders()
is_market_open = dclex.is_market_open()

dclex.logout()
