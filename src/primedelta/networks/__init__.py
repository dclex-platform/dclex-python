"""Bundled contract registry — SDK ships addresses + ABIs locally instead of
fetching `/contracts/` from the backend.

Why local config: the backend's `/contracts/` is wired to env vars whose values
come from a GitOps repo. Those values drift behind contract redeploys, leaving
the served addresses pointing at stale bytecode (whose ABI no longer matches).
Shipping a config file in the SDK lets the user pin addresses without depending
on backend ops cycles.

Edit `<network>.json` to change addresses for that network.
"""
import json
from pathlib import Path
from typing import Any

from primedelta.contracts import ContractRef, Contracts, CoreContracts


_NETWORKS_DIR = Path(__file__).parent
_ABIS_DIR = _NETWORKS_DIR / "abis"

_CORE_ABIS = {
    "stablecoin": "stablecoin.json",
    "vault": "vault.json",
    "factory": "factory.json",
    "digital_identity": "digital_identity.json",
    "dex_router": "dex_router.json",
    "position_manager": "position_manager.json",
    "oracle": "oracle.json",
    "wdel": "wdel.json",
}

_POOL_ABIS = {
    "dclex_pool": "dclex_pool.json",
    "univ3_pool": "univ3_pool.json",
    "univ3_factory": "univ3_factory.json",
    "erc20": "erc20.json",
}


def _read_abi(filename: str) -> list[Any]:
    return json.loads((_ABIS_DIR / filename).read_text())


def _make_ref(address: str, abi_filename: str) -> ContractRef:
    return ContractRef(address=address, abi=_read_abi(abi_filename))


def load(network: str) -> Contracts:
    """Load bundled contract registry for the given network.

    Looks for `<network>.json` alongside this module. Addresses come from that
    file; ABIs come from the `abis/` subdirectory.
    """
    config_path = _NETWORKS_DIR / f"{network}.json"
    if not config_path.exists():
        available = sorted(p.stem for p in _NETWORKS_DIR.glob("*.json"))
        raise ValueError(
            f"Unknown network {network!r}; available: {available}"
        )
    config = json.loads(config_path.read_text())
    core_cfg = config["core"]

    position_manager_addr = core_cfg.get("position_manager") or None
    core = CoreContracts(
        stablecoin=_make_ref(core_cfg["stablecoin"], _CORE_ABIS["stablecoin"]),
        vault=_make_ref(core_cfg["vault"], _CORE_ABIS["vault"]),
        factory=_make_ref(core_cfg["factory"], _CORE_ABIS["factory"]),
        digital_identity=_make_ref(
            core_cfg["digital_identity"], _CORE_ABIS["digital_identity"]
        ),
        dex_router=(
            _make_ref(core_cfg["dex_router"], _CORE_ABIS["dex_router"])
            if core_cfg.get("dex_router")
            else None
        ),
        position_manager=(
            _make_ref(position_manager_addr, _CORE_ABIS["position_manager"])
            if position_manager_addr
            else None
        ),
        oracle=(
            _make_ref(core_cfg["oracle"], _CORE_ABIS["oracle"])
            if core_cfg.get("oracle")
            else None
        ),
        wdel=(
            _make_ref(core_cfg["wdel"], _CORE_ABIS["wdel"])
            if core_cfg.get("wdel")
            else None
        ),
    )
    pool_abis = {key: _read_abi(filename) for key, filename in _POOL_ABIS.items()}
    return Contracts(
        chain_id=config["chain_id"],
        core=core,
        pool_abis=pool_abis,
        pools={},  # Pools are discovered on-chain via Router.allStockTokens().
    )
