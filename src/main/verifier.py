from datetime import datetime
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from middleware import retrieve, resolve
from claim_model import VerityClaim
from shared_model import DemoDIDDocument, VerificationMethod
from signer import verify

logger = logging.getLogger(__name__)
router = APIRouter()

class VerificationResult(BaseModel):
    """Standardized verification result for API responses."""
    verified: bool
    claim_id: str
    issuer: Dict[str, str]
    issuer_name: Optional[str] = None
    verification_tier: Optional[str] = None
    verification_time: str
    error_message: Optional[str] = None
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

async def verify_claim_chain(claim_cid: str) -> VerificationResult:
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
        # Step 1: Retrieve the claim from storage
        claim_resp = retrieve(claim_cid)
        if not claim_resp.exists:
            result.error_message = f"Claim not found: {claim_cid}"
            return result
            
        claim_dict = claim_resp.document
        claim = VerityClaim.model_validate(claim_dict)
        result.claim_id = claim.claim_id
        result.steps["claim_retrieved"] = True
        
        # Step 2: Extract issuer DID
        issuer_did = claim.issuer["id"] if isinstance(claim.issuer, dict) else claim.issuer
        if not issuer_did:
            result.error_message = "No issuer DID in claim"
            return result
            
        result.issuer = {"did": issuer_did}
        
        # Step 3: Resolve DID to CID
        did_resp = resolve(issuer_did)
        if did_resp.status != "success" or not did_resp.doc_cid:
            result.error_message = f"DID resolution failed: {issuer_did}"
            return result
            
        result.steps["did_resolved"] = True
        
        # Step 4: Retrieve DID Document
        diddoc_resp = retrieve(did_resp.doc_cid)
        if not diddoc_resp.exists:
            result.error_message = f"DID Document not found: {did_resp.doc_cid}"
            return result
            
        diddoc_dict = diddoc_resp.document
        diddoc = DemoDIDDocument.model_validate(diddoc_dict)
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
        claim.proof =None
        claim.verification_url = None
        message_to_verify = claim.model_dump_json()
        
        # Step 6: Check all verification methods in DID Document
        signature_valid = False
        authorized_method = None
        
        for vm in diddoc.verification_method:
            address = _extract_address_from_vm(vm)
            if address and verify(address, signature, message_to_verify):
                signature_valid = True
                authorized_method = vm.id
                break
        
        if not signature_valid:
            result.error_message = "Signature does not match any authorized key in DID Document"
            return result
            
        result.steps["signature_valid"] = True
        result.steps["issuer_authorized"] = True
        result.verified = True
        result.issuer["authorized_method"] = authorized_method
        
    except Exception as e:
        logger.exception(f"Verification failed for {claim_cid}")
        result.error_message = f"Verification error: {str(e)}"
    
    return result


@router.get("/verify/claim/{claim_id}", response_model=VerificationResult)
async def verify_by_claim_id(claim_id: str):
    """Verify a claim using its claim_id (requires lookup)."""
    # In real system, claim_id->CID index
    if claim_id.startswith("claim_"):
        res = resolve(claim_id)
        try:
                    result = await verify_claim_chain(res.doc_cid)
                    if result.steps["claim_retrieved"]:
                        return result
        except:
            raise HTTPException(status_code=500, detail=f"Internal error: {claim_id}")
    elif claim_id.startswith("cid_"):
        return await verify_claim_chain(claim_id)
    raise HTTPException(status_code=404, detail=f"Claim not found: {claim_id}")

