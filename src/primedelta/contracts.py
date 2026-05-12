from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ContractRef:
    address: str
    abi: list[Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractRef":
        return cls(address=data["address"], abi=data["abi"])


@dataclass(frozen=True)
class CoreContracts:
    usdc: ContractRef
    vault: ContractRef
    factory: ContractRef
    digital_identity: ContractRef
    dex_router: Optional[ContractRef] = None
    position_manager: Optional[ContractRef] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoreContracts":
        return cls(
            usdc=ContractRef.from_dict(data["usdc"]),
            vault=ContractRef.from_dict(data["vault"]),
            factory=ContractRef.from_dict(data["factory"]),
            digital_identity=ContractRef.from_dict(data["digitalIdentity"]),
            dex_router=(
                ContractRef.from_dict(data["dexRouter"])
                if data.get("dexRouter") and data["dexRouter"].get("address")
                else None
            ),
            position_manager=(
                ContractRef.from_dict(data["positionManager"])
                if data.get("positionManager") and data["positionManager"].get("address")
                else None
            ),
        )


@dataclass(frozen=True)
class StockPools:
    symbol: str
    stock_token_address: str
    pool_addresses: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StockPools":
        return cls(
            symbol=data["symbol"],
            stock_token_address=data["stockTokenAddress"],
            pool_addresses=list(data["poolAddresses"]),
        )


@dataclass(frozen=True)
class Contracts:
    chain_id: int
    core: CoreContracts
    pool_abis: dict[str, list[Any]] = field(default_factory=dict)
    pools: dict[str, StockPools] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contracts":
        pool_abis = dict(data.get("poolAbis", {}))
        pools_raw = data.get("pools", [])
        pools: dict[str, StockPools] = {}
        for entry in pools_raw:
            stock_pools = StockPools.from_dict(entry)
            pools[stock_pools.symbol] = stock_pools
        return cls(
            chain_id=data["chainId"],
            core=CoreContracts.from_dict(data["core"]),
            pool_abis=pool_abis,
            pools=pools,
        )
