"""
Utilities to handle claims
"""
import os
import mimetypes
from datetime import datetime
from typing import Any, Dict, Optional
from src.core.models import VerityClaim, ContentType
from src.core.crypto import hexhash, sign
from .middleware import register, store

class ClaimError(Exception):
    """
    ClaimError
    
    :var workflow: Description
    :vartype workflow: Create
    """

def _compute_content_hash_from_bytes(data: bytes) -> str:
    """Wrapper around hexhash"""
    # return a prefixed sha256 hex string
    h = hexhash(data)
    return f"sha256:{h}"

def create_claim(issuer_did:str,message:str=None,file_path:str=None,
                 content_type:Optional[ContentType]=None) -> VerityClaim:
    """
    Create a claim based on provided data

    :param issuer_did: Issuer DID
    :type issuer_did: str
    :param message: message to use for claim
    :type message: str
    :param file_path: path to file to use for claim
    :type file_path: str
    :param content_type: content type of file
    :type content_type: Optional[ContentType]
    :return: simple claim without proof
    :rtype: VerityClaim
    """
    if message is not None:
        return _create_claim_from_message(message, issuer_did)
    if file_path is not None:
        return _create_claim_from_file(file_path, issuer_did, content_type)
    raise ClaimError("Claim data can't be empty")

def _create_claim_from_file(file_path: str, issuer_did: str,
                            content_type: Optional[ContentType] = None) -> VerityClaim:
    """Create a VerityClaim from a local file. Does NOT embed the file contents.

    The claim will include metadata about the file and a content hash only.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    with open(file_path, "rb") as f:
        data = f.read()

    content_hash = _compute_content_hash_from_bytes(data)
    guess_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        if guess_type and guess_type.startswith("image"):
            ct = ContentType.IMAGE
        elif guess_type and guess_type.startswith("video"):
            ct = ContentType.VIDEO
        else:
            ct = ContentType.DOCUMENT
    else:
        ct = content_type

    now = datetime.now().isoformat()

    claim = VerityClaim(
        claim_id="tmp",
        context=["https://verity.foundation/contexts/claim/v1"],
        type=["VerifiableCredential", "VerityClaim"],
        issuance_date=now,
        issuer={"id": issuer_did},
        credential_subject={
            "id": f"urn:filepath:{os.path.basename(file_path)}",
            "type": os.path.splitext(os.path.basename(file_path))[1].lstrip("."),
            "filename": os.path.basename(file_path),
            "mime_type": guess_type or "application/octet-stream",
            "size_bytes": len(data),
        },
        content_hash=content_hash,
        content_type=ct,
    )

    # generate deterministic claim id
    claim.claim_id = claim.generate_claim_id()
    return claim


def _create_claim_from_message(message: str, issuer_did: str) -> VerityClaim:
    """Create a VerityClaim from 
    a short text message. 
    The message itself is stored in credential_subject.text."""
    now = datetime.now().isoformat()
    content_hash = _compute_content_hash_from_bytes(message.encode())
    claim = VerityClaim(
        claim_id="tmp",
        context=["https://verity.foundation/contexts/claim/v1"],
        type=["VerifiableCredential", "VerityClaim"],
        issuance_date=now,
        issuer={"id": issuer_did},
        credential_subject={
            "id": f"urn:message:{content_hash}",
            "type": "Message",
            "text": message,
        },
        content_hash=content_hash,
        content_type=ContentType.DOCUMENT,
    )
    claim.claim_id = claim.generate_claim_id()
    return claim


def sign_claim(claim: VerityClaim, priv_key_hex: str) -> VerityClaim:
    """Sign the claim using the provided private key hex string and attach proof."""
    # Serialize claim deterministically
    payload = claim.model_dump_json()
    signature = sign(priv_key_hex, payload)

    proof = {
        "type": "Ed25519Signature2020",
        "created": datetime.now().isoformat(),
        "proofValue": signature,
        "signer": claim.issuer.get("id"),
    }
    claim.proof = proof
    return claim


def store_claim(claim: VerityClaim):
    """Store claim via middleware.store and return the IPFS CID string from the response."""
    resp = store(claim)
    return resp.cid

def pin_claim(claim_id, cid):
    """map a claim id to cid """
    resp = register(claim_id, cid)
    return resp.status == "success"

def generate_verification_url(claim: VerityClaim, base_url: str = "http://localhost:8000") -> str:
    """Generate user-friendly verification URL for a claim."""
    # Use claim_id for URL (more readable than CID)
    claim_id = claim.claim_id
    return f"{base_url}/verify/claim/{claim_id}"

def create_and_register_claim(file_path: str, issuer_did: str,
                              issuer_private_key: str, verification_method: str = None,
                              base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Complete workflow: Create claim, sign it, store it, register DID, return verification URL.
    """
    # 1. Create claim from file
    claim = create_claim(file_path=file_path, issuer_did=issuer_did)
    # 2. Sign the claim
    if not verification_method:
        verification_method = f"{issuer_did}#key-1"
    signed_claim = sign_claim(claim=claim, priv_key_hex=issuer_private_key)

    # 3. Store claim (IPFS mock) and map claim to cid
    cid = store_claim(signed_claim)
    pin_claim(signed_claim.claim_id, cid)
    # 4. Generate verification URL
    verification_url = generate_verification_url(signed_claim, base_url)
    signed_claim.verification_url = verification_url

    return {
        "claim_id": signed_claim.claim_id,
        "cid": cid,
        "verification_url": verification_url,
        "issuer": issuer_did,
        "signed_at": signed_claim.proof.get("created") if signed_claim.proof else None
    }
