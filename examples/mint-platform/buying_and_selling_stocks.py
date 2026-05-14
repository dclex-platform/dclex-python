import os
from datetime import date, timedelta
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta, OrderSide

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
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
