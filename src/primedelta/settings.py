import os

SIWE_MESSAGE: str = (
    "By signing this message you confirm that you have completely"
    " read and understand Prime Delta's terms of service including all policies"
    " and disclosures and that you agree with each part of them."
)
USDC_ASSET_TYPE: str = "USDC"

PRIMEDELTA_BASE_URL: str = os.getenv(
    "PRIMEDELTA_BASE_URL", "https://api-dev.primedelta.io"
)
PRIMEDELTA_APP_URL: str = os.getenv(
    "PRIMEDELTA_APP_URL", "https://app-dev.primedelta.io"
)
SIWE_URI: str = PRIMEDELTA_APP_URL
# Backend may strip the port (e.g. accepts "localhost" not "localhost:5173").
# Override via PRIMEDELTA_SIWE_DOMAIN when the backend's allowed domain differs.
SIWE_DOMAIN: str = os.getenv(
    "PRIMEDELTA_SIWE_DOMAIN",
    PRIMEDELTA_APP_URL.replace("https://", "").replace("http://", ""),
)

# Pyth Hermes API for public price feeds
PYTH_HERMES_BASE_URL: str = os.getenv(
    "PYTH_HERMES_BASE_URL", "https://hermes.pyth.network"
)

BLOCKCHAIN_FALSE_VALUE = 2
