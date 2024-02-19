from decimal import Decimal

from dclex import Dclex

my_private_key = "0x"
web3_provider_url = "https://eth-sepolia.g.alchemy.com/v2/{your_api_key}"

dclex = Dclex(private_key=my_private_key, web3_provider_url=web3_provider_url)
dclex.login()

deposit_usdc_tx_hash = dclex.deposit_usdc(Decimal(100))
withdraw_usdc_tx_hash = dclex.withdraw_usdc(Decimal(100))
deposit_aapl_tx_hash = dclex.deposit_stock_token("AAPL", 10)
withdraw_aapl_tx_hash = dclex.withdraw_stock_token("AAPL", 10)

pending_transfers = dclex.pending_transfers()
closed_transfers = dclex.closed_transfers()
claimable_withdrawals = dclex.claimable_withdrawals()
