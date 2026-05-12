from decimal import Decimal

from primedelta import PrimeDelta, PriceFeedAddLiquidity, PriceFeedRemoveLiquidity

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)
primedelta.login()

# Add liquidity to the AAPL DCLEX pricefeed pool.
# liquidity_amount is the LP-share amount to mint (18 decimals).
# max_stock_amount / max_usdc_amount cap how much the pool may pull from your wallet.
liquidity_amount = Decimal(10**16)  # 0.01 LP shares

add_tx = primedelta.add_liquidity(
    PriceFeedAddLiquidity(
        symbol="AAPL",
        liquidity_amount=liquidity_amount,
        max_stock_amount=Decimal("5"),
        max_usdc_amount=Decimal("2000"),
    )
)

# Burn the LP shares back to underlying stock + USDC.
remove_tx = primedelta.remove_liquidity(
    PriceFeedRemoveLiquidity(
        symbol="AAPL",
        liquidity_amount=liquidity_amount,
    )
)

primedelta.logout()
