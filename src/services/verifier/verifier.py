"""
Docstring for verifier
"""
import tempfile
import os
from datetime import datetime
import logging
from typing import Dict, Optional, TypedDict, List
from fastapi import FastAPI, HTTPException, APIRouter,Form, File, UploadFile
from pydantic import BaseModel
from src.middleware import retrieve, resolve
from src.core.models import (VerityClaim, DemoDIDDocument,
VerificationMethod, IPFSRetrieveResponse,DIDRegistryResolveResponse)
from src.core.crypto import verify, hexhash
from src.core.exceptions import (VerityVerifierError, VerityValidationError)


logger = logging.getLogger(__name__)
router = APIRouter()

class ResponseDict(TypedDict, total=False):
    """Store all API responses"""
    claim_resp:IPFSRetrieveResponse
    did_resp:DIDRegistryResolveResponse
    diddoc_resp:IPFSRetrieveResponse

class TempDict(TypedDict, total=False):
    """Store parsed models"""
    claim_dict: dict
    diddoc_dict: dict


class VerificationResult(BaseModel):
    """Standardized verification result for API responses."""
    verified: bool
    claim_id: str
    issuer: Dict[str, str]
    issuer_name: Optional[str] = None
    verification_tier: Optional[str] = None
    verification_time: str
    error_message: Optional[str] = None
    checksum: Optional[str] = None
    steps: Dict[str, bool] = {
        "claim_retrieved": False,
        "did_resolved": False,
        "diddoc_retrieved": False,
        "signature_valid": False,
        "issuer_authorized": False
    }

def _extract_address_from_vm(vm: VerificationMethod) -> Optional[str]:
    """Extract Ethereum address from verification method's public_key_multibase."""
    pk = vm.public_key_multibase
    if pk.startswith("eth:"):
        return pk[4:]
    return pk

## valid in this case, we require details from previous requests
## in other requests and each request is fairly unique
# pylint: disable=too-many-return-statements,too-many-statements
async def verify_claim_chain(claim_cid: str,
                             checksum:Optional[str]=None,
                             use_checksum:bool=True) -> VerificationResult:
    """
    Core verification logic: Complete chain from claim CID to issuer validation.
    """
    result = VerificationResult(
        verified=False,
        claim_id=claim_cid,
        issuer={},
        verification_time=datetime.now().isoformat()
    )
    try:
        resq_dict:ResponseDict= {}
        tmp_dict: TempDict = {}
        # Step 1: Retrieve the claim from storage
        resq_dict['claim_resp'] = retrieve(claim_cid)
        if not resq_dict['claim_resp'].exists:
            result.error_message = f"Claim not found: {claim_cid}"
            return result

        tmp_dict['claim_dict'] = resq_dict['claim_resp'].document
        claim = VerityClaim.model_validate(tmp_dict['claim_dict'])
        result.claim_id = claim.claim_id
        result.steps["claim_retrieved"] = True

        # Step 2: Extract issuer DID
        issuer_did = claim.issuer["id"] if isinstance(claim.issuer, dict) else claim.issuer
        if not issuer_did:
            result.error_message = "No issuer DID in claim"
            return result

        result.issuer = {"did": issuer_did}

        # Step 3: Resolve DID to CID
        resq_dict['did_resp'] = resolve(issuer_did)
        if resq_dict['did_resp'].status != "success" or not resq_dict['did_resp'].doc_cid:
            result.error_message = f"DID resolution failed: {issuer_did}"
            return result

        result.steps["did_resolved"] = True

        # Step 4: Retrieve DID Document
        diddoc_resp = retrieve(resq_dict['did_resp'].doc_cid)
        if not diddoc_resp.exists:
            result.error_message = f"DID Document not found: {resq_dict['did_resp'].doc_cid}"
            return result

        tmp_dict['diddoc_dict'] = diddoc_resp.document
        diddoc = DemoDIDDocument.model_validate(tmp_dict['diddoc_dict'])
        result.steps["diddoc_retrieved"] = True

        # Extract issuer metadata
        result.issuer_name = diddoc.metadata.get("organizationName", "Unknown Organization")
        result.verification_tier = diddoc.metadata.get("tier", "Unknown")

        # Step 5: Validate signature
        if not claim.proof or "proofValue" not in claim.proof:
            result.error_message = "No signature proof in claim"
            return result

        signature = claim.proof["proofValue"]
        # Recreate the exact payload that was signed
        # Remove proof for verification since it wasn't part of signed payload
        claim.proof = None
        claim.verification_url = None
        message_to_verify = claim.model_dump_json()
        # Step 6: Check all verification methods in DID Document
        signature_valid, authorized_method = vm_verification(diddoc.verification_method,
        signature, message_to_verify)

        if not signature_valid:
            result.error_message = "Signature does not match any authorized key in DID Document"
            return result

        result.steps["signature_valid"] = True
        result.steps["issuer_authorized"] = True
        result.checksum = claim.content_hash
        if use_checksum:
            if result.checksum == checksum:
                result.verified = True
        else:
            result.verified = True ## without checksum
        if not authorized_method:
            raise VerityVerifierError("authorized method missing")
        result.issuer["authorized_method"] = authorized_method
    except VerityVerifierError as e:
        logger.exception("Verification failed for %s", claim_cid)
        result.error_message = f"Verification error: {str(e)}"
    except Exception as e:
        raise VerityVerifierError("Error in Verifier") from e
    return result

