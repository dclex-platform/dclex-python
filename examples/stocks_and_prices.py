from dclex import Dclex

my_private_key = "0x"
web3_provider_url = "https://eth-sepolia.g.alchemy.com/v2/{your_api_key}"

dclex = Dclex(private_key=my_private_key, web3_provider_url=web3_provider_url)

stocks = dclex.stocks()
aapl_stock = stocks["AAPL"]
symbol = aapl_stock.symbol
name = aapl_stock.name
cusip = aapl_stock.cusip
contract_address = aapl_stock.contract_address
number_of_tokens_in_circulation = aapl_stock.number_of_tokens_in_circulation

dclex.login()

prices_stream = dclex.prices_stream()
for price in prices_stream:
    print(price.symbol, price.last_price, price.timestamp, price.percentage_change)

dclex.logout()
