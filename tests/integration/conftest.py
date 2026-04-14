import os

import pytest
from dotenv import load_dotenv
from web3 import Web3

from primedelta import PrimeDelta

# Load environment variables from .env file
load_dotenv()


def pytest_configure(config):
    """Register integration test marker."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require .env setup)"
    )


@pytest.fixture(scope="session")
def provider_url():
    url = os.getenv("PRIMEDELTA_PROVIDER_URL")
    if not url:
        pytest.skip("PRIMEDELTA_PROVIDER_URL not set in .env")
    return url


@pytest.fixture(scope="session")
def test_private_key():
    key = os.getenv("PRIMEDELTA_TEST_PRIVATE_KEY")
    if not key:
        pytest.skip("PRIMEDELTA_TEST_PRIVATE_KEY not set in .env")
    return key


@pytest.fixture
def primedelta(test_private_key, provider_url) -> PrimeDelta:
    """Create a PrimeDelta instance with test credentials."""
    return PrimeDelta(private_key=test_private_key, web3_provider_url=provider_url)


@pytest.fixture
def primedelta_logged_in(primedelta) -> PrimeDelta:
    """Create a logged-in PrimeDelta instance."""
    primedelta.login()
    yield primedelta
    primedelta.logout()


def wait_for_transaction(tx_hash: str, provider_url: str) -> None:
    """Wait for a transaction to be mined."""
    Web3(Web3.HTTPProvider(provider_url)).eth.wait_for_transaction_receipt(tx_hash)
