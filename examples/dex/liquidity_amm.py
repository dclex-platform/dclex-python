import os
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from primedelta import (
    AMMAddLiquidity,
    AMMRemoveLiquidity,
    PrimeDelta,
    SwapSide,
)

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# AMMT1 is an AMM-only token; users acquire it via swap before LPing.
buy_tx = primedelta.swap_exact_input(
    "AMMT1",
    SwapSide.STABLECOIN_TO_STOCK,
    amount_in=Decimal("20"),
    min_amount_out=Decimal("0"),
)
print(f"buy:    {buy_tx}")

ammt1_balance = primedelta.get_onchain_stock_balance("AMMT1")
print(f"AMMT1 on chain: {ammt1_balance}")

# Add full-range liquidity (-887220/887220 is the full range for fee tier 3000).
# Pool draws the matching ratio at current price; caps prevent over-spend.
add_tx = primedelta.add_liquidity(
    AMMAddLiquidity(
        symbol="AMMT1",
        tick_lower=-887220,
        tick_upper=887220,
        amount_stock_desired=ammt1_balance / 2,
        amount_stablecoin_desired=Decimal("10"),
        amount_stock_min=Decimal("0"),
        amount_stablecoin_min=Decimal("0"),
    )
)
print(f"add:    {add_tx}")

# Discover the position NFT we just minted (it's the most recent one we own).
positions = primedelta.lp_positions()
position_id = positions[-1]
info = primedelta.lp_position(position_id)
print(f"position_id={position_id} liquidity={info.liquidity}")

# Burn all liquidity from this position.
remove_tx = primedelta.remove_liquidity(
    AMMRemoveLiquidity(
        position_id=position_id,
        liquidity=info.liquidity,
        amount_stock_min=Decimal("0"),
        amount_stablecoin_min=Decimal("0"),
    )
)
print(f"remove: {remove_tx}")

# Sweep any accumulated fees + the just-decreased liquidity.
collect_tx = primedelta.collect_fees(position_id)
print(f"collect:{collect_tx}")

primedelta.logout()
