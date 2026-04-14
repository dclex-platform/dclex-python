from decimal import Decimal
from unittest.mock import MagicMock, patch

from primedelta import PrimeDelta
from primedelta.primedelta_client import PrimeDeltaClient
from primedelta.types import Price


class TestGetPythFeedIds:
    def test_returns_feed_ids_for_valid_symbols(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "abc123",
                "attributes": {
                    "symbol": "Equity.US.AAPL/USD",
                    "base": "AAPL",
                },
            },
            {
                "id": "def456",
                "attributes": {
                    "symbol": "Equity.US.AAPL.PRE/USD",
                    "base": "AAPL",
                },
            },
        ]

        with patch("requests.get", return_value=mock_response) as mock_get:
            feed_ids = PrimeDeltaClient.get_pyth_feed_ids(["AAPL"])

        assert feed_ids == {"AAPL": "abc123"}
        mock_get.assert_called_once()

    def test_returns_empty_dict_for_no_matching_feeds(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []

        with patch("requests.get", return_value=mock_response):
            feed_ids = PrimeDeltaClient.get_pyth_feed_ids(["INVALID"])

        assert feed_ids == {}

    def test_filters_out_pre_post_market_feeds(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "pre123",
                "attributes": {
                    "symbol": "Equity.US.AAPL.PRE/USD",
                    "base": "AAPL",
                },
            },
            {
                "id": "post456",
                "attributes": {
                    "symbol": "Equity.US.AAPL.POST/USD",
                    "base": "AAPL",
                },
            },
        ]

        with patch("requests.get", return_value=mock_response):
            feed_ids = PrimeDeltaClient.get_pyth_feed_ids(["AAPL"])

        assert feed_ids == {}


class TestPythPricesStream:
    def test_yields_price_objects(self):
        client = PrimeDeltaClient()
        mock_feed_ids = {"AAPL": "abc123"}

        mock_sse_message = MagicMock()
        mock_sse_message.data = '{"parsed": [{"id": "abc123", "price": {"price": "25821026", "expo": -5, "publish_time": 1700000000}}]}'

        with patch.object(
            PrimeDeltaClient, "get_pyth_feed_ids", return_value=mock_feed_ids
        ):
            with patch(
                "primedelta.primedelta_client.SSEClient", return_value=[mock_sse_message]
            ):
                prices = list(client.pyth_prices_stream(["AAPL"]))

        assert len(prices) == 1
        assert prices[0].symbol == "AAPL"
        assert prices[0].last_price == Decimal("258.21026")
        assert prices[0].percentage_change == Decimal(0)

    def test_returns_early_when_no_feed_ids(self):
        client = PrimeDeltaClient()

        with patch.object(PrimeDeltaClient, "get_pyth_feed_ids", return_value={}):
            prices = list(client.pyth_prices_stream(["INVALID"]))

        assert prices == []

    def test_skips_empty_sse_messages(self):
        client = PrimeDeltaClient()
        mock_feed_ids = {"AAPL": "abc123"}

        empty_message = MagicMock()
        empty_message.data = ""

        valid_message = MagicMock()
        valid_message.data = '{"parsed": [{"id": "abc123", "price": {"price": "25821026", "expo": -5, "publish_time": 1700000000}}]}'

        with patch.object(
            PrimeDeltaClient, "get_pyth_feed_ids", return_value=mock_feed_ids
        ):
            with patch(
                "primedelta.primedelta_client.SSEClient",
                return_value=[empty_message, valid_message],
            ):
                prices = list(client.pyth_prices_stream(["AAPL"]))

        assert len(prices) == 1

    def test_handles_malformed_json_gracefully(self):
        client = PrimeDeltaClient()
        mock_feed_ids = {"AAPL": "abc123"}

        bad_message = MagicMock()
        bad_message.data = "not json"

        with patch.object(
            PrimeDeltaClient, "get_pyth_feed_ids", return_value=mock_feed_ids
        ):
            with patch(
                "primedelta.primedelta_client.SSEClient", return_value=[bad_message]
            ):
                prices = list(client.pyth_prices_stream(["AAPL"]))

        assert prices == []


