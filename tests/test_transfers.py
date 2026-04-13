from decimal import Decimal
from time import sleep
from unittest.mock import ANY

import pytest

from primedelta.primedelta import AccountNotVerified, NotEnoughFunds, WithdrawalNotFound
from primedelta.types import OrderSide, TransactionType, Transfer, TransferHistoryStatus

from .conftest import wait_for_transaction


def test_deposit_and_withdraw_usdc(primedelta, provider_url):
    primedelta.login()

    usdc_available_balance_before = primedelta.get_usdc_available_balance()
    usdc_total_balance_before = primedelta.get_usdc_total_balance()

    # tx_hash = primedelta.deposit_usdc(amount=Decimal(100))
    # wait_for_transaction(tx_hash, provider_url)

    # sleep(3)

    # assert primedelta.get_usdc_total_balance() - usdc_total_balance_before == 100
    # assert primedelta.get_usdc_available_balance() - usdc_available_balance_before == 100

    withdrawal_id = primedelta.request_usdc_withdrawal(Decimal(100))
    tx_hash = primedelta.claim_usdc_withdrawal(withdrawal_id)
    wait_for_transaction(tx_hash, provider_url)

    sleep(15)

    assert primedelta.get_usdc_total_balance() == usdc_total_balance_before - 100
    assert primedelta.get_usdc_available_balance() == usdc_available_balance_before - 100


def test_deposit_usdc_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.deposit_usdc(Decimal(100))


def test_request_usdc_withdrawal_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.request_usdc_withdrawal(Decimal(100))


def test_request_usdc_withdrawal_raises_when_not_enough_funds(primedelta, provider_url):
    primedelta.login()
    usdc_available_balance = primedelta.get_usdc_available_balance()

    with pytest.raises(NotEnoughFunds):
        primedelta.request_usdc_withdrawal(Decimal(usdc_available_balance + 1))


def test_claim_usdc_withdrawal_raises_when_claimable_withdrawal_id_does_not_exist(
    primedelta, provider_url
):
    primedelta.login()
    with pytest.raises(WithdrawalNotFound):
        primedelta.claim_usdc_withdrawal(9999)


def test_withdraw_and_deposit_stock(primedelta, provider_url):
    primedelta.login()

    tx_hash = primedelta.deposit_usdc(Decimal(200))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    aapl_available_balance_before = primedelta.get_stock_available_balance("AAPL")
    aapl_total_balance_before = primedelta.get_stock_total_balance("AAPL")

    withdrawal_id = primedelta.request_stock_withdrawal("AAPL", 1)
    tx_hash = primedelta.claim_stock_withdrawal(withdrawal_id)
    wait_for_transaction(tx_hash, provider_url)
    sleep(20)

    assert (
        primedelta.get_stock_available_balance("AAPL") - aapl_available_balance_before == -1
    )
    assert primedelta.get_stock_total_balance("AAPL") - aapl_total_balance_before == -1

    tx_hash = primedelta.deposit_stock_token("AAPL", 1)
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)

    assert primedelta.get_stock_available_balance("AAPL") == aapl_available_balance_before
    assert primedelta.get_stock_total_balance("AAPL") == aapl_total_balance_before


def test_deposit_stock_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.deposit_stock_token("AAPL", Decimal(1))


def test_request_stock_withdrawal_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.request_stock_withdrawal("AAPL", Decimal(1))


def test_request_stock_withdrawal_raises_when_not_enough_funds(primedelta, provider_url):
    primedelta.login()
    available_balance = primedelta.get_stock_available_balance("AAPL")

    with pytest.raises(NotEnoughFunds):
        primedelta.request_stock_withdrawal("AAPL", available_balance + 1)


def test_claim_stock_withdrawal_raises_when_claimable_withdrawal_id_does_not_exist(
    primedelta, provider_url
):
    primedelta.login()
    with pytest.raises(WithdrawalNotFound):
        primedelta.claim_stock_withdrawal(9999)


def test_usdc_pending_transfers(primedelta, provider_url):
    primedelta.login()

    assert primedelta.pending_transfers() == []

    tx_hash = primedelta.deposit_usdc(Decimal(100))
    wait_for_transaction(tx_hash, provider_url)
    sleep(3)
    assert primedelta.pending_transfers() == [
        Transfer(
            ANY,
            Decimal(100),
            "USDC",
            TransactionType.DEPOSIT,
            TransferHistoryStatus.PENDING,
        )
    ]

    sleep(10)
    assert primedelta.pending_transfers() == []

    tx_hash = primedelta.withdraw_usdc(Decimal(100))
    assert primedelta.pending_transfers() == [
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
    assert primedelta.pending_transfers() == []


def test_usdc_closed_transfers(primedelta, provider_url):
    primedelta.login()
    deposit_tx_hash = primedelta.deposit_usdc(Decimal(100))
    wait_for_transaction(deposit_tx_hash, provider_url)
    sleep(2)
    withdrawal_tx_hash = primedelta.withdraw_usdc(Decimal(100))
    wait_for_transaction(withdrawal_tx_hash, provider_url)
    sleep(2)

    closed_transfers = {
        transfer.transaction_id: transfer for transfer in primedelta.closed_transfers()
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


def test_stock_token_pending_transfers(primedelta, provider_url):
    primedelta.login()
    wait_for_transaction(primedelta.deposit_usdc(Decimal(200)), provider_url)
    sleep(2)
    primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    primedelta.withdraw_stock_token("AAPL", 1)
    assert primedelta.pending_transfers() == [
        Transfer(
            None,
            Decimal(1),
            "AAPL",
            TransactionType.WITHDRAWAL,
            TransferHistoryStatus.CLAIMABLE,
        )
    ]
    sleep(3)

    assert primedelta.pending_transfers() == []


def test_stock_token_closed_transfers(primedelta, provider_url):
    primedelta.login()
    wait_for_transaction(primedelta.deposit_usdc(Decimal(200)), provider_url)
    sleep(2)
    primedelta.send_limit_order(OrderSide.BUY, "AAPL", 1, Decimal(190))
    sleep(30)

    withdrawal_tx_hash = primedelta.withdraw_stock_token("AAPL", 1)
    wait_for_transaction(withdrawal_tx_hash, provider_url)
    sleep(2)
    deposit_tx_hash = primedelta.deposit_stock_token("AAPL", 1)
    wait_for_transaction(deposit_tx_hash, provider_url)
    sleep(2)

    closed_transfers = {
        transfer.transaction_id: transfer for transfer in primedelta.closed_transfers()
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
