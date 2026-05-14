import os

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

portfolio = primedelta.portfolio()
usdc_available_balance = primedelta.get_usdc_available_balance()
usdc_total_balance = primedelta.get_usdc_total_balance()
aapl_available_balance = primedelta.get_stock_available_balance("AAPL")
aapl_total_balance = primedelta.get_stock_total_balance("AAPL")

primedelta.logout()
