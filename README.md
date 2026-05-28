# Prime Delta Python Library

Official Python SDK for the [Prime Delta](https://primedelta.io) mint platform and on-chain DEX. Wraps account/KYC/order endpoints and signs transactions for the on-chain stock factory, AMM, and price-feed pools.

## Install

```bash
pip install primedelta
```

Requires Python >= 3.10.

## Quick start

```python
from decimal import Decimal
from primedelta import PrimeDelta, SwapSide

primedelta = PrimeDelta(
    private_key=...,
    web3_provider_url=...,
)
primedelta.login()

# Spend 10 dUSD buying AAPL on the DEX.
tx = primedelta.swap_exact_input(
    "AAPL",
    SwapSide.STABLECOIN_TO_STOCK,
    amount_in=Decimal("10"),
    min_amount_out=Decimal("0"),
)
```

## Mint platform examples

- [Login and logout](./examples/mint-platform/login_and_logout.py)
- [Stocks](./examples/mint-platform/stocks.py)
- [Deposit, withdraw, distributions](./examples/mint-platform/deposit_withdraw_distribution.py)
- [Buying and selling stocks (orders)](./examples/mint-platform/buying_and_selling_stocks.py)
- [Portfolio](./examples/mint-platform/portfolio.py)
- [Real-time price stream (logged in)](./examples/mint-platform/price_stream/prices_stream_logged.py)
- [Real-time price stream (public Pyth)](./examples/mint-platform/price_stream/prices_stream_not_logged.py)

## DEX examples

### Swaps

The router accepts dUSD on one side (`buyExact*`/`sellExact*`) or two non-dUSD tokens routed through dUSD (`swapExact*`, 2-hop). The SDK picks the right entrypoint per call.

- [dUSD ↔ stock (AAPL)](./examples/dex/swap.py) — `swap_exact_input` / `swap_exact_output` with `SwapSide`
- [dUSD ↔ AMM token (AMMT1, AMMT2)](./examples/dex/swap_amm.py) — same API, AMM symbol
- [Cross-dex token ↔ token](./examples/dex/swap_cross_dex.py) — `swap_token_to_token_exact_input` / `swap_token_to_token_exact_output` for AMM↔AMM, AMM↔stock, stock↔stock
- [Native DEL swaps](./examples/dex/swap_native.py) — `wrap_del` / `unwrap_del` plus regular swap on WDEL

> The stablecoin is **dUSD** on chain. `SwapSide.STABLECOIN_TO_STOCK` and `SwapSide.STOCK_TO_STABLECOIN` are the two single-hop directions; cross-dex swaps use the dedicated `swap_token_to_token_*` methods instead of `SwapSide`.

### Liquidity

- [Price-feed pool liquidity](./examples/dex/liquidity_pricefeed.py) — `add_liquidity` / `remove_liquidity` with `PriceFeedAddLiquidity` / `PriceFeedRemoveLiquidity`
- [AMM (Uniswap V3) liquidity](./examples/dex/liquidity_amm.py) — concentrated-range positions via `AMMAddLiquidity` / `AMMRemoveLiquidity`

## Networks

Addresses and ABIs ship inside the package under [`networks/`](./src/primedelta/networks/). Default network is `dev`. To pin a different deployment, edit the JSON file or pass `network="..."` to `PrimeDelta(...)`.

## License

See [LICENSE](./LICENSE).
