from datetime import date, timedelta
from decimal import Decimal

from primedelta import PrimeDelta, OrderSide

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)
primedelta.login()

limit_buy_order_id = primedelta.send_limit_order(OrderSide.BUY, "AAPL", 5, Decimal("185.50"))
order_status = primedelta.get_order_status(limit_buy_order_id)

cancellation_date = date.today() + timedelta(days=10)
limit_sell_order_id = primedelta.send_limit_order(
    OrderSide.SELL, "AAPL", 5, Decimal("185.50"), cancellation_date
)

market_sell_order_id = primedelta.send_sell_market_order("AAPL", 5)
primedelta.cancel_order(market_sell_order_id)

open_orders = primedelta.open_orders(page_number=1, page_size=100)
closed_orders = primedelta.closed_orders(page_number=1, page_size=100)
is_market_open = primedelta.is_market_open()

primedelta.logout()
