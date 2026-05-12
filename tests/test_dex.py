from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from primedelta import (
    AccountNotVerified,
    AMMAddLiquidity,
    AMMRemoveLiquidity,
    PrimeDelta,
    PriceFeedAddLiquidity,
    PriceFeedRemoveLiquidity,
    SwapSide,
)
from primedelta.contracts import (
    ContractRef,
    Contracts,
    CoreContracts,
    StockPools,
)
from primedelta.dex.handlers import (
    PoolNotFound,
    PositionManagerNotConfigured,
    RouterNotConfigured,
    _AMMPoolHandler,
    _DclexPoolHandler,
    _RouterSwapHandler,
)
from primedelta.types import AccountStatus


_USER_ADDRESS = "0x" + "B" * 40
_USDC_ADDRESS = "0x" + "1" * 40
_VAULT_ADDRESS = "0x" + "2" * 40
_FACTORY_ADDRESS = "0x" + "3" * 40
_DID_ADDRESS = "0x" + "4" * 40
_ROUTER_ADDRESS = "0x" + "5" * 40
_NPM_ADDRESS = "0x" + "6" * 40
_AAPL_TOKEN = "0x" + "A" * 40
_DCLEX_POOL = "0x" + "C" * 40
_AMM_POOL = "0x" + "D" * 40


def _ref(address: str) -> ContractRef:
    return ContractRef(address=address, abi=[])


def _contracts(*, with_router: bool = True, with_npm: bool = True) -> Contracts:
    core = CoreContracts(
        usdc=_ref(_USDC_ADDRESS),
        vault=_ref(_VAULT_ADDRESS),
        factory=_ref(_FACTORY_ADDRESS),
        digital_identity=_ref(_DID_ADDRESS),
        dex_router=_ref(_ROUTER_ADDRESS) if with_router else None,
        position_manager=_ref(_NPM_ADDRESS) if with_npm else None,
    )
    return Contracts(
        chain_id=31337,
        core=core,
        pool_abis={"dclex_pool": [], "univ3_pool": []},
        pools={
            "AAPL": StockPools(
                symbol="AAPL",
                stock_token_address=_AAPL_TOKEN,
                pool_addresses=[_DCLEX_POOL, _AMM_POOL],
            ),
        },
    )


def _make_web3_mock() -> MagicMock:
    web3 = MagicMock()
    web3.to_checksum_address.side_effect = lambda a: a
    web3.eth.get_block.return_value = {"timestamp": 1_700_000_000}
    return web3


def _make_account() -> MagicMock:
    acct = MagicMock()
    acct.address = _USER_ADDRESS
    return acct


