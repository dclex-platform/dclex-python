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

primedelta.login()
primedelta.claim_digital_identity()
primedelta.logout()
