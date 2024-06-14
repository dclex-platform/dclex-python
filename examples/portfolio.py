from dclex import Dclex

my_private_key = "0x"
web3_provider_url = "https://eth-sepolia.g.alchemy.com/v2/{your_api_key}"

dclex = Dclex(private_key=my_private_key, web3_provider_url=web3_provider_url)
dclex.login()

portfolio = dclex.portfolio()
usdc_available_balance = dclex.get_usdc_available_balance()
usdc_total_balance = dclex.get_usdc_total_balance()
aapl_available_balance = dclex.get_stock_available_balance("AAPL")
aapl_total_balance = dclex.get_stock_total_balance("AAPL")

dclex.logout()
