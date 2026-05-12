from decimal import Decimal
from typing import Any, Callable, Optional

from primedelta.contracts import ContractRef, Contracts
from primedelta.dex.params import (
    AMMAddLiquidity,
    AMMRemoveLiquidity,
    PriceFeedAddLiquidity,
    PriceFeedRemoveLiquidity,
    SwapSide,
)


_USDC_DECIMALS = Decimal(10**6)
_STOCK_DECIMALS = Decimal(10**18)


class PoolNotFound(Exception):
    pass


class RouterNotConfigured(Exception):
    pass


class PositionManagerNotConfigured(Exception):
    pass


class _RouterSwapHandler:
    def __init__(
        self,
        web3,
        account,
        contracts_provider: Callable[[], Contracts],
        signed_prices_fetcher: Callable[[list[str]], list[bytes]],
        send_tx: Callable[..., str],
    ) -> None:
        self._web3 = web3
        self._account = account
        self._contracts_provider = contracts_provider
        self._signed_prices_fetcher = signed_prices_fetcher
        self._send_tx = send_tx

    def swap_exact_input(
        self,
        symbol: str,
        side: SwapSide,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline_seconds: int = 600,
        pyth_value: int = 0,
    ) -> str:
        contracts = self._contracts_provider()
        router_ref = self._require_router(contracts)
        stock_token_addr = self._require_stock_token(contracts, symbol)

        update_data = self._fetch_pyth_update_data(symbol)
        deadline = self._now() + deadline_seconds
        router = self._contract(router_ref)

        if side == SwapSide.USDC_TO_STOCK:
            amount_in_units = int(amount_in * _USDC_DECIMALS)
            min_out_units = int(min_amount_out * _STOCK_DECIMALS)
            self._approve(contracts.core.usdc, router_ref.address, amount_in_units)
            tx_function = router.functions.buyExactInput(
                stock_token_addr,
                amount_in_units,
                min_out_units,
                deadline,
                update_data,
            )
        else:
            amount_in_units = int(amount_in * _STOCK_DECIMALS)
            min_out_units = int(min_amount_out * _USDC_DECIMALS)
            self._approve_stock(stock_token_addr, router_ref.address, amount_in_units)
            tx_function = router.functions.sellExactInput(
                stock_token_addr,
                amount_in_units,
                min_out_units,
                deadline,
                update_data,
            )
        return self._send_tx(tx_function, value=pyth_value)

    def swap_exact_output(
        self,
        symbol: str,
        side: SwapSide,
        amount_out: Decimal,
        max_amount_in: Decimal,
        deadline_seconds: int = 600,
        pyth_value: int = 0,
    ) -> str:
        contracts = self._contracts_provider()
        router_ref = self._require_router(contracts)
        stock_token_addr = self._require_stock_token(contracts, symbol)

        update_data = self._fetch_pyth_update_data(symbol)
        deadline = self._now() + deadline_seconds
        router = self._contract(router_ref)

        if side == SwapSide.USDC_TO_STOCK:
            amount_out_units = int(amount_out * _STOCK_DECIMALS)
            max_in_units = int(max_amount_in * _USDC_DECIMALS)
            self._approve(contracts.core.usdc, router_ref.address, max_in_units)
            tx_function = router.functions.buyExactOutput(
                stock_token_addr,
                amount_out_units,
                max_in_units,
                deadline,
                update_data,
            )
        else:
            amount_out_units = int(amount_out * _USDC_DECIMALS)
            max_in_units = int(max_amount_in * _STOCK_DECIMALS)
            self._approve_stock(stock_token_addr, router_ref.address, max_in_units)
            tx_function = router.functions.sellExactOutput(
                stock_token_addr,
                amount_out_units,
                max_in_units,
                deadline,
                update_data,
            )
        return self._send_tx(tx_function, value=pyth_value)

    def _require_router(self, contracts: Contracts) -> ContractRef:
        if contracts.core.dex_router is None:
            raise RouterNotConfigured()
        return contracts.core.dex_router

    def _require_stock_token(self, contracts: Contracts, symbol: str) -> str:
        pool = contracts.pools.get(symbol)
        if pool is None:
            raise PoolNotFound(symbol)
        return pool.stock_token_address

    def _fetch_pyth_update_data(self, symbol: str) -> list[bytes]:
        # Backend's `/signed-prices/` returns 117-byte FIOracle-format updates
        # (feedId + price + expo + publishTime + v + r + s) signed by the
        # backend's trusted signer. The pool's oracle verifies this signature,
        # so we cannot substitute Hermes/Pyth bytes.
        return self._signed_prices_fetcher([symbol])

    def _now(self) -> int:
        return int(self._web3.eth.get_block("latest")["timestamp"])

    def _contract(self, ref: ContractRef):
        return self._web3.eth.contract(
            address=self._web3.to_checksum_address(ref.address), abi=ref.abi
        )

    def _approve(self, token_ref: ContractRef, spender: str, amount: int) -> None:
        token = self._contract(token_ref)
        self._send_tx(
            token.functions.approve(self._web3.to_checksum_address(spender), amount)
        )

    def _approve_stock(self, stock_token_address: str, spender: str, amount: int) -> None:
        token = self._erc20_at(stock_token_address)
        self._send_tx(
            token.functions.approve(self._web3.to_checksum_address(spender), amount)
        )

    def _erc20_at(self, address: str):
        return self._web3.eth.contract(
            address=self._web3.to_checksum_address(address), abi=_ERC20_APPROVE_ABI
        )


