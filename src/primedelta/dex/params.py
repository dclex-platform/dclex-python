from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Union


class PoolType(str, Enum):
    AMM = "AMM"
    PRICE_FEED = "PRICE_FEED"


class SwapSide(str, Enum):
    USDC_TO_STOCK = "USDC_TO_STOCK"
    STOCK_TO_USDC = "STOCK_TO_USDC"


@dataclass(frozen=True)
class PriceFeedAddLiquidity:
    symbol: str
    liquidity_amount: Decimal
    max_stock_amount: Decimal
    max_usdc_amount: Decimal
    pool_type: ClassVar[PoolType] = PoolType.PRICE_FEED


@dataclass(frozen=True)
class AMMAddLiquidity:
    symbol: str
    tick_lower: int
    tick_upper: int
    amount_stock_desired: Decimal
    amount_usdc_desired: Decimal
    amount_stock_min: Decimal
    amount_usdc_min: Decimal
    pool_type: ClassVar[PoolType] = PoolType.AMM


@dataclass(frozen=True)
class PriceFeedRemoveLiquidity:
    symbol: str
    liquidity_amount: Decimal
    pool_type: ClassVar[PoolType] = PoolType.PRICE_FEED


@dataclass(frozen=True)
class AMMRemoveLiquidity:
    position_id: int
    liquidity: int
    amount_stock_min: Decimal
    amount_usdc_min: Decimal
    pool_type: ClassVar[PoolType] = PoolType.AMM


AddLiquidityParams = Union[PriceFeedAddLiquidity, AMMAddLiquidity]
RemoveLiquidityParams = Union[PriceFeedRemoveLiquidity, AMMRemoveLiquidity]
