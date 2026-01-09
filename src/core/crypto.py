"""
Cryptographic utilities for Ethereum signing and hashing.
"""
import secrets
from typing import Union
import uuid
import hashlib
from eth_account import Account
from eth_account.messages import encode_defunct
from .exceptions import VerityCryptoError

def create_ethereum_account():
    """
    Create a new Ethereum account with random private key.

    Returns:
        eth_account.Account: New Ethereum account object.

    Raises:
        VerityCryptoError: If account creation fails.
    """
    try:
        priv_key = "0x" + secrets.token_hex(32)
        account = Account()
        return account.from_key(private_key=priv_key)
    except Exception as e:
        raise VerityCryptoError(f"Failed to create Ethereum account: {e}") from e


def get_ethereum_address(account: Account) -> str:
    """
    Extract address from Ethereum account.

    Args:
        account: eth_account.Account object.

    Returns:
        Ethereum address as string.
    """
    return account.address


def get_ethereum_private_key(account: Account) -> str:
    """
    Extract private key from Ethereum account.

    Args:
        account: eth_account.Account object.

    Returns:
        Private key as hex string.
    """
    return account.key


# Backward compatibility aliases
def eth_addr(acc):
    """Deprecated: use get_ethereum_address() instead."""
    return get_ethereum_address(acc)


def eth_key(acc):
    """Deprecated: use get_ethereum_private_key() instead."""
    return get_ethereum_private_key(acc)


def create_new_eth():
    """Deprecated: use create_ethereum_account() instead."""
    return create_ethereum_account()



def sign_message(priv_key: str, msg: str) -> str:
    """
    Sign a message with Ethereum private key.

    Args:
        priv_key: Private key as hex string.
        msg: Message to sign.

    Returns:
        Signature as hex string.

    Raises:
        VerityCryptoError: If signing fails.
    """
    try:
        signed_msg = sign_message_raw(priv_key, msg)
        return signed_msg.signature.hex()
    except Exception as e:
        raise VerityCryptoError(f"Failed to sign message: {e}") from e


def sign(priv_key, msg):
    """Deprecated: use sign_message() instead."""
    return sign_message(priv_key, msg)


def sign_message_raw(priv_key: str, msg: str):
    """
    Sign a message and return raw SignedMessage object.

    Args:
        priv_key: Private key as hex string.
        msg: Message to sign.

    Returns:
        eth_account.messages.SignedMessage: Raw signed message object.

    Raises:
        VerityCryptoError: If signing fails.
    """
    try:
        encoded_msg = encode_defunct(text=msg)
        account = Account()
        return account.sign_message(signable_message=encoded_msg, private_key=priv_key)
    except Exception as e:
        raise VerityCryptoError(f"Failed to sign message: {e}") from e


def sign_raw(priv_key, msg):
    """Deprecated: use sign_message_raw() instead."""
    return sign_message_raw(priv_key, msg)

# # pylint: disable=broad-exception-caught
def verify_signature(address: str, signature_hex: str, msg: str) -> bool:
    """
    Verify a message signature against an Ethereum address.

    Args:
        address: Ethereum address to verify against.
        signature_hex: Signature as hex string.
        msg: Original message.

    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        enc_msg = encode_defunct(text=msg)
        account = Account()
        recovered_address = account.recover_message(
            signable_message=enc_msg, signature=signature_hex
        )
        return recovered_address.lower() == address.lower()
    except Exception:
        return False


def verify(address, signa, msg):
    """Deprecated: use verify_signature() instead."""
    return verify_signature(address, signa, msg)



def newuuid() -> uuid.UUID:
    """
    Generate a new UUID.

    Returns:
        uuid.UUID: Random UUID.
    """
    return uuid.uuid4()


def hash_sha256_bytes(data: Union[bytes, str]) -> bytes:
    """
    Hash data with SHA256 and return bytes.

    Args:
        data: Data to hash (string or bytes).

    Returns:
        SHA256 hash as bytes.
    """
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).digest()


def dighash(data: Union[bytes, str]) -> bytes:
    """Deprecated: use hash_sha256_bytes() instead."""
    return hash_sha256_bytes(data)


def hash_sha256_hex(data: Union[bytes, str]) -> str:
    """
    Hash data with SHA256 and return hex string.

    Args:
        data: Data to hash (string or bytes).

    Returns:
        SHA256 hash as hex string.
    """
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def hexhash(data: Union[bytes, str]) -> str:
    """Deprecated: use hash_sha256_hex() instead."""
    return hash_sha256_hex(data)

def encode_id(escrow_id: int) -> str:
    """Convert internal int ID to string for JSON/API."""
    return str(escrow_id)

def decode_id(raw: str | int) -> int:
    """Convert external string/int back to internal int."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        return int(raw)
    raise ValueError(f"Unsupported escrow_id type: {type(raw)}")
