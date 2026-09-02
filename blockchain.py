"""Blockchain interaction for Sepolia testnet using web3.py."""

import json
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()

CONTRACT_ABI_PATH = Path(__file__).parent / "contracts" / "FaceVerify.json"
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "")


def get_web3() -> Web3:
    """Create and return a Web3 instance connected to Sepolia."""
    w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC_URL))
    # Sepolia uses PoA consensus — inject middleware for extraData handling
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract(w3: Web3):
    """Load the deployed FaceVerify contract."""
    if not CONTRACT_ADDRESS:
        raise ValueError("CONTRACT_ADDRESS not set in .env — deploy the contract first")
    if not CONTRACT_ABI_PATH.exists():
        raise FileNotFoundError(
            f"Contract ABI not found at {CONTRACT_ABI_PATH}. "
            "Compile FaceVerify.sol first (see README)."
        )
    with open(CONTRACT_ABI_PATH) as f:
        contract_data = json.load(f)
    abi = contract_data if isinstance(contract_data, list) else contract_data.get("abi", contract_data)
    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi,
    )


def get_account(w3: Web3):
    """Derive account from private key."""
    if not PRIVATE_KEY:
        raise ValueError("PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(PRIVATE_KEY)


def store_post_hash(
    post_hash: str,
    post_url: str,
    title: str,
    source: str,
) -> str:
    """
    Store a post fingerprint on the Sepolia testnet.

    Args:
        post_hash: SHA-256 hex digest of the post.
        post_url: URL of the discovered post.
        title: Post title or caption.
        source: Platform name.

    Returns:
        Transaction hash string.
    """
    w3 = get_web3()
    contract = get_contract(w3)
    account = get_account(w3)

    # Convert hex hash to bytes32
    hash_bytes = bytes.fromhex(post_hash)

    # Build transaction
    tx = contract.functions.verifyPost(
        hash_bytes,
        post_url,
        title,
        source,
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
        "chainId": 11155111,  # Sepolia chain ID
    })

    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    print(f"[Blockchain] TX confirmed: {receipt.transactionHash.hex()}")
    print(f"[Blockchain] Gas used: {receipt.gasUsed}")
    return receipt.transactionHash.hex()


def verify_post_hash(post_hash: str) -> dict:
    """
    Verify whether a post hash exists on-chain.

    Args:
        post_hash: SHA-256 hex digest to check.

    Returns:
        Dict with verification result. Keys: verified, postUrl, title, source, timestamp, uploader.
    """
    w3 = get_web3()
    contract = get_contract(w3)

    hash_bytes = bytes.fromhex(post_hash)

    # Check existence
    exists = contract.functions.isVerified(hash_bytes).call()

    if not exists:
        return {"verified": False, "message": "Hash not found on-chain"}

    # Fetch full record
    record = contract.functions.getVerification(hash_bytes).call()
    return {
        "verified": True,
        "postHash": record[0].hex(),
        "postUrl": record[1],
        "title": record[2],
        "source": record[3],
        "timestamp": record[4],
        "uploader": record[5],
    }


def get_stored_count() -> int:
    """Return the total number of hashes stored on-chain."""
    w3 = get_web3()
    contract = get_contract(w3)
    return contract.functions.getStoredCount().call()


def deploy_contract() -> str:
    """
    Deploy the FaceVerify contract to Sepolia.
    Returns the contract address.
    """
    w3 = get_web3()
    account = get_account(w3)

    if not CONTRACT_ABI_PATH.exists():
        raise FileNotFoundError(
            f"Contract ABI not found at {CONTRACT_ABI_PATH}. "
            "Compile FaceVerify.sol first (see README)."
        )

    with open(CONTRACT_ABI_PATH) as f:
        contract_data = json.load(f)

    abi = contract_data["abi"]
    bytecode = contract_data["bytecode"]

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price,
        "chainId": 11155111,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    contract_address = receipt.contractAddress
    print(f"[Blockchain] Contract deployed at: {contract_address}")
    print(f"[Blockchain] TX: {receipt.transactionHash.hex()}")
    return contract_address
