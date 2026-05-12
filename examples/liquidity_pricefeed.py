import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from primedelta import PrimeDelta, PriceFeedAddLiquidity, PriceFeedRemoveLiquidity

# Load .env.local if present (local stack), else .env (default/dev).
_repo_root = Path(__file__).resolve().parents[1]
_env_local = _repo_root / ".env.local"
load_dotenv(_env_local if _env_local.exists() else _repo_root / ".env")

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# Add liquidity to the AAPL DCLEX pricefeed pool.
# liquidity_amount is the LP-share amount to mint (18 decimals).
# max_stock_amount / max_usdc_amount cap how much the pool may pull from your wallet.
liquidity_amount = Decimal(10**16)  # 0.01 LP shares

add_tx = primedelta.add_liquidity(
    PriceFeedAddLiquidity(
        symbol="AAPL",
        liquidity_amount=liquidity_amount,
        max_stock_amount=Decimal("5"),
        max_usdc_amount=Decimal("2000"),
    )
)

# Burn the LP shares back to underlying stock + USDC.
remove_tx = primedelta.remove_liquidity(
    PriceFeedRemoveLiquidity(
        symbol="AAPL",
        liquidity_amount=liquidity_amount,
    )
)

primedelta.logout()
