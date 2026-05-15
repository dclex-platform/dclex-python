import os

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)

# `stocks()` is unauthenticated — no login required.
stocks = primedelta.stocks()
print(f"{len(stocks)} stocks listed")

aapl = stocks["AAPL"]
print(f"  symbol:   {aapl.symbol}")
print(f"  name:     {aapl.name}")
print(f"  cusip:    {aapl.cusip}")
print(f"  contract: {aapl.contract_address}")
print(f"  supply:   {aapl.number_of_tokens_in_circulation}")
