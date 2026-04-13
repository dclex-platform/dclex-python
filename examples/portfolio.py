from primedelta import PrimeDelta

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)
primedelta.login()

portfolio = primedelta.portfolio()
usdc_available_balance = primedelta.get_usdc_available_balance()
usdc_total_balance = primedelta.get_usdc_total_balance()
aapl_available_balance = primedelta.get_stock_available_balance("AAPL")
aapl_total_balance = primedelta.get_stock_total_balance("AAPL")

primedelta.logout()
