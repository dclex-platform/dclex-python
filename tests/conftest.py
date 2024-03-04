import pytest
from eth_typing.encoding import HexStr
from web3 import Web3

from dclex.dclex import Dclex


def pytest_addoption(parser):
    parser.addoption("--test-account-private-key", action="store")
    parser.addoption("--provider-url", action="store")


@pytest.fixture(scope="session")
def provider_url(pytestconfig):
    return pytestconfig.getoption("provider_url")


@pytest.fixture(scope="session")
def test_account_private_key(pytestconfig):
    return pytestconfig.getoption("test_account_private_key")


@pytest.fixture
def unverified_user_private_key():
    account = Web3().eth.account.create()
    return Web3.to_hex(account.key)


@pytest.fixture(name="dclex")
def dclex_fixture(test_account_private_key, provider_url) -> Dclex:
    return Dclex(private_key=test_account_private_key, web3_provider_url=provider_url)


@pytest.fixture
def dclex_unverified(unverified_user_private_key, provider_url):
    return Dclex(
        private_key=unverified_user_private_key, web3_provider_url=provider_url
    )


def wait_for_transaction(tx_hash: HexStr, provider_url: str) -> None:
    Web3(Web3.HTTPProvider(provider_url)).eth.wait_for_transaction_receipt(tx_hash)
