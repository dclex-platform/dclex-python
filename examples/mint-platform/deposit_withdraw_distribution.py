import os
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from primedelta import PrimeDelta

load_dotenv(find_dotenv(".env.local") or find_dotenv(".env"))

primedelta = PrimeDelta(
    private_key=os.environ["PRIMEDELTA_TEST_PRIVATE_KEY"],
    web3_provider_url=os.environ["PRIMEDELTA_PROVIDER_URL"],
)
primedelta.login()

deposit_usdc_tx_hash = primedelta.deposit_usdc(Decimal(100))
usdc_withdrawal_id = primedelta.request_usdc_withdrawal(Decimal(100))
withdraw_usdc_tx_hash = primedelta.claim_usdc_withdrawal(usdc_withdrawal_id)
deposit_aapl_tx_hash = primedelta.deposit_stock_token("AAPL", 10)
stock_withdrawal_id = primedelta.request_stock_withdrawal("AAPL", 10)
withdraw_aapl_tx_hash = primedelta.claim_stock_withdrawal(1)

pending_transfers = primedelta.pending_transfers(page_number=1, page_size=100)
closed_transfers = primedelta.closed_transfers(page_number=1, page_size=100)
claimable_withdrawals = primedelta.claimable_withdrawals()
distributions = primedelta.distributions(page_number=1, page_size=100)

primedelta.logout()