class TestRouterSwapHandler:
    def test_swap_exact_input_usdc_to_stock_approves_and_calls_buy_exact_input(self):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        pyth_data = [b"\xde\xad"]
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            signed_prices_fetcher=lambda symbols: pyth_data,
            send_tx=send_tx,
        )

        tx = handler.swap_exact_input(
            "AAPL",
            SwapSide.USDC_TO_STOCK,
            amount_in=Decimal("100"),
            min_amount_out=Decimal("0.5"),
        )

        assert tx == "0xTX"
        assert send_tx.call_count == 2

        usdc_contract = web3.eth.contract.return_value
        usdc_contract.functions.approve.assert_called_once_with(
            _ROUTER_ADDRESS, 100 * 10**6
        )
        usdc_contract.functions.buyExactInput.assert_called_once_with(
            _AAPL_TOKEN,
            100 * 10**6,
            int(Decimal("0.5") * 10**18),
            1_700_000_000 + 600,
            pyth_data,
        )

    def test_swap_exact_input_stock_to_usdc_approves_stock_and_calls_sell(self):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            signed_prices_fetcher=lambda symbols: [b""],
            send_tx=send_tx,
        )

        tx = handler.swap_exact_input(
            "AAPL",
            SwapSide.STOCK_TO_USDC,
            amount_in=Decimal("2"),
            min_amount_out=Decimal("100"),
        )

        assert tx == "0xTX"
        contract = web3.eth.contract.return_value
        contract.functions.approve.assert_called_once_with(
            _ROUTER_ADDRESS, 2 * 10**18
        )
        contract.functions.sellExactInput.assert_called_once_with(
            _AAPL_TOKEN,
            2 * 10**18,
            100 * 10**6,
            1_700_000_000 + 600,
            [b""],
        )

    def test_swap_exact_output_usdc_to_stock_uses_max_in_for_approval(self):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            signed_prices_fetcher=lambda symbols: [b""],
            send_tx=send_tx,
        )

        handler.swap_exact_output(
            "AAPL",
            SwapSide.USDC_TO_STOCK,
            amount_out=Decimal("1"),
            max_amount_in=Decimal("250"),
        )

        contract = web3.eth.contract.return_value
        contract.functions.approve.assert_called_once_with(
            _ROUTER_ADDRESS, 250 * 10**6
        )
        contract.functions.buyExactOutput.assert_called_once_with(
            _AAPL_TOKEN, 1 * 10**18, 250 * 10**6, 1_700_000_000 + 600, [b""]
        )

    def test_swap_passes_pyth_value(self):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            signed_prices_fetcher=lambda symbols: [b""],
            send_tx=send_tx,
        )

        handler.swap_exact_input(
            "AAPL",
            SwapSide.USDC_TO_STOCK,
            amount_in=Decimal("100"),
            min_amount_out=Decimal("0.5"),
            pyth_value=42,
        )

        # Last send_tx call (the swap, not the approve) carried the value kwarg
        last_call = send_tx.call_args_list[-1]
        assert last_call.kwargs.get("value") == 42

    def test_swap_raises_when_router_not_configured(self):
        web3 = _make_web3_mock()
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(with_router=False),
            signed_prices_fetcher=lambda symbols: [b""],
            send_tx=MagicMock(),
        )

        with pytest.raises(RouterNotConfigured):
            handler.swap_exact_input(
                "AAPL",
                SwapSide.USDC_TO_STOCK,
                amount_in=Decimal("1"),
                min_amount_out=Decimal("0"),
            )

    def test_swap_raises_when_symbol_unknown(self):
        web3 = _make_web3_mock()
        handler = _RouterSwapHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            signed_prices_fetcher=lambda symbols: [b""],
            send_tx=MagicMock(),
        )

        with pytest.raises(PoolNotFound):
            handler.swap_exact_input(
                "UNKNOWN",
                SwapSide.USDC_TO_STOCK,
                amount_in=Decimal("1"),
                min_amount_out=Decimal("0"),
            )


class TestDclexHandlerLiquidity:
    def _setup(self):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        contract = MagicMock()
        web3.eth.contract.return_value = contract
        contract.functions.stockTokenToPool.return_value.call.return_value = _DCLEX_POOL

        handler = _DclexPoolHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            send_tx=send_tx,
        )
        return handler, web3, contract, send_tx

    def test_add_liquidity_approves_caps_and_calls_pool(self):
        handler, web3, contract, send_tx = self._setup()

        params = PriceFeedAddLiquidity(
            symbol="AAPL",
            liquidity_amount=Decimal(30 * 10**18),
            max_stock_amount=Decimal("10"),
            max_usdc_amount=Decimal("20"),
        )
        tx = handler.add_liquidity(params)

        assert tx == "0xTX"
        contract.functions.addLiquidity.assert_called_once_with(30 * 10**18)
        approve_args = [a.args for a in contract.functions.approve.call_args_list]
        assert (_DCLEX_POOL, 10 * 10**18) in approve_args
        assert (_DCLEX_POOL, 20 * 10**6) in approve_args

    def test_remove_liquidity_calls_pool_remove(self):
        handler, web3, contract, send_tx = self._setup()

        params = PriceFeedRemoveLiquidity(
            symbol="AAPL", liquidity_amount=Decimal(5 * 10**18)
        )
        tx = handler.remove_liquidity(params)
        assert tx == "0xTX"
        contract.functions.removeLiquidity.assert_called_once_with(5 * 10**18)

    def test_lookup_raises_when_router_returns_zero(self):
        handler, web3, contract, _ = self._setup()
        contract.functions.stockTokenToPool.return_value.call.return_value = (
            "0x" + "0" * 40
        )

        with pytest.raises(PoolNotFound):
            handler.add_liquidity(
                PriceFeedAddLiquidity(
                    symbol="AAPL",
                    liquidity_amount=Decimal(1),
                    max_stock_amount=Decimal("1000"),
                    max_usdc_amount=Decimal("1000"),
                )
            )