class _DclexPoolHandler:
    def __init__(
        self,
        web3,
        account,
        contracts_provider: Callable[[], Contracts],
        send_tx: Callable[..., str],
    ) -> None:
        self._web3 = web3
        self._account = account
        self._contracts_provider = contracts_provider
        self._send_tx = send_tx

    def add_liquidity(self, params: PriceFeedAddLiquidity) -> str:
        contracts = self._contracts_provider()
        router_ref = self._require_router(contracts)
        stock_token_addr = self._require_stock_token(contracts, params.symbol)

        pool_address = self._lookup_dclex_pool(router_ref, stock_token_addr)
        pool = self._dclex_pool(contracts, pool_address)

        liquidity_units = int(params.liquidity_amount)
        max_stock_units = int(params.max_stock_amount * _STOCK_DECIMALS)
        max_usdc_units = int(params.max_usdc_amount * _USDC_DECIMALS)

        # Approve user-specified caps; pool takes proportional amount and reverts
        # if it would exceed allowance (chain-enforced slippage bound).
        self._approve_at(stock_token_addr, pool_address, max_stock_units)
        self._approve(contracts.core.usdc, pool_address, max_usdc_units)
        return self._send_tx(pool.functions.addLiquidity(liquidity_units))

    def remove_liquidity(self, params: PriceFeedRemoveLiquidity) -> str:
        contracts = self._contracts_provider()
        router_ref = self._require_router(contracts)
        stock_token_addr = self._require_stock_token(contracts, params.symbol)

        pool_address = self._lookup_dclex_pool(router_ref, stock_token_addr)
        pool = self._dclex_pool(contracts, pool_address)
        liquidity_units = int(params.liquidity_amount)
        return self._send_tx(pool.functions.removeLiquidity(liquidity_units))

    def _require_router(self, contracts: Contracts) -> ContractRef:
        if contracts.core.dex_router is None:
            raise RouterNotConfigured()
        return contracts.core.dex_router

    def _require_stock_token(self, contracts: Contracts, symbol: str) -> str:
        pool = contracts.pools.get(symbol)
        if pool is None:
            raise PoolNotFound(symbol)
        return pool.stock_token_address

    def _lookup_dclex_pool(self, router_ref: ContractRef, stock_token_addr: str) -> str:
        router = self._web3.eth.contract(
            address=self._web3.to_checksum_address(router_ref.address),
            abi=router_ref.abi,
        )
        pool_addr = router.functions.stockTokenToPool(
            self._web3.to_checksum_address(stock_token_addr)
        ).call()
        if int(pool_addr, 16) == 0:
            raise PoolNotFound(f"no DCLEX pool registered for {stock_token_addr}")
        return pool_addr

    def _dclex_pool(self, contracts: Contracts, pool_address: str):
        abi = contracts.pool_abis.get("dclex_pool")
        if abi is None:
            raise RuntimeError("dclex_pool ABI missing from /contracts/ payload")
        return self._web3.eth.contract(
            address=self._web3.to_checksum_address(pool_address), abi=abi
        )

    def _approve(self, token_ref: ContractRef, spender: str, amount: int) -> None:
        token = self._web3.eth.contract(
            address=self._web3.to_checksum_address(token_ref.address), abi=token_ref.abi
        )
        self._send_tx(
            token.functions.approve(self._web3.to_checksum_address(spender), amount)
        )

    def _approve_at(self, token_address: str, spender: str, amount: int) -> None:
        token = self._web3.eth.contract(
            address=self._web3.to_checksum_address(token_address),
            abi=_ERC20_APPROVE_ABI,
        )
        self._send_tx(
            token.functions.approve(self._web3.to_checksum_address(spender), amount)
        )