# HTML Interface
@router.get("/", response_class=HTMLResponse)
async def verification_interface():
    """Simple web interface for claim verification."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verity Protocol - Claim Verifier</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
            .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
            .input-group { margin-bottom: 20px; }
            input[type="text"] { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; border: none; padding: 12px 30px; font-size: 16px; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .result { margin-top: 30px; padding: 20px; border-radius: 5px; display: none; }
            .verified { background: #d4edda; border: 2px solid #c3e6cb; color: #155724; }
            .not-verified { background: #f8d7da; border: 2px solid #f5c6cb; color: #721c24; }
            .badge { font-size: 24px; font-weight: bold; margin: 10px 0; }
            .step { margin: 5px 0; padding: 5px; border-left: 3px solid #6c757d; padding-left: 10px; }
            .step.success { border-color: #28a745; }
            .step.failure { border-color: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Verity Protocol - Claim Verification</h1>
            <p>Verify the authenticity of election results, official statements, and other certified content.</p>
            
            <div class="input-group">
                <label for="claimUrl"><b>Verification URL or Claim ID:</b></label>
                <input type="text" id="claimUrl" placeholder="https://... or cid_abc123... or claim_abc123">
                <button onclick="verifyClaim()">Verify Authenticity</button>
            </div>
            
            <div id="loading" style="display: none;">
                <p>⏳ Verifying claim... (checking cryptographic signatures)</p>
            </div>
            
            <div id="result" class="result"></div>
        </div>
        
        <script>
            async function verifyClaim() {
                const input = document.getElementById('claimUrl').value.trim();
                const loading = document.getElementById('loading');
                const resultDiv = document.getElementById('result');
                
                if (!input) {
                    alert('Please enter a verification URL or Claim ID');
                    return;
                }
                
                // Extract claim ID from URL if needed
                let claimId = input;
                if (input.includes('/verify/')) {
                    claimId = input.split('/verify/').pop();
                } else if (input.includes('cid=')) {
                    claimId = new URL(input).searchParams.get('cid');
                }
                
                loading.style.display = 'block';
                resultDiv.style.display = 'none';
                
                try {
                    let response;
                    response = await fetch(`/verify/claim/${encodeURIComponent(claimId)}`);
                    const data = await response.json();
                    
                    // Display results
                    resultDiv.innerHTML = '';
                    resultDiv.className = 'result ' + (data.verified ? 'verified' : 'not-verified');
                    
                    const badge = data.verified 
                        ? '<div class="badge">✅ VERIFIED & VALID</div>'
                        : '<div class="badge">❌ NOT VERIFIED</div>';
                    
                    const issuer = data.issuer_name || data.issuer?.did || 'Unknown';
                    const tier = data.verification_tier ? `Tier ${data.verification_tier}` : 'Unknown Tier';
                    
                    let stepsHtml = '<h3>Verification Steps:</h3>';
                    for (const [step, success] of Object.entries(data.steps || {})) {
                        const stepName = step.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                        stepsHtml += `<div class="step ${success ? 'success' : 'failure'}">${success ? '✓' : '✗'} ${stepName}</div>`;
                    }
                    
                    resultDiv.innerHTML = `
                        ${badge}
                        <h2>${issuer}</h2>
                        <p><strong>Status:</strong> ${data.verified ? 'Cryptographically verified' : 'Verification failed'}</p>
                        <p><strong>Claim ID:</strong> ${data.claim_id}</p>
                        <p><strong>Verification Tier:</strong> ${tier}</p>
                        <p><strong>Time:</strong> ${new Date(data.verification_time).toLocaleString()}</p>
                        ${data.error_message ? `<p><strong>Error:</strong> ${data.error_message}</p>` : ''}
                        ${stepsHtml}
                        ${data.verified ? '<p style="margin-top: 20px; font-size: 18px; color: #155724;">This content is authentic and has not been tampered with.</p>' : ''}
                    `;
                    
                } catch (error) {
                    resultDiv.className = 'result not-verified';
                    resultDiv.innerHTML = `
                        <div class="badge">❌ VERIFICATION ERROR</div>
                        <p>Unable to verify claim: ${error.message}</p>
                    `;
                } finally {
                    loading.style.display = 'none';
                    resultDiv.style.display = 'block';
                }
            }
            
            // Allow Enter key to trigger verification
            document.getElementById('claimUrl').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') verifyClaim();
            });
        </script>
    </body>
    </html>
    """

# Register with main app
def setup_verification_app(app: FastAPI):
    """Register verification routes with FastAPI app."""
    app.include_router(router)