class TestAMMHandlerLiquidity:
    def _setup(self, *, token0=_USDC_ADDRESS, token1=_AAPL_TOKEN, fee=3000):
        web3 = _make_web3_mock()
        send_tx = MagicMock(return_value="0xTX")
        contract = MagicMock()
        web3.eth.contract.return_value = contract

        contract.functions.stockToAMMPool.return_value.call.return_value = _AMM_POOL
        contract.functions.token0.return_value.call.return_value = token0
        contract.functions.token1.return_value.call.return_value = token1
        contract.functions.fee.return_value.call.return_value = fee
        contract.encodeABI.side_effect = lambda fn_name, args: f"0x{fn_name}".encode()

        handler = _AMMPoolHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(),
            send_tx=send_tx,
        )
        return handler, web3, contract, send_tx

    def test_add_liquidity_orders_tokens_correctly_when_stock_is_token1(self):
        handler, web3, contract, send_tx = self._setup(
            token0=_USDC_ADDRESS, token1=_AAPL_TOKEN
        )
        params = AMMAddLiquidity(
            symbol="AAPL",
            tick_lower=-100,
            tick_upper=100,
            amount_stock_desired=Decimal("2"),
            amount_usdc_desired=Decimal("400"),
            amount_stock_min=Decimal("1.9"),
            amount_usdc_min=Decimal("390"),
        )
        handler.add_liquidity(params)

        mint_args = contract.functions.mint.call_args.args[0]
        assert mint_args["token0"] == _USDC_ADDRESS
        assert mint_args["token1"] == _AAPL_TOKEN
        assert mint_args["fee"] == 3000
        assert mint_args["amount0Desired"] == 400 * 10**6
        assert mint_args["amount1Desired"] == 2 * 10**18
        assert mint_args["amount0Min"] == 390 * 10**6
        assert mint_args["amount1Min"] == int(Decimal("1.9") * 10**18)
        assert mint_args["recipient"] == _USER_ADDRESS

    def test_add_liquidity_orders_tokens_correctly_when_stock_is_token0(self):
        handler, web3, contract, send_tx = self._setup(
            token0=_AAPL_TOKEN, token1=_USDC_ADDRESS
        )
        params = AMMAddLiquidity(
            symbol="AAPL",
            tick_lower=-100,
            tick_upper=100,
            amount_stock_desired=Decimal("2"),
            amount_usdc_desired=Decimal("400"),
            amount_stock_min=Decimal("1.9"),
            amount_usdc_min=Decimal("390"),
        )
        handler.add_liquidity(params)

        mint_args = contract.functions.mint.call_args.args[0]
        assert mint_args["amount0Desired"] == 2 * 10**18
        assert mint_args["amount1Desired"] == 400 * 10**6

    def test_remove_liquidity_uses_multicall(self):
        handler, web3, contract, send_tx = self._setup()
        params = AMMRemoveLiquidity(
            position_id=42,
            liquidity=10**18,
            amount_stock_min=Decimal("0"),
            amount_usdc_min=Decimal("0"),
        )
        handler.remove_liquidity(params)
        contract.functions.multicall.assert_called_once()
        calls_arg = contract.functions.multicall.call_args.args[0]
        assert len(calls_arg) == 2
        assert b"decreaseLiquidity" in calls_arg[0]
        assert b"collect" in calls_arg[1]

    def test_collect_fees_calls_collect(self):
        handler, web3, contract, send_tx = self._setup()
        handler.collect_fees(99)
        collect_args = contract.functions.collect.call_args.args[0]
        assert collect_args["tokenId"] == 99
        assert collect_args["recipient"] == _USER_ADDRESS
        assert collect_args["amount0Max"] == (1 << 128) - 1

    def test_amm_raises_when_npm_not_configured(self):
        web3 = _make_web3_mock()
        handler = _AMMPoolHandler(
            web3=web3,
            account=_make_account(),
            contracts_provider=lambda: _contracts(with_npm=False),
            send_tx=MagicMock(),
        )
        with pytest.raises(PositionManagerNotConfigured):
            handler.collect_fees(1)


