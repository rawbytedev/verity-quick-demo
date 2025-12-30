import secrets
from socket import MsgFlag
from eth_account import Account
from eth_account.messages import encode_defunct


def CreateNew():
    priv_key = "0x" + secrets.token_hex(32)
    acct = Account.from_key(priv_key)
    
    return acct

def Address(acc):
    return acc.address

def Keys(acc):
    return acc.key

def sign(priv_key, msg):
    signed = sign_raw(priv_key, msg).signature.hex()
    return signed

def sign_raw(priv_key, msg):
    encoded_msg = encode_defunct(text=msg)
    # Sign the message using the private key
    signed_msg = Account.sign_message(encoded_msg, private_key=priv_key)
    return signed_msg

def verify(address, sign, msg):
    recovered_address = Account.recover_message(
    encode_defunct(text=msg), 
    signature=sign
    )
    if recovered_address == address:
        return True ## Signature is valid
    return False ## Signature Invalid
    

