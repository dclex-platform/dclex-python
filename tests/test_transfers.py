from decimal import Decimal
from time import sleep
from unittest.mock import ANY

import pytest

from dclex.dclex import AccountNotVerified, NotEnoughFunds
from dclex.types import OrderSide, TransactionType, Transfer, TransferHistoryStatus

from .conftest import wait_for_transaction


def test_deposit_and_withdraw_usdc(dclex, provider_url):
    dclex.login()

    usdc_available_balance_before = dclex.get_usdc_available_balance()
    usdc_ledger_balance_before = dclex.get_usdc_ledger_balance()

    tx_hash = dclex.deposit_usdc(amount=Decimal(100))
    wait_for_transaction(tx_hash, provider_url)

    sleep(3)

    assert dclex.get_usdc_ledger_balance() - usdc_ledger_balance_before == 100
    assert dclex.get_usdc_available_balance() - usdc_available_balance_before == 100

    tx_hash = dclex.withdraw_usdc(Decimal(100))
    wait_for_transaction(tx_hash, provider_url)

    sleep(3)

    assert dclex.get_usdc_ledger_balance() == usdc_ledger_balance_before
    assert dclex.get_usdc_available_balance() == usdc_available_balance_before


def test_deposit_usdc_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.deposit_usdc(Decimal(100))


def test_withdraw_usdc_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.withdraw_usdc(Decimal(100))


def test_withdraw_usdc_raises_when_not_enough_funds(dclex, provider_url):
    dclex.login()
    usdc_available_balance = dclex.get_usdc_available_balance()

    with pytest.raises(NotEnoughFunds):
        dclex.withdraw_usdc(Decimal(usdc_available_balance + 1))


def test_withdraw_and_deposit_stock(dclex, provider_url):
    dclex.login()

    tx_hash = dclex.deposit_usdc(Decimal(200))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    dclex.create_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    aapl_available_balance_before = dclex.get_stock_available_balance("AAPL")
    aapl_ledger_balance_before = dclex.get_stock_ledger_balance("AAPL")

    tx_hash = dclex.withdraw_stock_token("AAPL", 1)
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    assert (
        dclex.get_stock_available_balance("AAPL") - aapl_available_balance_before == -1
    )
    assert dclex.get_stock_ledger_balance("AAPL") - aapl_ledger_balance_before == -1

    tx_hash = dclex.deposit_stock_token("AAPL", 1)
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    assert dclex.get_stock_available_balance("AAPL") == aapl_available_balance_before
    assert dclex.get_stock_ledger_balance("AAPL") == aapl_ledger_balance_before


def test_deposit_stock_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.deposit_stock_token("AAPL", Decimal(1))


def test_withdraw_stock_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.withdraw_stock_token("AAPL", Decimal(1))


def test_withdraw_stock_raises_when_not_enough_funds(dclex, provider_url):
    dclex.login()
    available_balance = dclex.get_stock_available_balance("AAPL")

    with pytest.raises(NotEnoughFunds):
        dclex.withdraw_stock_token("AAPL", Decimal(available_balance + 1))


def test_usdc_pending_transfers(dclex, provider_url):
    dclex.login()

    assert dclex.pending_transfers() == []

    tx_hash = dclex.deposit_usdc(Decimal(100))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)
    assert dclex.pending_transfers() == [
        Transfer(
            ANY,
            Decimal(100),
            "USDC",
            TransactionType.DEPOSIT,
            TransferHistoryStatus.PENDING,
        )
    ]

    sleep(10)
    assert dclex.pending_transfers() == []

    tx_hash = dclex.withdraw_usdc(Decimal(100))
    assert dclex.pending_transfers() == [
        Transfer(
            ANY,
            Decimal(100),
            "USDC",
            TransactionType.WITHDRAWAL,
            TransferHistoryStatus.CLAIMABLE,
        )
    ]
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)
    assert dclex.pending_transfers() == []


def test_usdc_closed_transfers(dclex, provider_url):
    dclex.login()
    deposit_tx_hash = dclex.deposit_usdc(Decimal(100))
    wait_for_transaction(deposit_tx_hash, provider_url)
    sleep(2)
    withdrawal_tx_hash = dclex.withdraw_usdc(Decimal(100))
    wait_for_transaction(withdrawal_tx_hash, provider_url)
    sleep(2)

    closed_transfers = {
        transfer.transaction_id: transfer for transfer in dclex.closed_transfers()
    }
    assert closed_transfers[deposit_tx_hash] == Transfer(
        deposit_tx_hash,
        Decimal(100),
        "USDC",
        TransactionType.DEPOSIT,
        TransferHistoryStatus.DONE,
    )
    assert closed_transfers[withdrawal_tx_hash] == Transfer(
        withdrawal_tx_hash,
        Decimal(100),
        "USDC",
        TransactionType.WITHDRAWAL,
        TransferHistoryStatus.DONE,
    )


def test_stock_token_pending_transfers(dclex, provider_url):
    dclex.login()
    wait_for_transaction(dclex.deposit_usdc(Decimal(200)), provider_url)
    sleep(2)
    dclex.create_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    dclex.withdraw_stock_token("AAPL", 1)
    assert dclex.pending_transfers() == [
        Transfer(
            None,
            Decimal(1),
            "AAPL",
            TransactionType.WITHDRAWAL,
            TransferHistoryStatus.CLAIMABLE,
        )
    ]
    sleep(3)

    assert dclex.pending_transfers() == []


def test_stock_token_closed_transfers(dclex, provider_url):
    dclex.login()
    wait_for_transaction(dclex.deposit_usdc(Decimal(200)), provider_url)
    sleep(2)
    dclex.create_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    withdrawal_tx_hash = dclex.withdraw_stock_token("AAPL", 1)
    wait_for_transaction(withdrawal_tx_hash, provider_url)
    sleep(2)
    deposit_tx_hash = dclex.deposit_stock_token("AAPL", 1)
    wait_for_transaction(deposit_tx_hash, provider_url)
    sleep(2)

    closed_transfers = {
        transfer.transaction_id: transfer for transfer in dclex.closed_transfers()
    }
    assert closed_transfers[deposit_tx_hash] == Transfer(
        deposit_tx_hash,
        Decimal(1),
        "AAPL",
        TransactionType.DEPOSIT,
        TransferHistoryStatus.DONE,
    )
    assert closed_transfers[withdrawal_tx_hash] == Transfer(
        withdrawal_tx_hash,
        Decimal(1),
        "AAPL",
        TransactionType.WITHDRAWAL,
        TransferHistoryStatus.DONE,
    )
