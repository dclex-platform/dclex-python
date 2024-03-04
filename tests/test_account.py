from unittest.mock import ANY

import pytest

from dclex import AccountNotVerified, DigitalIdentityAlreadyClaimed
from dclex.types import Portfolio


def test_login_and_logout(dclex):
    assert not dclex.logged_in()

    dclex.login()
    assert dclex.logged_in()

    dclex.logout()
    assert not dclex.logged_in()


def test_claim_digital_identity_raises_when_user_has_already_claimed_it(
    dclex, provider_url
):
    dclex.login()
    with pytest.raises(DigitalIdentityAlreadyClaimed):
        dclex.claim_digital_identity()


def test_claim_digital_identity_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.claim_digital_identity()


def test_should_get_portfolio(dclex):
    dclex.login()

    assert dclex.portfolio() == Portfolio(
        available=ANY,
        equity=ANY,
        funds=ANY,
        profit_loss=ANY,
        total_value=ANY,
        positions=ANY,
    )


def test_portfolio_raises_when_user_is_not_verified(dclex_unverified):
    dclex_unverified.login()
    with pytest.raises(AccountNotVerified):
        dclex_unverified.portfolio()
