import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from primedelta import PrimeDelta, AMMAddLiquidity, AMMRemoveLiquidity

# Load .env.local if present (local stack), else .env (default/dev).
_repo_root = Path(__file__).resolve().parents[1]
_env_local = _repo_root / ".env.local"
load_dotenv(_env_local if _env_local.exists() else _repo_root / ".env")

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# Add liquidity to the Uniswap V3-style AMM pool for an AMM-listed symbol (e.g. AMMT1).
# Ticks define the price range. -887220/887220 is the full range for fee tier 3000.
add_tx = primedelta.add_liquidity(
    AMMAddLiquidity(
        symbol="AMMT1",
        tick_lower=-887220,
        tick_upper=887220,
        amount_stock_desired=Decimal("1"),
        amount_usdc_desired=Decimal("100"),
        amount_stock_min=Decimal("0"),
        amount_usdc_min=Decimal("0"),
    )
)

# Remove liquidity. position_id is the NFT tokenId returned by NonfungiblePositionManager.mint.
# liquidity is the raw uint128 liquidity amount to burn (read from the position).
position_id = 1
liquidity_to_remove = 10**12

remove_tx = primedelta.remove_liquidity(
    AMMRemoveLiquidity(
        position_id=position_id,
        liquidity=liquidity_to_remove,
        amount_stock_min=Decimal("0"),
        amount_usdc_min=Decimal("0"),
    )
)

# Collect any accumulated fees on the position.
collect_tx = primedelta.collect_fees(position_id)

primedelta.logout()
