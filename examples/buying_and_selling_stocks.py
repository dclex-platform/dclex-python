import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from primedelta import PrimeDelta, OrderSide

# Load .env.local if present (local stack), else .env (default/dev).
_repo_root = Path(__file__).resolve().parents[1]
_env_local = _repo_root / ".env.local"
load_dotenv(_env_local if _env_local.exists() else _repo_root / ".env")

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