def _make_primedelta() -> PrimeDelta:
    with patch("primedelta.primedelta.Web3"):
        return PrimeDelta(
            private_key="0x" + "1" * 64,
            web3_provider_url="http://localhost:8545",
        )


class TestDispatcher:
    def test_swap_exact_input_routes_to_router_swapper(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.DID_MINTED,
        ), patch.object(
            primedelta._router_swapper, "swap_exact_input", return_value="0xTX"
        ) as mock_swap:
            tx = primedelta.swap_exact_input(
                "AAPL", SwapSide.USDC_TO_STOCK, Decimal("100"), Decimal("0.5")
            )
        assert tx == "0xTX"
        mock_swap.assert_called_once_with(
            "AAPL", SwapSide.USDC_TO_STOCK, Decimal("100"), Decimal("0.5"), 600, 0
        )

    def test_swap_exact_output_routes_to_router_swapper(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.DID_MINTED,
        ), patch.object(
            primedelta._router_swapper, "swap_exact_output", return_value="0xTX"
        ) as mock_swap:
            tx = primedelta.swap_exact_output(
                "AAPL", SwapSide.STOCK_TO_USDC, Decimal("100"), Decimal("3")
            )
        assert tx == "0xTX"
        mock_swap.assert_called_once()

    def test_add_liquidity_dispatches_by_params_pool_type(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.DID_MINTED,
        ), patch.object(
            primedelta._dclex_handler, "add_liquidity", return_value="0xPF"
        ) as mock_pf, patch.object(
            primedelta._amm_handler, "add_liquidity", return_value="0xAMM"
        ) as mock_amm:
            pf_params = PriceFeedAddLiquidity(
                symbol="AAPL",
                liquidity_amount=Decimal("1"),
                max_stock_amount=Decimal("1"),
                max_usdc_amount=Decimal("100"),
            )
            assert primedelta.add_liquidity(pf_params) == "0xPF"
            mock_pf.assert_called_once_with(pf_params)
            mock_amm.assert_not_called()

            amm_params = AMMAddLiquidity(
                symbol="AAPL",
                tick_lower=-100,
                tick_upper=100,
                amount_stock_desired=Decimal("1"),
                amount_usdc_desired=Decimal("100"),
                amount_stock_min=Decimal("0.9"),
                amount_usdc_min=Decimal("90"),
            )
            assert primedelta.add_liquidity(amm_params) == "0xAMM"
            mock_amm.assert_called_once_with(amm_params)


class TestAuthGates:
    def test_swap_requires_did_minted(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.VERIFIED,
        ):
            with pytest.raises(AccountNotVerified):
                primedelta.swap_exact_input(
                    "AAPL", SwapSide.USDC_TO_STOCK, Decimal("1"), Decimal("0")
                )

    def test_add_liquidity_requires_did_minted(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.NOT_VERIFIED,
        ):
            with pytest.raises(AccountNotVerified):
                primedelta.add_liquidity(
                    PriceFeedAddLiquidity(
                        symbol="AAPL",
                        liquidity_amount=Decimal("1"),
                        max_stock_amount=Decimal("1"),
                        max_usdc_amount=Decimal("100"),
                    )
                )

    def test_remove_liquidity_skips_auth_gate(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client, "get_account_status"
        ) as mock_status, patch.object(
            primedelta._dclex_handler, "remove_liquidity", return_value="0xTX"
        ):
            tx = primedelta.remove_liquidity(
                PriceFeedRemoveLiquidity(symbol="AAPL", liquidity_amount=Decimal("1"))
            )
        assert tx == "0xTX"
        mock_status.assert_not_called()

    def test_collect_fees_requires_did_minted(self):
        primedelta = _make_primedelta()
        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.VERIFIED,
        ):
            with pytest.raises(AccountNotVerified):
                primedelta.collect_fees(1)
