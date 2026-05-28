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

# Native DEL isn't an ERC20, so it can't be passed directly to the router. Wrap
# it to WDEL first (1:1 deposit), then swap WDEL like any AMM token. Unwrap on
# the way back.

native_balance = primedelta.get_native_del_balance()
print(f"native DEL balance: {native_balance}")

# DEL → AAPL: wrap a small amount, then cross-dex swap WDEL → AAPL.
primedelta.wrap_del(Decimal("1"))
wdel_balance = primedelta.get_onchain_stock_balance("WDEL")
print(f"WDEL after wrap: {wdel_balance}")

del_to_aapl_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="WDEL",
    output_symbol="AAPL",
    amount_in=wdel_balance,
    min_amount_out=Decimal("0"),
)
print(f"DEL → AAPL: {del_to_aapl_tx}")

# AAPL → DEL: sell AAPL for WDEL, then unwrap.
aapl_balance = primedelta.get_onchain_stock_balance("AAPL")
aapl_to_wdel_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="AAPL",
    output_symbol="WDEL",
    amount_in=aapl_balance / 2,
    min_amount_out=Decimal("0"),
)
print(f"AAPL → WDEL: {aapl_to_wdel_tx}")

wdel_after_sell = primedelta.get_onchain_stock_balance("WDEL")
unwrap_tx = primedelta.unwrap_del(wdel_after_sell)
print(f"WDEL → DEL (unwrap): {unwrap_tx}")

# DEL → AMMT1: wrap then AMM ↔ AMM swap.
primedelta.wrap_del(Decimal("0.5"))
wdel_now = primedelta.get_onchain_stock_balance("WDEL")
del_to_ammt1_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="WDEL",
    output_symbol="AMMT1",
    amount_in=wdel_now,
    min_amount_out=Decimal("0"),
)
print(f"DEL → AMMT1: {del_to_ammt1_tx}")

# AMMT1 → DEL: AMM ↔ AMM swap to WDEL, then unwrap.
ammt1_balance = primedelta.get_onchain_stock_balance("AMMT1")
ammt1_to_wdel_tx = primedelta.swap_token_to_token_exact_input(
    input_symbol="AMMT1",
    output_symbol="WDEL",
    amount_in=ammt1_balance / 2,
    min_amount_out=Decimal("0"),
)
print(f"AMMT1 → WDEL: {ammt1_to_wdel_tx}")
unwrap_tx = primedelta.unwrap_del(primedelta.get_onchain_stock_balance("WDEL"))
print(f"WDEL → DEL (unwrap): {unwrap_tx}")

# DEL → dUSD and dUSD → DEL also work — they use the simple buy/sell paths
# rather than cross-dex, because dUSD is one side.
primedelta.wrap_del(Decimal("0.5"))
del_to_dusd_tx = primedelta.swap_exact_input(
    "WDEL",
    SwapSide.STOCK_TO_STABLECOIN,
    amount_in=primedelta.get_onchain_stock_balance("WDEL"),
    min_amount_out=Decimal("0"),
)
print(f"DEL → dUSD: {del_to_dusd_tx}")

dusd_to_del_tx = primedelta.swap_exact_input(
    "WDEL",
    SwapSide.STABLECOIN_TO_STOCK,
    amount_in=Decimal("1"),
    min_amount_out=Decimal("0"),
)
print(f"dUSD → DEL: {dusd_to_del_tx}")
primedelta.unwrap_del(primedelta.get_onchain_stock_balance("WDEL"))

primedelta.logout()