def vm_verification(verification_method:List[VerificationMethod], signature, message_to_verify:str):
    "Check whether a message was signed by available verification methods"
    signature_valid = False
    authorized_method = None
    for vm in verification_method:
        address = _extract_address_from_vm(vm)
        if address and verify(address, signature, message_to_verify):
            signature_valid = True
            authorized_method = vm.id
            break
    return signature_valid, authorized_method


@router.get("/verify/claim/{claim_id}", response_model=VerificationResult)
async def verify_by_claim(claim_id:str):
    """Simple api for fast verification"""
    is_claim = claim_id.startswith("claim_")
    is_cid = claim_id.startswith("cid_")
    try:
        if is_claim:
            res = resolve(claim_id)
            if not res.doc_cid:
                raise VerityVerifierError("doc cid unavailable")
            result = await verify_claim_chain(res.doc_cid)
            if result.steps["claim_retrieved"]:
                return result
        elif is_cid:
            return await verify_claim_chain(claim_id)
    except VerityVerifierError as e:
        raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}") from e
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error in verifier {claim_id}") from e

@router.post("/verify/post/claim", response_model=VerificationResult)
async def verify_by_claim_id(
    claim_id: str = Form(default=None),
    message: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None)
    ):
    """Verify a claim using its claim_id (requires lookup)."""
    # In real system, claim_id->CID index
    is_claim = claim_id.startswith("claim_")
    is_cid = claim_id.startswith("cid_")
    if message:
        checksum = await generate_checksum(message=message)
    elif file:
        checksum = await generate_checksum(file=file)
    else:
        raise VerityVerifierError("No content to verify")
    try:
        if is_claim:
            res = resolve(claim_id)
            if not res.doc_cid:
                raise VerityVerifierError("doc cid unavailable")
            result = await verify_claim_chain(res.doc_cid, checksum)
            if result.steps["claim_retrieved"]:
                return result
        elif is_cid:
            return await verify_claim_chain(claim_id,checksum)
    except VerityVerifierError as e:
        raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}") from e
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error in verifier {claim_id}") from e


# Register with main app
def setup_verification_app(app: FastAPI):
    """Register verification routes with FastAPI app."""
    app.include_router(router)

async def generate_checksum(
    message:Optional[str]=None,
    file:Optional[UploadFile]=None
):
    """
    Uses provided content and generate a checksum which 
    is then used to attest authenticity of content
    """
    try:
        if message:
            checksum = checksum_data(data=message.encode())
        elif file:
            if not file.filename:
                raise VerityValidationError("Filename missing")
            # Save uploaded file temporarily and create claim from it
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False,
                                             suffix=os.path.splitext(file.filename)[1]) as tmp:
                contents = await file.read()
                tmp.write(contents)
                tmp_path = tmp.name

            try:
                checksum = checksum_data(file_path=tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'message' or 'file' is required"
            )
        return checksum
    except Exception as e:
        raise HTTPException(
                status_code=500,
                detail="Internal error"
            ) from e

def checksum_data(data:Optional[bytes]=None, file_path:Optional[str]=None) -> str:
    """A wrapper that generate checksum  using provided data"""
    if file_path:
        with open(file_path, "rb") as f:
            data = f.read()
    if data:
        check_sum = hexhash(data)
        return f"sha256:{check_sum}"
    return "sha256"
