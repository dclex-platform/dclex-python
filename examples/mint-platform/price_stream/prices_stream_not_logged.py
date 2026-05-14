import os

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)

# Anonymous stream — no login required. Returns Pyth public prices.
for price in primedelta.prices_stream(["AAPL", "TSLA", "NVDA"]):
    print(f"{price.symbol}: {price.last_price} @ {price.timestamp}")
