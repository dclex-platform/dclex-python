import os
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta, SwapSide

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# Spend 10 USDC of buying power on AAPL. The actual amount received depends on
# the current pool price, so we don't know it ahead of time.
buy_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("10"),
    min_amount_out=Decimal("0"),
)
print(f"buy:  {buy_tx}")

# Read what we actually received on chain (backend indexer can lag).
aapl_received = primedelta.get_onchain_stock_balance("AAPL")
print(f"AAPL on chain: {aapl_received}")

# Sell half of what we just bought.
sell_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.STOCK_TO_USDC,
    amount_in=aapl_received / 2,
    min_amount_out=Decimal("0"),
)
print(f"sell: {sell_tx}")

# Buy exactly 0.01 AAPL, capping spend at 10 USDC.
exact_out_tx = primedelta.swap_exact_output(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_out=Decimal("0.01"),
    max_amount_in=Decimal("10"),
)
print(f"exact-out buy: {exact_out_tx}")

# Receive exactly 5 dUSD by selling AAPL, capping the AAPL spent at 1.
exact_out_sell_tx = primedelta.swap_exact_output(
    "AAPL",
    SwapSide.STOCK_TO_USDC,
    amount_out=Decimal("5"),
    max_amount_in=Decimal("1"),
)
print(f"exact-out sell: {exact_out_sell_tx}")

primedelta.logout()
