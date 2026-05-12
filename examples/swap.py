import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from primedelta import PrimeDelta, SwapSide

# Load .env.local if present (local stack), else .env (default/dev).
_repo_root = Path(__file__).resolve().parents[1]
_env_local = _repo_root / ".env.local"
load_dotenv(_env_local if _env_local.exists() else _repo_root / ".env")

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

# Buy AAPL with 10 USDC, accept any output above 0.
buy_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("10"),
    min_amount_out=Decimal("0"),
)

# Sell 0.05 AAPL for USDC, accept any output above 0.
sell_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.STOCK_TO_USDC,
    amount_in=Decimal("0.05"),
    min_amount_out=Decimal("0"),
)

# Buy exactly 0.1 AAPL, willing to spend up to 50 USDC.
exact_out_tx = primedelta.swap_exact_output(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_out=Decimal("0.1"),
    max_amount_in=Decimal("50"),
)

primedelta.logout()
