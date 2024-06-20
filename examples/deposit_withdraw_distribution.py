from decimal import Decimal

from dclex import Dclex

my_private_key = "0x"
web3_provider_url = "https://eth-sepolia.g.alchemy.com/v2/{your_api_key}"

dclex = Dclex(private_key=my_private_key, web3_provider_url=web3_provider_url)
dclex.login()

deposit_usdc_tx_hash = dclex.deposit_usdc(Decimal(100))
usdc_withdrawal_id = dclex.request_usdc_withdrawal(Decimal(100))
withdraw_usdc_tx_hash = dclex.claim_usdc_withdrawal(usdc_withdrawal_id)
deposit_aapl_tx_hash = dclex.deposit_stock_token("AAPL", 10)
stock_withdrawal_id = dclex.request_stock_withdrawal("AAPL", 10)
withdraw_aapl_tx_hash = dclex.claim_stock_withdrawal(1)

pending_transfers = dclex.pending_transfers(page_number=1, page_size=100)
closed_transfers = dclex.closed_transfers(page_number=1, page_size=100)
claimable_withdrawals = dclex.claimable_withdrawals()
pending_distributions = dclex.pending_distributions(page_number=1, page_size=100)
closed_distributions = dclex.closed_distributions(page_number=1, page_size=100)

dclex.logout()
