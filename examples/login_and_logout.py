from primedelta import PrimeDelta

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)

primedelta.login()
primedelta.claim_digital_identity()
primedelta.logout()
