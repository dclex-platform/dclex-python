from primedelta import PrimeDelta

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)

# Anonymous stream — no login required. Returns Pyth public prices.
for price in primedelta.prices_stream(["AAPL", "TSLA", "NVDA"]):
    print(f"{price.symbol}: {price.last_price} @ {price.timestamp}")
    break

# Authenticated stream — broker feed for verified accounts. `symbols` is
# ignored on this path (the broker pushes everything the user is entitled to).
primedelta.login()
for price in primedelta.prices_stream():
    print(f"{price.symbol}: {price.last_price} @ {price.timestamp}")
    break
primedelta.logout()
