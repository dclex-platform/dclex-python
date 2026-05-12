import os
from pathlib import Path

from dotenv import load_dotenv

from primedelta import PrimeDelta

# Load .env.local if present (local stack), else .env (default/dev).
_repo_root = Path(__file__).resolve().parents[1]
_env_local = _repo_root / ".env.local"
load_dotenv(_env_local if _env_local.exists() else _repo_root / ".env")

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)

# Anonymous stream — no login required. Returns Pyth public prices.
for price in primedelta.prices_stream(["AAPL", "TSLA", "NVDA"]):
    print(f"{price.symbol}: {price.last_price} @ {price.timestamp}")
    break

# Authenticated stream — broker feed for verified accounts. `symbols` is
# ignored on this path (the broker pushes everything the user is entitled to).
# primedelta.login()
# for price in primedelta.prices_stream():
#     print(f"{price.symbol}: {price.last_price} @ {price.timestamp}")
#     break
# primedelta.logout()
