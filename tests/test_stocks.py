from decimal import Decimal
from unittest.mock import MagicMock, patch

from primedelta import PrimeDelta
from primedelta.types import Stock


class TestStocks:
    def test_stocks_returns_dictionary_of_available_stocks(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_stocks = {
            "AAPL": Stock(
                symbol="AAPL",
                name="Apple Inc",
                cusip="037833100",
                contract_address="0x1234567890123456789012345678901234567890",
                number_of_tokens_in_circulation=Decimal("1000000"),
            ),
            "TSLA": Stock(
                symbol="TSLA",
                name="Tesla Inc",
                cusip="88160R101",
                contract_address="0x0987654321098765432109876543210987654321",
                number_of_tokens_in_circulation=Decimal("500000"),
            ),
        }

        with patch.object(
            primedelta._primedelta_client, "stocks", return_value=mock_stocks
        ):
            stocks = primedelta.stocks()

        assert len(stocks) == 2
        assert "AAPL" in stocks
        assert "TSLA" in stocks
        assert stocks["AAPL"].name == "Apple Inc"
        assert stocks["TSLA"].name == "Tesla Inc"
