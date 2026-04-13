from unittest.mock import ANY

import pytest

from primedelta import AccountNotVerified, DigitalIdentityAlreadyClaimed
from primedelta.types import Portfolio


def test_login_and_logout(primedelta):
    assert not primedelta.logged_in()

    primedelta.login()
    assert primedelta.logged_in()

    primedelta.logout()
    assert not primedelta.logged_in()


def test_claim_digital_identity_raises_when_user_has_already_claimed_it(
    primedelta, provider_url
):
    primedelta.login()
    with pytest.raises(DigitalIdentityAlreadyClaimed):
        primedelta.claim_digital_identity()


def test_claim_digital_identity_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.claim_digital_identity()


def test_should_get_portfolio(primedelta):
    primedelta.login()

    assert primedelta.portfolio() == Portfolio(
        buying_power=ANY,
        total_equity=ANY,
        total_funds=ANY,
        profit_loss=ANY,
        total_value=ANY,
        positions=ANY,
    )


def test_portfolio_raises_when_user_is_not_verified(primedelta_unverified):
    primedelta_unverified.login()
    with pytest.raises(AccountNotVerified):
        primedelta_unverified.portfolio()