class TestPricesStreamAutoSwitch:
    def test_uses_broker_api_when_logged_in(self):
        mock_token = "test_token"
        mock_price = Price(
            symbol="AAPL",
            last_price=Decimal("150.00"),
            timestamp=MagicMock(),
            percentage_change=Decimal("1.5"),
        )

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64, web3_provider_url="http://localhost:8545"
            )

        with patch.object(primedelta, "logged_in", return_value=True):
            with patch.object(
                primedelta._primedelta_client,
                "prices_stream_access_token",
                return_value=mock_token,
            ) as mock_token_method:
                with patch.object(
                    primedelta._primedelta_client,
                    "prices_stream",
                    return_value=iter([mock_price]),
                ) as mock_stream:
                    prices = list(primedelta.prices_stream())

        mock_token_method.assert_called_once()
        mock_stream.assert_called_once_with(mock_token)
        assert len(prices) == 1

    def test_uses_pyth_when_not_logged_in(self):
        mock_price = Price(
            symbol="AAPL",
            last_price=Decimal("150.00"),
            timestamp=MagicMock(),
            percentage_change=Decimal(0),
        )

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64, web3_provider_url="http://localhost:8545"
            )

        with patch.object(primedelta, "logged_in", return_value=False):
            with patch.object(
                primedelta._primedelta_client, "stocks", return_value={"AAPL": MagicMock()}
            ):
                with patch.object(
                    primedelta._primedelta_client,
                    "pyth_prices_stream",
                    return_value=iter([mock_price]),
                ) as mock_pyth:
                    prices = list(primedelta.prices_stream())

        mock_pyth.assert_called_once_with(["AAPL"])
        assert len(prices) == 1

    def test_uses_provided_symbols_when_not_logged_in(self):
        mock_price = Price(
            symbol="TSLA",
            last_price=Decimal("200.00"),
            timestamp=MagicMock(),
            percentage_change=Decimal(0),
        )

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64, web3_provider_url="http://localhost:8545"
            )

        with patch.object(primedelta, "logged_in", return_value=False):
            with patch.object(
                primedelta._primedelta_client,
                "pyth_prices_stream",
                return_value=iter([mock_price]),
            ) as mock_pyth:
                prices = list(primedelta.prices_stream(symbols=["TSLA", "MSFT"]))

        mock_pyth.assert_called_once_with(["TSLA", "MSFT"])


class TestPythPricesStreamDirect:
    def test_pyth_prices_stream_method(self):
        mock_price = Price(
            symbol="AAPL",
            last_price=Decimal("150.00"),
            timestamp=MagicMock(),
            percentage_change=Decimal(0),
        )

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64, web3_provider_url="http://localhost:8545"
            )

        with patch.object(
            primedelta._primedelta_client, "stocks", return_value={"AAPL": MagicMock()}
        ):
            with patch.object(
                primedelta._primedelta_client,
                "pyth_prices_stream",
                return_value=iter([mock_price]),
            ) as mock_pyth:
                prices = list(primedelta.pyth_prices_stream())

        mock_pyth.assert_called_once_with(["AAPL"])

    def test_pyth_prices_stream_with_explicit_symbols(self):
        mock_price = Price(
            symbol="GOOGL",
            last_price=Decimal("140.00"),
            timestamp=MagicMock(),
            percentage_change=Decimal(0),
        )

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64, web3_provider_url="http://localhost:8545"
            )

        with patch.object(
            primedelta._primedelta_client,
            "pyth_prices_stream",
            return_value=iter([mock_price]),
        ) as mock_pyth:
            prices = list(primedelta.pyth_prices_stream(symbols=["GOOGL"]))

        mock_pyth.assert_called_once_with(["GOOGL"])
