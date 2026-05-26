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

# AMM-token swaps go through the same router entrypoints as stocks; only the
# pool implementation differs (UniswapV3 vs. custom pricefeed). The SDK picks
# automatically based on which pool is registered for the symbol.

# Buy AMMT1 with 10 dUSD.
buy_tx = primedelta.swap_exact_input(
    "AMMT1",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("10"),
    min_amount_out=Decimal("0"),
)
print(f"buy AMMT1 with dUSD: {buy_tx}")

ammt1_received = primedelta.get_onchain_stock_balance("AMMT1")
print(f"AMMT1 on chain: {ammt1_received}")

# Sell half of the AMMT1 we just bought back to dUSD.
sell_tx = primedelta.swap_exact_input(
    "AMMT1",
    SwapSide.STOCK_TO_USDC,
    amount_in=ammt1_received / 2,
    min_amount_out=Decimal("0"),
)
print(f"sell AMMT1 for dUSD: {sell_tx}")

# Exact-output: buy exactly 0.05 AMMT2, capping spend at 25 dUSD.
exact_out_tx = primedelta.swap_exact_output(
    "AMMT2",
    SwapSide.USDC_TO_STOCK,
    amount_out=Decimal("0.05"),
    max_amount_in=Decimal("25"),
)
print(f"exact-out buy AMMT2 with dUSD: {exact_out_tx}")

# Exact-output sell: receive exactly 5 dUSD by selling AMMT1, capping the AMMT1
# spent at half of what we still hold.
remaining_ammt1 = primedelta.get_onchain_stock_balance("AMMT1")
exact_out_sell_tx = primedelta.swap_exact_output(
    "AMMT1",
    SwapSide.STOCK_TO_USDC,
    amount_out=Decimal("5"),
    max_amount_in=remaining_ammt1 / 2,
)
print(f"exact-out sell AMMT1 for dUSD: {exact_out_sell_tx}")

primedelta.logout()