class _AMMPoolHandler:
    def __init__(
        self,
        web3,
        account,
        contracts_provider: Callable[[], Contracts],
        send_tx: Callable[..., str],
    ) -> None:
        self._web3 = web3
        self._account = account
        self._contracts_provider = contracts_provider
        self._send_tx = send_tx

    def add_liquidity(self, params: AMMAddLiquidity) -> str:
        contracts = self._contracts_provider()
        npm_ref = self._require_npm(contracts)
        router_ref = self._require_router(contracts)
        stock_token_addr = self._require_stock_token(contracts, params.symbol)

        pool_address = self._lookup_amm_pool(router_ref, stock_token_addr)
        token0, token1, fee = self._read_pool_tokens(contracts, pool_address)

        amounts = self._map_amounts(
            stock_token_addr,
            token0,
            stock=params.amount_stock_desired,
            usdc=params.amount_usdc_desired,
        )
        amounts_min = self._map_amounts(
            stock_token_addr,
            token0,
            stock=params.amount_stock_min,
            usdc=params.amount_usdc_min,
        )

        npm = self._contract(npm_ref)
        self._approve_at(token0, npm_ref.address, amounts[0])
        self._approve_at(token1, npm_ref.address, amounts[1])

        deadline = self._now() + 600
        return self._send_tx(
            npm.functions.mint(
                {
                    "token0": self._web3.to_checksum_address(token0),
                    "token1": self._web3.to_checksum_address(token1),
                    "fee": fee,
                    "tickLower": params.tick_lower,
                    "tickUpper": params.tick_upper,
                    "amount0Desired": amounts[0],
                    "amount1Desired": amounts[1],
                    "amount0Min": amounts_min[0],
                    "amount1Min": amounts_min[1],
                    "recipient": self._account.address,
                    "deadline": deadline,
                }
            )
        )

    def remove_liquidity(self, params: AMMRemoveLiquidity) -> str:
        contracts = self._contracts_provider()
        npm_ref = self._require_npm(contracts)
        npm = self._contract(npm_ref)
        deadline = self._now() + 600

        amount_stock_min_units = int(params.amount_stock_min * _STOCK_DECIMALS)
        amount_usdc_min_units = int(params.amount_usdc_min * _USDC_DECIMALS)

        max_uint128 = (1 << 128) - 1
        decrease_call = npm.encodeABI(
            fn_name="decreaseLiquidity",
            args=[
                (
                    params.position_id,
                    params.liquidity,
                    amount_stock_min_units,
                    amount_usdc_min_units,
                    deadline,
                )
            ],
        )
        collect_call = npm.encodeABI(
            fn_name="collect",
            args=[
                (
                    params.position_id,
                    self._account.address,
                    max_uint128,
                    max_uint128,
                )
            ],
        )
        return self._send_tx(npm.functions.multicall([decrease_call, collect_call]))

    def collect_fees(self, position_id: int) -> str:
        contracts = self._contracts_provider()
        npm_ref = self._require_npm(contracts)
        npm = self._contract(npm_ref)
        max_uint128 = (1 << 128) - 1
        return self._send_tx(
            npm.functions.collect(
                {
                    "tokenId": position_id,
                    "recipient": self._account.address,
                    "amount0Max": max_uint128,
                    "amount1Max": max_uint128,
                }
            )
        )

    def _require_npm(self, contracts: Contracts) -> ContractRef:
        if contracts.core.position_manager is None:
            raise PositionManagerNotConfigured()
        return contracts.core.position_manager

    def _require_router(self, contracts: Contracts) -> ContractRef:
        if contracts.core.dex_router is None:
            raise RouterNotConfigured()
        return contracts.core.dex_router

    def _require_stock_token(self, contracts: Contracts, symbol: str) -> str:
        pool = contracts.pools.get(symbol)
        if pool is None:
            raise PoolNotFound(symbol)
        return pool.stock_token_address

    def _lookup_amm_pool(self, router_ref: ContractRef, stock_token_addr: str) -> str:
        router = self._contract(router_ref)
        pool_addr = router.functions.stockToAMMPool(
            self._web3.to_checksum_address(stock_token_addr)
        ).call()
        if int(pool_addr, 16) == 0:
            raise PoolNotFound(f"no AMM pool registered for {stock_token_addr}")
        return pool_addr

    def _read_pool_tokens(
        self, contracts: Contracts, pool_address: str
    ) -> tuple[str, str, int]:
        abi = contracts.pool_abis.get("univ3_pool")
        if abi is None:
            raise RuntimeError("univ3_pool ABI missing from /contracts/ payload")
        pool = self._web3.eth.contract(
            address=self._web3.to_checksum_address(pool_address), abi=abi
        )
        return (
            pool.functions.token0().call(),
            pool.functions.token1().call(),
            pool.functions.fee().call(),
        )

    def _map_amounts(
        self, stock_token_addr: str, token0: str, *, stock: Decimal, usdc: Decimal
    ) -> tuple[int, int]:
        stock_units = int(stock * _STOCK_DECIMALS)
        usdc_units = int(usdc * _USDC_DECIMALS)
        if token0.lower() == stock_token_addr.lower():
            return (stock_units, usdc_units)
        return (usdc_units, stock_units)

    def _now(self) -> int:
        return int(self._web3.eth.get_block("latest")["timestamp"])

    def _contract(self, ref: ContractRef):
        return self._web3.eth.contract(
            address=self._web3.to_checksum_address(ref.address), abi=ref.abi
        )

    def _approve_at(self, token_address: str, spender: str, amount: int) -> None:
        token = self._web3.eth.contract(
            address=self._web3.to_checksum_address(token_address),
            abi=_ERC20_APPROVE_ABI,
        )
        self._send_tx(
            token.functions.approve(self._web3.to_checksum_address(spender), amount)
        )


_ERC20_APPROVE_ABI: list[Any] = [
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]
