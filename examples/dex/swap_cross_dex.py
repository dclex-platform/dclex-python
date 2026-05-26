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

# Cross-dex swaps trade two non-dUSD tokens; the router routes input→dUSD→output
# internally. Either leg may be a custom (pricefeed) or AMM pool — the router
# picks per-token.

# Seed AMMT1 and AAPL balances with dUSD so the cross-dex swaps have something
# to spend.
primedelta.swap_exact_input(
    "AMMT1",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("20"),
    min_amount_out=Decimal("0"),
)
primedelta.swap_exact_input(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("20"),
    min_amount_out=Decimal("0"),
)
ammt1_balance = primedelta.get_onchain_stock_balance("AMMT1")
aapl_balance = primedelta.get_onchain_stock_balance("AAPL")
print(f"seeded AMMT1={ammt1_balance}, AAPL={aapl_balance}")

# AMM → AMM: swap part of our AMMT1 for AMMT2.
amm_to_amm_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="AMMT1",
    output_symbol="AMMT2",
    amount_in=ammt1_balance / 4,
    min_amount_out=Decimal("0"),
)
print(f"AMMT1 → AMMT2: {amm_to_amm_tx}")

# Stock → AMM: trade AAPL for AMMT1.
stock_to_amm_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="AAPL",
    output_symbol="AMMT1",
    amount_in=aapl_balance / 4,
    min_amount_out=Decimal("0"),
)
print(f"AAPL → AMMT1: {stock_to_amm_tx}")

# AMM → Stock: trade some AMMT1 for AAPL.
amm_to_stock_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="AMMT1",
    output_symbol="AAPL",
    amount_in=primedelta.get_onchain_stock_balance("AMMT1") / 4,
    min_amount_out=Decimal("0"),
)
print(f"AMMT1 → AAPL: {amm_to_stock_tx}")

# Exact-output cross-dex: buy exactly 0.01 AAPL by spending at most 5 AMMT1.
exact_out_tx = primedelta.swap_token_to_token_exact_output(
    input_symbol="AMMT1",
    output_symbol="AAPL",
    amount_out=Decimal("0.01"),
    max_amount_in=Decimal("5"),
)
print(f"exact-out AMMT1 → AAPL: {exact_out_tx}")

primedelta.logout()
