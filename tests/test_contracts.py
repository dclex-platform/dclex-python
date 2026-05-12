from unittest.mock import patch

import pytest

from primedelta import PrimeDelta
from primedelta.contracts import Contracts, ContractRef


_DCLEX_POOL_ABI = [{"type": "function", "name": "swapExactInput"}]
_UNIV3_POOL_ABI = [{"type": "function", "name": "swap"}]


def _core_payload() -> dict:
    return {
        "usdc": {"address": "0xUSDC", "abi": [{"type": "function", "name": "transfer"}]},
        "vault": {"address": "0xVAULT", "abi": [{"type": "function", "name": "withdraw"}]},
        "factory": {"address": "0xFACTORY", "abi": [{"type": "function", "name": "burnStocks"}]},
        "digitalIdentity": {"address": "0xDID", "abi": [{"type": "function", "name": "mint"}]},
        "dexRouter": {"address": "", "abi": []},
        "positionManager": {"address": "", "abi": []},
    }


def _sample_payload() -> dict:
    return {
        "chainId": 2028,
        "core": _core_payload(),
        "poolAbis": {},
        "pools": [],
    }


def _payload_with_pools() -> dict:
    return {
        "chainId": 2028,
        "core": {
            **_core_payload(),
            "dexRouter": {"address": "0xROUTER", "abi": []},
            "positionManager": {"address": "0xNPM", "abi": []},
        },
        "poolAbis": {
            "dclex_pool": _DCLEX_POOL_ABI,
            "univ3_pool": _UNIV3_POOL_ABI,
        },
        "pools": [
            {
                "symbol": "AAPL",
                "stockTokenAddress": "0xAAPL",
                "poolAddresses": ["0xAAPL_PF", "0xAAPL_AMM"],
            },
            {
                "symbol": "TSLA",
                "stockTokenAddress": "0xTSLA",
                "poolAddresses": ["0xTSLA_PF"],
            },
        ],
    }


class TestContractsParsing:
    def test_parses_core_contracts(self):
        contracts = Contracts.from_dict(_sample_payload())

        assert contracts.chain_id == 2028
        assert contracts.core.usdc == ContractRef(
            address="0xUSDC", abi=[{"type": "function", "name": "transfer"}]
        )
        assert contracts.core.vault.address == "0xVAULT"
        assert contracts.core.factory.address == "0xFACTORY"
        assert contracts.core.digital_identity.address == "0xDID"

    def test_dex_router_optional_when_address_empty(self):
        contracts = Contracts.from_dict(_sample_payload())
        assert contracts.core.dex_router is None
        assert contracts.core.position_manager is None

    def test_dex_router_parsed_when_present(self):
        contracts = Contracts.from_dict(_payload_with_pools())
        assert contracts.core.dex_router is not None
        assert contracts.core.dex_router.address == "0xROUTER"
        assert contracts.core.position_manager is not None
        assert contracts.core.position_manager.address == "0xNPM"

    def test_contracts_is_frozen(self):
        contracts = Contracts.from_dict(_sample_payload())
        with pytest.raises(Exception):
            contracts.chain_id = 9999  # type: ignore[misc]

    def test_missing_core_key_raises(self):
        payload = _sample_payload()
        del payload["core"]["vault"]
        with pytest.raises(KeyError):
            Contracts.from_dict(payload)

    def test_missing_chain_id_raises(self):
        payload = _sample_payload()
        del payload["chainId"]
        with pytest.raises(KeyError):
            Contracts.from_dict(payload)


class TestPoolParsing:
    def test_pools_keyed_by_symbol(self):
        contracts = Contracts.from_dict(_payload_with_pools())

        assert set(contracts.pools) == {"AAPL", "TSLA"}
        aapl = contracts.pools["AAPL"]
        assert aapl.stock_token_address == "0xAAPL"
        assert aapl.pool_addresses == ["0xAAPL_PF", "0xAAPL_AMM"]

    def test_pool_abis_passed_through(self):
        contracts = Contracts.from_dict(_payload_with_pools())

        assert contracts.pool_abis["dclex_pool"] == _DCLEX_POOL_ABI
        assert contracts.pool_abis["univ3_pool"] == _UNIV3_POOL_ABI

    def test_empty_pools_default(self):
        contracts = Contracts.from_dict(_sample_payload())
        assert contracts.pools == {}
        assert contracts.pool_abis == {}


class TestPrimeDeltaContractsLoading:
    def test_lazy_fetch_and_cache(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "get_contracts",
            return_value=_sample_payload(),
        ) as mock_fetch:
            first = primedelta._get_contracts()
            second = primedelta._get_contracts()

        assert first is second
        assert isinstance(first, Contracts)
        assert first.chain_id == 2028
        mock_fetch.assert_called_once()

    def test_initial_state_is_unloaded(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        assert primedelta._contracts is None
