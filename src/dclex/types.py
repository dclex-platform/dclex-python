from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class AccountStatus(Enum):
    NOT_VERIFIED = "NOT_VERIFIED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    DID_MINTED = "VERIFIED_MINTED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class TransferHistoryStatus(Enum):
    PENDING = "PENDING"
    CLAIMABLE = "CLAIMABLE"
    REJECTED = "REJECTED"
    DONE = "DONE"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELED = "CANCELED"


@dataclass(frozen=True)
class Transfer:
    transaction_id: str
    amount: Decimal
    symbol: str
    type: TransactionType
    status: TransferHistoryStatus


@dataclass(frozen=True)
class DigitalIdentitySignature:
    signature: str
    nonce: str
    nationality: str


@dataclass(frozen=True)
class DepositStocksSignature:
    signature: str
    nonce: str


@dataclass(frozen=True)
class Order:
    id: int
    order_side: OrderSide
    type: str
    symbol: str
    quantity: int
    status: OrderStatus
    price: Optional[Decimal]
    date_of_cancellation: Optional[date]


@dataclass(frozen=True)
class Position:
    symbol: str
    name: str
    total_owned: Decimal
    available_to_sell: Decimal
    average_purchase_price: Decimal
    last_market_price: Decimal
    profit_loss: Decimal
    profit_loss_percentage: Decimal
    is_offboarded: bool
    multiplier_numerator: int
    multiplier_denominator: int


@dataclass(frozen=True)
class Portfolio:
    available: Decimal
    equity: Decimal
    funds: Decimal
    profit_loss: Decimal
    total_value: Decimal
    positions: list[Position]


@dataclass(frozen=True)
class ClaimableWithdrawal:
    withdrawal_id: int
    amount: Decimal
    asset_type: str


@dataclass(frozen=True)
class Stock:
    symbol: str
    name: str
    cusip: str
    contract_address: str
    number_of_tokens_in_circulation: Decimal


@dataclass(frozen=True)
class Price:
    symbol: str
    last_price: Decimal
    timestamp: datetime
    percentage_change: Decimal
