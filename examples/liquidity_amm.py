from decimal import Decimal

from primedelta import PrimeDelta, AMMAddLiquidity, AMMRemoveLiquidity

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)
primedelta.login()

# Add liquidity to the Uniswap V3-style AMM pool for an AMM-listed symbol (e.g. AMMT1).
# Ticks define the price range. -887220/887220 is the full range for fee tier 3000.
add_tx = primedelta.add_liquidity(
    AMMAddLiquidity(
        symbol="AMMT1",
        tick_lower=-887220,
        tick_upper=887220,
        amount_stock_desired=Decimal("1"),
        amount_usdc_desired=Decimal("100"),
        amount_stock_min=Decimal("0"),
        amount_usdc_min=Decimal("0"),
    )
)

# Remove liquidity. position_id is the NFT tokenId returned by NonfungiblePositionManager.mint.
# liquidity is the raw uint128 liquidity amount to burn (read from the position).
position_id = 1
liquidity_to_remove = 10**12

remove_tx = primedelta.remove_liquidity(
    AMMRemoveLiquidity(
        position_id=position_id,
        liquidity=liquidity_to_remove,
        amount_stock_min=Decimal("0"),
        amount_usdc_min=Decimal("0"),
    )
)

# Collect any accumulated fees on the position.
collect_tx = primedelta.collect_fees(position_id)

primedelta.logout()
