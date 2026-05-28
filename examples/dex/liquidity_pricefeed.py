import os
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from primedelta import (
    PrimeDelta,
    PriceFeedAddLiquidity,
    PriceFeedRemoveLiquidity,
    SwapSide,
)

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# Acquire some TSLA so we have stock to pair with the stablecoin for LP.
buy_tx = primedelta.swap_exact_input(
    "TSLA",
    SwapSide.STABLECOIN_TO_STOCK,
    amount_in=Decimal("30"),
    min_amount_out=Decimal("0"),
)
print(f"buy:    {buy_tx}")
tsla_balance = primedelta.get_onchain_stock_balance("TSLA")
print(f"TSLA on chain: {tsla_balance}")

# Add liquidity to the TSLA DCLEX pricefeed pool.
# liquidity_amount is the LP-share amount to mint (18 decimals).
# max_*_amount cap how much the pool may pull from your wallet at the current
# pool price — set generously vs your actual balance.
liquidity_amount = Decimal(10**15)  # 0.001 LP shares

add_tx = primedelta.add_liquidity(
    PriceFeedAddLiquidity(
        symbol="TSLA",
        liquidity_amount=liquidity_amount,
        max_stock_amount=Decimal("0.5"),
        max_stablecoin_amount=Decimal("250"),
    )
)
print(f"add:    {add_tx}")

# Burn the LP shares back to underlying stock + stablecoin.
remove_tx = primedelta.remove_liquidity(
    PriceFeedRemoveLiquidity(
        symbol="TSLA",
        liquidity_amount=liquidity_amount,
    )
)
print(f"remove: {remove_tx}")

primedelta.logout()
