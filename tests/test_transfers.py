from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from primedelta import PrimeDelta
from primedelta.primedelta import AccountNotVerified, NotEnoughFunds, WithdrawalNotFound
from primedelta.primedelta_client import APIError
from primedelta.types import (
    AccountStatus,
    ClaimableWithdrawal,
    Distribution,
    DistributionType,
    Transfer,
    TransactionType,
    TransferHistoryStatus,
)


class TestDepositUSDC:
    def test_deposit_usdc_raises_when_user_is_not_verified(self):
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
                primedelta.deposit_usdc(Decimal("100"))


class TestWithdrawUSDC:
    def test_request_usdc_withdrawal(self):
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
            with patch.object(
                primedelta._primedelta_client,
                "request_usdc_withdrawal",
                return_value=123,
            ) as mock_request:
                withdrawal_id = primedelta.request_usdc_withdrawal(Decimal("100"))

        assert withdrawal_id == 123
        mock_request.assert_called_once_with(amount=Decimal("100"))

    def test_request_usdc_withdrawal_raises_when_user_is_not_verified(self):
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
                primedelta.request_usdc_withdrawal(Decimal("100"))

    def test_request_usdc_withdrawal_raises_when_not_enough_funds(self):
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
            with patch.object(
                primedelta._primedelta_client,
                "request_usdc_withdrawal",
                side_effect=APIError("INSUFFICIENT_FUNDS"),
            ):
                with pytest.raises(NotEnoughFunds):
                    primedelta.request_usdc_withdrawal(Decimal("10000"))

    def test_claim_usdc_withdrawal_raises_when_not_found(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "claimable_withdrawals",
            return_value=[],
        ):
            with pytest.raises(WithdrawalNotFound):
                primedelta.claim_usdc_withdrawal(9999)


class TestDepositStock:
    def test_deposit_stock_raises_when_user_is_not_verified(self):
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
                primedelta.deposit_stock_token("AAPL", 1)


class TestWithdrawStock:
    def test_request_stock_withdrawal_raises_when_user_is_not_verified(self):
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
                primedelta.request_stock_withdrawal("AAPL", 1)

    def test_request_stock_withdrawal_raises_when_not_enough_funds(self):
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
            with patch.object(
                primedelta._primedelta_client,
                "request_stock_withdrawal",
                side_effect=APIError("INSUFFICIENT_FUNDS"),
            ):
                with pytest.raises(NotEnoughFunds):
                    primedelta.request_stock_withdrawal("AAPL", 100)

    def test_claim_stock_withdrawal_raises_when_not_found(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        with patch.object(
            primedelta._primedelta_client,
            "claimable_withdrawals",
            return_value=[],
        ):
            with pytest.raises(WithdrawalNotFound):
                primedelta.claim_stock_withdrawal(9999)


class TestPendingTransfers:
    def test_pending_transfers(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_transfers = [
            Transfer(
                transaction_id="0x123",
                amount=Decimal("100"),
                symbol="USDC",
                type=TransactionType.DEPOSIT,
                status=TransferHistoryStatus.PENDING,
            )
        ]

        with patch.object(
            primedelta._primedelta_client,
            "get_pending_transfers",
            return_value=mock_transfers,
        ):
            transfers = primedelta.pending_transfers()

        assert len(transfers) == 1
        assert transfers[0].symbol == "USDC"
        assert transfers[0].status == TransferHistoryStatus.PENDING


class TestClosedTransfers:
    def test_closed_transfers(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_transfers = [
            Transfer(
                transaction_id="0x123",
                amount=Decimal("100"),
                symbol="USDC",
                type=TransactionType.DEPOSIT,
                status=TransferHistoryStatus.DONE,
            ),
            Transfer(
                transaction_id="0x456",
                amount=Decimal("50"),
                symbol="USDC",
                type=TransactionType.WITHDRAWAL,
                status=TransferHistoryStatus.DONE,
            ),
        ]

        with patch.object(
            primedelta._primedelta_client,
            "get_closed_transfers",
            return_value=mock_transfers,
        ):
            transfers = primedelta.closed_transfers()

        assert len(transfers) == 2
        assert transfers[0].type == TransactionType.DEPOSIT
        assert transfers[1].type == TransactionType.WITHDRAWAL


class TestDistributions:
    def test_distributions(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_distributions = [
            Distribution(
                amount=Decimal("10.50"),
                type=DistributionType.DIVIDEND,
                stock_symbol="AAPL",
                stock_quantity=Decimal("100"),
            )
        ]

        with patch.object(
            primedelta._primedelta_client,
            "get_distributions",
            return_value=mock_distributions,
        ):
            distributions = primedelta.distributions()

        assert len(distributions) == 1
        assert distributions[0].stock_symbol == "AAPL"
        assert distributions[0].type == DistributionType.DIVIDEND


class TestClaimableWithdrawals:
    def test_claimable_withdrawals(self):
        with patch("primedelta.primedelta.Web3"):
            primedelta = PrimeDelta(
                private_key="0x" + "1" * 64,
                web3_provider_url="http://localhost:8545",
            )

        mock_withdrawals = [
            ClaimableWithdrawal(
                withdrawal_id=123,
                amount=Decimal("100"),
                asset_type="USDC",
            ),
            ClaimableWithdrawal(
                withdrawal_id=456,
                amount=Decimal("5"),
                asset_type="AAPL",
            ),
        ]

        with patch.object(
            primedelta._primedelta_client,
            "claimable_withdrawals",
            return_value=mock_withdrawals,
        ):
            withdrawals = primedelta.claimable_withdrawals()

        assert len(withdrawals) == 2
        assert withdrawals[0].asset_type == "USDC"
        assert withdrawals[1].asset_type == "AAPL"
