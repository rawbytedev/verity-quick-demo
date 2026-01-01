"""
Small utility to sign
"""
import secrets
from eth_account import Account
from eth_account.messages import encode_defunct


def create_new_eth():
    """
    Creates a new ethereum account and returns it
    """
    priv_key = "0x" + secrets.token_hex(32)
    tmp = Account()
    acct = tmp.from_key(private_key=priv_key)
    return acct

def eth_addr(acc):
    """Return the address of an eth account"""
    return acc.address

def eth_key(acc):
    """Return the key of an eth account"""
    return acc.key

def sign(priv_key, msg):
    """Signs a message with an eth key
    return hex string"""
    signed = sign_raw(priv_key, msg).signature.hex()
    return signed

def sign_raw(priv_key, msg):
    """Signs a message with an eth key
    return bytes representation"""
    encoded_msg = encode_defunct(text=msg)
    # Sign the message using the private key
    tmp = Account()
    signed_msg = tmp.sign_message(signable_message=encoded_msg, private_key=priv_key)
    return signed_msg

def verify(address, signa, msg):
    """
    check the signature of a sign message against an address and 
    return whether the msg was signed by that address or not
    """
    enc_msg = encode_defunct(text=msg)
    tmp = Account()
    recovered_address = tmp.recover_message(
    signable_message=enc_msg,
    signature=signa
    )
    if recovered_address == address:
        return True ## Signature is valid
    return False ## Signature Invalid
