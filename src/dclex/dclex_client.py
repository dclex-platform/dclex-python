import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import requests
from sseclient import SSEClient

from dclex.settings import DCLEX_BASE_URL
from dclex.types import (
    AccountStatus,
    ClaimableWithdrawal,
    DepositStocksSignature,
    DigitalIdentitySignature,
    Order,
    OrderSide,
    OrderStatus,
    Portfolio,
    Position,
    Price,
    Stock,
    TransactionType,
    Transfer,
    TransferHistoryStatus,
)


class NotLoggedIn(Exception):
    pass


class AuthorizationError(Exception):
    pass


class APIError(Exception):
    def __init__(self, error_code: str):
        self.error_code = error_code


class UserSignedMessageVerificationError(Exception):
    pass


class DclexClient:
    def __init__(self) -> None:
        self._token = None

    def get_nonce(self) -> str:
        response = requests.get(f"{DCLEX_BASE_URL}/users/nonce/")
        response.raise_for_status()
        return response.json()["nonce"]

    def login(self, message: str, signature: str, nonce: str) -> None:
        response = requests.post(
            f"{DCLEX_BASE_URL}/users/verify/",
            data={"message": message, "signature": signature, "nonce": nonce},
        )
        if response.status_code == 400:
            if response.json().get("errorCode") == "MESSAGE_VERIFICATION_ERROR":
                raise UserSignedMessageVerificationError()
        response.raise_for_status()

        self._token = response.json()["token"]

    def logout(self) -> None:
        self._authorized_post("/logout/", {})
        self._token = None

    def get_account_status(self) -> AccountStatus:
        response = requests.get(
            f"{DCLEX_BASE_URL}/verification-status/",
            headers={"Authorization": f"Token {self._token}"},
        )
        if response.status_code == 401:
            raise NotLoggedIn()
        response.raise_for_status()

        return AccountStatus(response.json()["status"])

    def get_pending_transfers(self, page: int = 1, size: int = 100) -> list[Transfer]:
        response = self._authorized_get("/pending-transfers/", {})
        items = [
            Transfer(
                transaction_id=item["transactionId"],
                amount=Decimal(item["amount"]),
                symbol=item["symbol"],
                type=TransactionType(item["type"]),
                status=TransferHistoryStatus(item["status"]),
            )
            for item in response["items"]
        ]
        if page * size < response["total"]:
            items += self.get_pending_transfers(page + 1, size)
        return items

    def get_closed_transfers(self, page: int = 1, size: int = 100) -> list[Transfer]:
        response = self._authorized_get("/closed-transfers/", {})
        items = [
            Transfer(
                transaction_id=item["transactionId"],
                amount=Decimal(item["amount"]),
                symbol=item["symbol"],
                type=TransactionType(item["type"]),
                status=TransferHistoryStatus(item["status"]),
            )
            for item in response["items"]
        ]
        if page * size < response["total"]:
            items += self.get_pending_transfers(page + 1, size)
        return items

    def create_digital_identity_signature(self) -> DigitalIdentitySignature:
        response = self._authorized_post("/digital-identity-signature/", {})
        return DigitalIdentitySignature(
            signature=response["signature"],
            nonce=response["nonce"],
            nationality=response["nationality"],
        )

    def cancel_order(self, order_id: int) -> None:
        self._authorized_delete(f"/open-orders/{order_id}/")

    def open_orders(self, page: int = 1, size: int = 100) -> list[Order]:
        response = self._authorized_get("/open-orders/", {"page": page, "size": size})
        items = [
            Order(
                id=item["id"],
                order_side=OrderSide(item["actionType"]),
                type=item["type"],
                symbol=item["stockSymbol"],
                quantity=int(Decimal(item["quantity"])),
                price=Decimal(item["price"]),
                status=OrderStatus(item["status"]),
                date_of_cancellation=(
                    date.fromisoformat(item["dateOfCancellation"])
                    if item["dateOfCancellation"]
                    else None
                ),
            )
            for item in response["items"]
        ]
        if page * size < response["total"]:
            items += self.open_orders(page + 1, size)
        return items

    def closed_orders(self, page: int = 1, size: int = 100) -> list[Order]:
        response = self._authorized_get("/closed-orders/", {"page": page, "size": size})
        items = [
            Order(
                id=item["id"],
                order_side=OrderSide(item["actionType"]),
                type=item["type"],
                symbol=item["stockSymbol"],
                quantity=int(Decimal(item["quantity"])),
                price=Decimal(item["price"]) if item["price"] is not None else None,
                status=OrderStatus(item["status"]),
                date_of_cancellation=(
                    date.fromisoformat(item["dateOfCancellation"])
                    if item["dateOfCancellation"]
                    else None
                ),
            )
            for item in response["items"]
        ]
        if page * size < response["total"]:
            items += self.closed_orders(page + 1, size)
        return items

    def get_deposit_stocks_signature(
        self, amount: int, symbol: str
    ) -> DepositStocksSignature:
        response = self._authorized_post(
            "/deposit-stocks-signature/", {"amount": str(amount), "symbol": symbol}
        )
        return DepositStocksSignature(
            signature=response["signature"],
            nonce=response["nonce"],
        )

    def initialize_usdc_withdrawal(self, amount: Decimal) -> int:
        response = self._authorized_post(
            "/initialize-usdc-withdraw/", {"amount": str(amount)}
        )
        return response["withdrawalId"]

    def initialize_stock_withdrawal(self, amount: int, asset_type: str) -> int:
        response = self._authorized_post(
            "/initialize-stocks-withdraw/",
            {"amount": str(amount), "assetType": asset_type},
        )
        return response["withdrawalId"]

    def get_withdraw_signature(self, withdrawal_id: int) -> str:
        response = self._authorized_post(f"/withdraw-signature/{withdrawal_id}/", {})
        return response["signature"]

    def portfolio(self) -> Portfolio:
        response = self._authorized_get("/portfolio/")
        balance = response["balance"]
        positions = response["stocks"]
        return Portfolio(
            available=Decimal(balance["available"]),
            equity=Decimal(balance["equity"]),
            funds=Decimal(balance["funds"]),
            profit_loss=Decimal(balance["profitLoss"]),
            total_value=Decimal(balance["totalValue"]),
            positions=[
                Position(
                    symbol=stock["symbol"],
                    name=stock["name"],
                    total_owned=Decimal(stock["totalOwned"]),
                    available_to_sell=Decimal(stock["availableToSell"]),
                    average_purchase_price=Decimal(stock["averagePurchasePrice"]),
                    last_market_price=Decimal(stock["lastMarketPrice"]),
                    profit_loss=Decimal(stock["profitLoss"]),
                    profit_loss_percentage=Decimal(stock["profitLossPercentage"]),
                    is_offboarded=stock["isOffboarded"],
                    multiplier_numerator=stock["multiplierNumerator"],
                    multiplier_denominator=stock["multiplierDenominator"],
                )
                for stock in positions
            ],
        )

    def claimable_withdrawals(self) -> list[ClaimableWithdrawal]:
        response = self._authorized_get("/claimable-withdrawals/")
        return [
            ClaimableWithdrawal(
                withdrawal_id=item["withdrawalId"],
                amount=Decimal(item["amount"]),
                asset_type=item["assetType"],
            )
            for item in response["items"]
        ]

    def create_limit_order(
        self,
        amount: int,
        asset_type: str,
        order_side: OrderSide,
        price_limit: Decimal,
        date_of_cancellation: Optional[date],
    ) -> int:
        request_data = {
            "amount": str(amount),
            "stockSymbol": asset_type,
            "priceLimit": str(price_limit),
            "dateOfCancellation": (
                str(date_of_cancellation) if date_of_cancellation is not None else None
            ),
        }
        response = self._authorized_post(
            f"/orders/limit/{order_side.value.lower()}/", request_data
        )
        return response["orderId"]

    def create_sell_market_order(
        self,
        amount: int,
        asset_type: str,
    ) -> int:
        response = self._authorized_post(
            "/orders/market/sell/",
            {
                "amount": str(amount),
                "stockSymbol": asset_type,
            },
        )
        return response["orderId"]

    def stocks(self) -> dict[str, Stock]:
        response = requests.get(f"{DCLEX_BASE_URL}/stocks/", {"size": 100})
        response.raise_for_status()
        stocks_data = response.json()["items"]
        return {
            stock["symbol"]: Stock(
                symbol=stock["symbol"],
                name=stock["name"],
                cusip=stock["cusipId"],
                contract_address=stock["smartContractAddress"],
                number_of_tokens_in_circulation=Decimal(stock["numberOfTokens"]),
            )
            for stock in stocks_data
        }

    def market_prices(self):
        response = self._authorized_get("/stocks-prices/", {"size": 100})
        prices_data = response["items"]
        return {
            stock["symbol"]: Price(
                symbol=stock["symbol"],
                last_price=Decimal(stock["price"]["price"]),
                timestamp=self._parse_timestamp(stock["price"]["timestamp"]),
                percentage_change=Decimal(stock["price"]["percentageChange"]),
            )
            for stock in prices_data
        }

    def prices_stream_access_token(self) -> str:
        response = self._authorized_get("/prices-stream-access-token/")
        return response["pricesStreamAccessToken"]

    def prices_stream(self, prices_stream_access_token: str):
        for sse_message in SSEClient(f"{DCLEX_BASE_URL}/prices-stream/", params={"token": prices_stream_access_token}):
            price_data = json.loads(sse_message.data)
            yield Price(
                symbol=price_data["symbol"],
                last_price=Decimal(price_data["price"]),
                timestamp=self._parse_timestamp(price_data["timestamp"]),
                percentage_change=Decimal(price_data["percentageChange"]),
            )

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)

    def _authorized_post(self, endpoint: str, request_data: dict) -> dict:
        response = requests.post(
            f"{DCLEX_BASE_URL}{endpoint}",
            headers={"Authorization": f"Token {self._token}"},
            json=request_data,
        )
        if response.status_code == 400:
            error_code = response.json()["errorCode"]
            raise APIError(error_code)
        elif response.status_code == 401:
            raise NotLoggedIn()
        elif response.status_code == 403:
            raise AuthorizationError()
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    def _authorized_get(
        self, endpoint: str, params: Optional[dict[str, str | int]] = None
    ) -> dict:
        response = requests.get(
            f"{DCLEX_BASE_URL}{endpoint}",
            headers={"Authorization": f"Token {self._token}"},
            params=params,
        )
        if response.status_code == 400:
            error_code = response.json()["errorCode"]
            raise APIError(error_code)
        elif response.status_code == 401:
            raise NotLoggedIn()
        elif response.status_code == 403:
            raise AuthorizationError()
        response.raise_for_status()
        return response.json()

    def _authorized_delete(self, endpoint: str) -> None:
        response = requests.delete(
            f"{DCLEX_BASE_URL}{endpoint}",
            headers={"Authorization": f"Token {self._token}"},
        )
        if response.status_code == 401:
            raise NotLoggedIn()
        response.raise_for_status()
