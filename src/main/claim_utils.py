import os
import mimetypes
from datetime import datetime
from typing import Optional

from utils import hexhash
from claim_model import VerityClaim, ContentType
from signer import sign
from middleware import store


def _compute_content_hash_from_bytes(data: bytes) -> str:
    # return a prefixed sha256 hex string
    h = hexhash(data)
    return f"sha256:{h}"


def create_claim_from_file(file_path: str, issuer_did: str, content_type: Optional[ContentType] = None) -> VerityClaim:
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


def create_claim_from_message(message: str, issuer_did: str) -> VerityClaim:
    """Create a VerityClaim from a short text message. The message itself is stored in credential_subject.text."""
    now = datetime.now()
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


def sign_claim(claim: VerityClaim, priv_key_hex: str, verification_method: str) -> VerityClaim:
    """Sign the claim using the provided private key hex string and attach proof."""
    # Serialize claim deterministically
    payload = claim.model_dump_json()
    signature = sign(priv_key_hex, payload)

    proof = {
        "type": "Ed25519Signature2020",
        "created": datetime.now().isoformat(),
        "verificationMethod": verification_method,
        "proofValue": signature,
        "signer": claim.issuer.get("id"),
    }
    claim.proof = proof
    return claim


def store_claim(claim: VerityClaim, did_verify: bool = False):
    """Store claim via middleware.store and return the IPFS CID string from the response."""
    resp = store(claim)
    return resp.cid
