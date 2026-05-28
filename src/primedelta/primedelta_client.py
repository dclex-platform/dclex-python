import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import requests
from sseclient import SSEClient

from primedelta.settings import PRIMEDELTA_BASE_URL, PYTH_HERMES_BASE_URL
from primedelta.types import (
    AccountStatus,
    ClaimableWithdrawal,
    DepositStocksSignature,
    DigitalIdentitySignature,
    Distribution,
    DistributionType,
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


class PrimeDeltaClient:
    def __init__(self) -> None:
        self._token = None

    @staticmethod
    def get_nonce() -> str:
        response = requests.get(f"{PRIMEDELTA_BASE_URL}/users/nonce/")
        response.raise_for_status()
        return response.json()["nonce"]

    def login(self, message: str, signature: str, nonce: str) -> None:
        response = requests.post(
            f"{PRIMEDELTA_BASE_URL}/users/verify/",
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
            f"{PRIMEDELTA_BASE_URL}/verification-status/",
            headers={"Authorization": f"Token {self._token}"},
        )
        if response.status_code == 401:
            raise NotLoggedIn()
        response.raise_for_status()

        return AccountStatus(response.json()["status"])

    def get_pending_transfers(self, page: int, size: int) -> list[Transfer]:
        response = self._authorized_get(
            "/pending-transfers/", {"page": page, "size": size}
        )
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
        return items

    def get_closed_transfers(self, page: int, size: int) -> list[Transfer]:
        response = self._authorized_get(
            "/closed-transfers/", {"page": page, "size": size}
        )
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
        return items

    def get_distributions(self, page: int, size: int) -> list[Distribution]:
        response = self._authorized_get(
            "/closed-distributions/", {"page": page, "size": size}
        )
        items = [
            Distribution(
                amount=Decimal(item["amount"]),
                type=DistributionType(item["type"]),
                stock_symbol=item["stockSymbol"],
                stock_quantity=Decimal(item["quantity"]),
            )
            for item in response["items"]
        ]
        return items

    def create_digital_identity_signature(self) -> DigitalIdentitySignature:
        response = self._authorized_post(
            "/digital-identity-signature/", {"requestedFromLibrary": True}
        )
        return DigitalIdentitySignature(
            signature=response["signature"],
            nonce=response["nonce"],
            data=response["data"],
            is_pro=response["isPro"],
        )

    def cancel_order(self, order_id: int) -> None:
        self._authorized_delete(f"/open-orders/{order_id}/")

    def get_order_status(self, order_id: int) -> OrderStatus:
        response = self._authorized_get(f"/orders/{order_id}/status/")
        return OrderStatus(response["orderStatus"])

    def open_orders(self, page: int, size: int) -> list[Order]:
        response = self._authorized_get("/open-orders/", {"page": page, "size": size})
        items = [
            Order(
                id=item["id"],
                order_side=OrderSide(item["actionType"]),
                type=item["type"],
                symbol=item["stockSymbol"],
                quantity=int(Decimal(item["quantity"])),
                price=Decimal(item["price"]),
                status=OrderStatus.PENDING,  # Open orders are always pending
                date_of_cancellation=(
                    date.fromisoformat(item["dateOfCancellation"])
                    if item["dateOfCancellation"]
                    else None
                ),
            )
            for item in response["items"]
        ]
        return items

    def closed_orders(self, page: int, size: int) -> list[Order]:
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

    def request_stablecoin_withdrawal(self, amount: Decimal) -> int:
        # Backend endpoint name remains "/initialize-usdc-withdraw/" until the
        # backend renames it; the Python method is the SDK's surface.
        response = self._authorized_post(
            "/initialize-usdc-withdraw/", {"amount": str(amount)}
        )
        return response["withdrawalId"]

    def request_stock_withdrawal(self, amount: int, asset_type: str) -> int:
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
            buying_power=Decimal(balance["available"]),
            total_equity=Decimal(balance["equity"]),
            total_funds=Decimal(balance["funds"]),
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

    def send_limit_order(
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

    def send_sell_market_order(
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
        response = requests.get(f"{PRIMEDELTA_BASE_URL}/stocks/", {"size": 100})
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

    def prices_stream_access_token(self) -> str:
        if not self._token:
            raise NotLoggedIn()
        return self._token

    def prices_stream(self, prices_stream_access_token: str):
        for sse_message in SSEClient(
            f"{PRIMEDELTA_BASE_URL}/prices-stream/",
            params={"token": prices_stream_access_token},
        ):
            price_data = json.loads(sse_message.data)
            yield Price(
                symbol=price_data["symbol"],
                last_price=Decimal(price_data["price"]),
                timestamp=self._parse_timestamp(price_data["timestamp"]),
                percentage_change=Decimal(price_data["percentageChange"]),
            )

    @staticmethod
    def is_market_open() -> bool:
        response = requests.get(f"{PRIMEDELTA_BASE_URL}/market-status/")
        response.raise_for_status()
        return response.json()["isMarketOpen"]

    def get_signed_price_updates(self, symbols: list[str]) -> list[bytes]:
        """Fetch FIOracle-format signed price updates from the backend.

        Returns a list of 117-byte packed updates (feedId + price + expo +
        publishTime + v + r + s) ready to pass as `pythUpdateData` to the
        DCLEX router/pool. Skips symbols the backend doesn't have a price for.
        """
        if not symbols:
            return []
        # `/signed-prices/` accepts Bearer auth, unlike most other endpoints
        # which use `Authorization: Token <token>`.
        response = requests.get(
            f"{PRIMEDELTA_BASE_URL}/signed-prices/",
            params={"symbols": ",".join(symbols)},
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if response.status_code == 401:
            raise NotLoggedIn()
        response.raise_for_status()
        return [bytes.fromhex(item["signature"].removeprefix("0x")) for item in response.json()]

    @staticmethod
    def get_pyth_feed_ids(symbols: list[str]) -> dict[str, str]:
        """Fetch Pyth price feed IDs for given stock symbols.

        Returns a mapping of symbol -> pyth_feed_id for regular market hours feeds.
        """
        feed_ids = {}
        for symbol in symbols:
            response = requests.get(
                f"{PYTH_HERMES_BASE_URL}/v2/price_feeds",
                params={"query": symbol, "asset_type": "equity"},
            )
            response.raise_for_status()
            feeds = response.json()

            # Find the regular market hours feed (no suffix like .PRE, .POST, .ON)
            for feed in feeds:
                feed_symbol = feed.get("attributes", {}).get("symbol", "")
                base = feed.get("attributes", {}).get("base", "")
                if base == symbol and feed_symbol == f"Equity.US.{symbol}/USD":
                    feed_ids[symbol] = feed["id"]
                    break

        return feed_ids

    def pyth_prices_stream(self, symbols: list[str]):
        """Stream prices from Pyth Hermes API for given stock symbols.

        This method does not require authentication and can be used when not logged in.
        """
        feed_ids = self.get_pyth_feed_ids(symbols)

        if not feed_ids:
            return

        # Build query string with all feed IDs
        ids_param = "&".join(f"ids[]={fid}" for fid in feed_ids.values())
        stream_url = f"{PYTH_HERMES_BASE_URL}/v2/updates/price/stream?{ids_param}"

        # Create reverse mapping: feed_id -> symbol
        id_to_symbol = {v: k for k, v in feed_ids.items()}

        for sse_message in SSEClient(stream_url):
            if not sse_message.data:
                continue

            try:
                data = json.loads(sse_message.data)
                parsed_prices = data.get("parsed", [])

                for price_data in parsed_prices:
                    feed_id = price_data.get("id", "")
                    symbol = id_to_symbol.get(feed_id)

                    if symbol and "price" in price_data:
                        price_info = price_data["price"]
                        # Convert price using exponent (e.g., price=25821026, expo=-5 -> 258.21026)
                        raw_price = int(price_info["price"])
                        expo = int(price_info["expo"])
                        actual_price = Decimal(raw_price) * Decimal(10) ** expo

                        publish_time = price_info.get("publish_time", 0)
                        timestamp = datetime.fromtimestamp(publish_time, tz=timezone.utc)

                        yield Price(
                            symbol=symbol,
                            last_price=actual_price,
                            timestamp=timestamp,
                            percentage_change=Decimal(0),  # Pyth doesn't provide percentage change
                        )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)

    def _authorized_post(self, endpoint: str, request_data: dict) -> dict:
        response = requests.post(
            f"{PRIMEDELTA_BASE_URL}{endpoint}",
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
            f"{PRIMEDELTA_BASE_URL}{endpoint}",
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
            f"{PRIMEDELTA_BASE_URL}{endpoint}",
            headers={"Authorization": f"Token {self._token}"},
        )
        if response.status_code == 401:
            raise NotLoggedIn()
        response.raise_for_status()
