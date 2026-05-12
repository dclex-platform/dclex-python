from decimal import Decimal

from primedelta import PrimeDelta, SwapSide

my_private_key = "0x"
web3_provider_url = "YOUR_WEB3_PROVIDER_URL"

primedelta = PrimeDelta(private_key=my_private_key, web3_provider_url=web3_provider_url)
primedelta.login()

# Buy AAPL with 10 USDC, accept any output above 0.
buy_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_in=Decimal("10"),
    min_amount_out=Decimal("0"),
)

# Sell 0.05 AAPL for USDC, accept any output above 0.
sell_tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.STOCK_TO_USDC,
    amount_in=Decimal("0.05"),
    min_amount_out=Decimal("0"),
)

# Buy exactly 0.1 AAPL, willing to spend up to 50 USDC.
exact_out_tx = primedelta.swap_exact_output(
    "AAPL",
    SwapSide.USDC_TO_STOCK,
    amount_out=Decimal("0.1"),
    max_amount_in=Decimal("50"),
)

primedelta.logout()
