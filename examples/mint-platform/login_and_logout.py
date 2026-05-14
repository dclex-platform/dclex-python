import os

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta
from primedelta.primedelta import DigitalIdentityAlreadyClaimed

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)

primedelta.login()
try:
    primedelta.claim_digital_identity()
except DigitalIdentityAlreadyClaimed:
    print("Digital identity already claimed for this account.")
primedelta.logout()
