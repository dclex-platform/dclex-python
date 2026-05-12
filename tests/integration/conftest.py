import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from web3 import Web3

# Prefer .env.local when present (local stack), fall back to .env (default/dev).
_repo_root = Path(__file__).resolve().parents[2]
_env_local = _repo_root / ".env.local"
_env = _repo_root / ".env"
if _env_local.exists():
    load_dotenv(_env_local, override=True)
elif _env.exists():
    load_dotenv(_env, override=True)

from primedelta import PrimeDelta  # noqa: E402
from primedelta.types import AccountStatus  # noqa: E402


def pytest_configure(config):
    """Register integration test markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require .env setup)",
    )
    config.addinivalue_line(
        "markers",
        "dex: dex flow integration tests (swap, liquidity)",
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
    if not key or key == "0x...":
        pytest.skip("PRIMEDELTA_TEST_PRIVATE_KEY not set in .env")
    return key


@pytest.fixture(scope="session")
def unverified_private_key():
    key = os.getenv("PRIMEDELTA_UNVERIFIED_PRIVATE_KEY")
    if not key:
        pytest.skip("PRIMEDELTA_UNVERIFIED_PRIVATE_KEY not set in .env")
    return key


@pytest.fixture(scope="session")
def test_symbol():
    return os.getenv("PRIMEDELTA_TEST_SYMBOL", "AAPL")


@pytest.fixture
def primedelta(test_private_key, provider_url) -> PrimeDelta:
    return PrimeDelta(private_key=test_private_key, web3_provider_url=provider_url)


@pytest.fixture
def primedelta_logged_in(primedelta) -> PrimeDelta:
    primedelta.login()
    yield primedelta
    primedelta.logout()


@pytest.fixture
def unverified_primedelta(unverified_private_key, provider_url) -> PrimeDelta:
    return PrimeDelta(
        private_key=unverified_private_key, web3_provider_url=provider_url
    )


@pytest.fixture
def unverified_primedelta_logged_in(unverified_primedelta) -> PrimeDelta:
    unverified_primedelta.login()
    yield unverified_primedelta
    unverified_primedelta.logout()


def wait_for_transaction(tx_hash: str, provider_url: str) -> None:
    """Wait for a transaction to be mined."""
    Web3(Web3.HTTPProvider(provider_url)).eth.wait_for_transaction_receipt(tx_hash)


# Anvil default deployer key — has 10000 ETH on a fresh local chain.
# Use to fund the test account with gas + USDC (USDCMock.mint is unrestricted).
_ANVIL_DEPLOYER_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _fund_test_account_eth_and_usdc(test_address: str, provider_url: str) -> None:
    """Top up the test account with ETH for gas + USDC for swaps/liquidity."""
    w3 = Web3(Web3.HTTPProvider(provider_url))
    deployer = w3.eth.account.from_key(_ANVIL_DEPLOYER_KEY)

    # Fund ETH if balance < 1 ether.
    eth_balance = w3.eth.get_balance(test_address)
    if eth_balance < w3.to_wei(1, "ether"):
        tx = {
            "to": test_address,
            "value": w3.to_wei(10, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(deployer.address),
            "chainId": w3.eth.chain_id,
        }
        signed = deployer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

    # Mint USDC (6 decimals). Top up to ≥10 USDC.
    contracts = PrimeDelta(
        private_key=test_private_key_or_skip(),
        web3_provider_url=provider_url,
    )._get_contracts()
    usdc = w3.eth.contract(
        address=w3.to_checksum_address(contracts.core.usdc.address),
        abi=contracts.core.usdc.abi,
    )
    usdc_balance = usdc.functions.balanceOf(test_address).call()
    if usdc_balance < 10 * 10**6:
        # USDCMock.mint(address,uint256) is public/unrestricted.
        mint_tx = usdc.functions.mint(test_address, 1_000_000 * 10**6).build_transaction(
            {
                "from": deployer.address,
                "nonce": w3.eth.get_transaction_count(deployer.address),
                "chainId": w3.eth.chain_id,
                "gas": 200_000,
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed = deployer.sign_transaction(mint_tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)


def test_private_key_or_skip() -> str:
    key = os.getenv("PRIMEDELTA_TEST_PRIVATE_KEY")
    if not key or key == "0x...":
        pytest.skip("PRIMEDELTA_TEST_PRIVATE_KEY not set")
    return key


def _wait_for_did_minted(sdk: PrimeDelta, timeout_s: float = 30.0) -> None:
    """Backend syncs on-chain DID via the tasks indexer — poll until it lands."""
    import time

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if sdk.get_account_status() == AccountStatus.DID_MINTED:
            return
        time.sleep(1.0)


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_test_account(test_private_key, provider_url):
    """Ensure the test account is funded + VERIFIED + DID_MINTED on a fresh stack.

    Funds ETH (from Anvil deployer) and USDC (USDCMock.mint is unrestricted),
    then runs the verification flow against `FakeVerificationClient` and mints
    the on-chain DID NFT. Idempotent — handles the case where the DID NFT is
    already on-chain but the backend indexer hasn't caught up yet (409 from
    `/digital-identity-signature/`).
    """
    if not test_private_key or test_private_key == "0x...":
        return  # Real fixtures will pytest.skip; nothing to bootstrap.

    test_address = Web3().eth.account.from_key(test_private_key).address
    _fund_test_account_eth_and_usdc(test_address, provider_url)

    sdk = PrimeDelta(private_key=test_private_key, web3_provider_url=provider_url)
    sdk.login()
    try:
        status = sdk.get_account_status()
        if status == AccountStatus.DID_MINTED:
            return
        if status == AccountStatus.NOT_VERIFIED:
            base_url = os.getenv("PRIMEDELTA_BASE_URL")
            token = sdk._primedelta_client._token
            response = requests.post(
                f"{base_url}/verification-token/",
                headers={"Authorization": f"Token {token}"},
            )
            response.raise_for_status()
            status = sdk.get_account_status()
        if status == AccountStatus.VERIFIED:
            try:
                tx_hash = sdk.claim_digital_identity()
                wait_for_transaction(tx_hash, provider_url)
            except requests.exceptions.HTTPError as exc:
                # 409 = ALREADY_HAS_DID. DID is already on-chain (e.g. from a
                # prior test run on the same chain state); just wait for the
                # backend indexer to flip the status.
                if exc.response is None or exc.response.status_code != 409:
                    raise
            _wait_for_did_minted(sdk)
    finally:
        sdk.logout()
