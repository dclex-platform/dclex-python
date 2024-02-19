import json
import os

CHAIN_ID: int = 11155111
SIWE_MESSAGE: str = (
    "By signing this message you confirm that you have completely"
    " read and understand DCLEX's terms of service including all policies"
    " and disclosures and that you agree with each part of them."
)
SIWE_DOMAIN: str = "app.stg.dclex.com"
SIWE_URI: str = "http://app.stg.dclex.com"
USDC_ASSET_TYPE: str = "USDC"

DCLEX_BASE_URL = "https://api.stg.dclex.com"
USDC_CONTRACT_ADDRESS = "0xd3AA652C5b750F8195B46E185Bad5C9965bB37ea"
VAULT_CONTRACT_ADDRESS = "0x9171338754ac82cdE212Dadc924bfB8F2432E008"
DIGITAL_IDENTITY_CONTRACT_ADDRESS = "0xc9B2a2e25116865286b13859053eBa163C62dace"
FACTORY_CONTRACT_ADDRESS = "0x520677edeCbd1A716846F5167bbA4ad5fCD781B7"
BLOCKCHAIN_FALSE_VALUE = 2


def _load_abi(name: str):
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "resources", f"{name}.json"
    )
    with open(path) as f:
        return json.load(f)


USDC_CONTRACT_ABI = _load_abi("usdc_contract_abi")
DIGITAL_IDENTITY_CONTRACT_ABI = _load_abi("digital_identity_contract_abi")
FACTORY_CONTRACT_ABI = _load_abi("factory_contract_abi")
VAULT_CONTRACT_ABI = _load_abi("vault_contract_abi")
