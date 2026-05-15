from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from primedelta import PrimeDelta, AccountNotVerified, DigitalIdentityAlreadyClaimed
from primedelta.primedelta_client import NotLoggedIn
from primedelta.types import AccountStatus, Portfolio, Position


class TestLogin:
    def test_logged_in_returns_false_when_not_logged_in(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(primedelta._primedelta_client, "get_account_status") as mock:
            mock.side_effect = NotLoggedIn()
            assert not primedelta.logged_in()

    def test_logged_in_returns_true_when_logged_in(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.VERIFIED,
        ):
            assert primedelta.logged_in()

    def test_logout(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(primedelta._primedelta_client, "logout") as mock_logout:
            primedelta.logout()

        mock_logout.assert_called_once()


class TestClaimDigitalIdentity:
    def test_raises_when_user_has_already_claimed_it(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.DID_MINTED,
        ):
            with pytest.raises(DigitalIdentityAlreadyClaimed):
                primedelta.claim_digital_identity()

    def test_raises_when_user_is_not_verified(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "get_account_status",
            return_value=AccountStatus.NOT_VERIFIED,
        ):
            with pytest.raises(AccountNotVerified):
                primedelta.claim_digital_identity()


class TestPortfolio:
    def test_should_get_portfolio(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_portfolio = Portfolio(
            buying_power=Decimal("1000.00"),
            total_equity=Decimal("5000.00"),
            total_funds=Decimal("1000.00"),
            profit_loss=Decimal("100.00"),
            total_value=Decimal("5000.00"),
            positions=[
                Position(
                    symbol="AAPL",
                    name="Apple Inc",
                    total_owned=Decimal("10"),
                    available_to_sell=Decimal("10"),
                    average_purchase_price=Decimal("150.00"),
                    last_market_price=Decimal("160.00"),
                    profit_loss=Decimal("100.00"),
                    profit_loss_percentage=Decimal("6.67"),
                    is_offboarded=False,
                    multiplier_numerator=1,
                    multiplier_denominator=1,
                )
            ],
        )

        with patch.object(
            primedelta._primedelta_client, "portfolio", return_value=mock_portfolio
        ):
            portfolio = primedelta.portfolio()

        assert portfolio.buying_power == Decimal("1000.00")
        assert portfolio.total_equity == Decimal("5000.00")
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"

    def test_raises_when_user_is_not_verified(self):
        from primedelta.primedelta_client import APIError

        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "portfolio",
            side_effect=APIError("ACCOUNT_NOT_FOUND"),
        ):
            with pytest.raises(AccountNotVerified):
                primedelta.portfolio()
