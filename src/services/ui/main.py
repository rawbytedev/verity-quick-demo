"""
UI Service - Web interface for Verity Protocol demo
Wires up the VerityDemo backend and middleware operations
"""
import tempfile
import os
import json
from typing import Optional
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from src.backend import VerityDemo
from src.core.models import (
    DemoDIDDocument,
    VerificationMethod,
)
from src.core.exceptions import VerityBackendError, VerityCliError, VerityError

app = FastAPI(
    title="DID Management System",
    description="Verity Protocol - DID Document and Claim Management"
)

# Mount static files and templates (if available)

app.mount("/ui/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")


# Initialize backend (single instance for all requests)
backend = VerityDemo()

# ============================================================================
# HTML Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render main HTML interface."""
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verity Protocol - DID Management</title>
    </head>
    <body>
        <h1>Verity Protocol - DID Management</h1>
        <p>Templates not found. Using API endpoints directly.</p>
        <ul>
            <li><a href="/docs">/docs - API Documentation</a></li>
            <li><a href="/api/accounts">/api/accounts - List Accounts</a></li>
        </ul>
    </body>
    </html>
    """

# ============================================================================
# Account Management API
# ============================================================================

@app.post("/api/accounts/create")
async def api_create_account():
    """
    Create a new account.
    Delegates to backend.create_account()
    """
    try:
        address = backend.create_account()
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "address": address,
                "message": "Account created successfully"
            }
        )
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/accounts")
async def api_list_accounts():
    """
    List all accounts.
    Delegates to backend.list_account()
    """
    try:
        addresses, diddoc_counts = backend.list_account()
        return JSONResponse(
            status_code=200,
            content={
                "accounts": addresses,
                "diddoc_counts": diddoc_counts or {}
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/accounts/select")
async def api_select_account(account_id: str = Form(...)):
    """
    Select an account as the current session.
    Delegates to backend.select_account_by_index()
    """
    try:
        # account_id can be index (1-based) or address
        try:
            result = backend.select_account(account_id)
            #result = backend.select_account_by_index(idx)
        except ValueError as exc:
            # If not an integer, treat as address lookup
            addresses, _ = backend.list_account()
            if account_id in addresses:
                idx = addresses.index(account_id) + 1
                result = backend.select_account_by_index(idx)
            else:
                raise HTTPException(status_code=400, detail="Account not found") from exc
        if result:
            _, addr = backend.is_active()
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "current_account": addr
                }
            )
        raise HTTPException(status_code=400, detail="Failed to select account")
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ============================================================================
# DID Document Management API
# ============================================================================
# pylint: disable=R
@app.post("/api/diddoc/create")
async def api_create_diddoc(
    organization_name: str = Form(...),
    namespace: str = Form(default="org"),
    entity_identifier: str = Form(...),
    jurisdiction: str = Form(default="US"),
    tier: str = Form(default="S"),
    account_id: str = Form(...),
    verification_methods: Optional[str] = Form(default="[]"),
    sign_after_create: Optional[str] = Form(default="0"),
    register_after_create: Optional[str] = Form(default="0")
):
    """
    Create a diddoc
    """
    try:
        # Ensure an active session: attempt to select the provided account
        # account_id may already be selected by the UI, but ensure it.
        try:
            # try numeric index
            idx = int(account_id)
            backend.select_account_by_index(idx)
        except VerityBackendError as e:
            res = await api_select_account(account_id)
            data = json.loads(res.body)
            if data['status'] != "success":
                raise HTTPException(status_code=400, detail="Bad req") from e
            if data['current_account'] == account_id:
                raise HTTPException(status_code=400, detail="Bad req") from e

        active, addr = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session after selecting account")

        # Build DID string same as CLI
        did = f"did:verity:{namespace}:{entity_identifier}"

        # Build verification methods from JSON sent by UI
        try:
            vms = json.loads(verification_methods or "[]")
        except VerityError:
            vms = []

        # Normalize verification methods into VerificationMethod instances (not dicts)
        vm_objs = []
        for i, vm in enumerate(vms):
            vm_id = vm.get("id") or f"{did}#key-{i+1}"
            vm_type = vm.get("type", "Ed25519VerificationKey2020")
            controller = vm.get("controller") or did
            public = vm.get("public_key") or vm.get("public") or vm.get("public_key_multibase")
            # Create VerificationMethod instance with correct field name
            vm_obj = VerificationMethod(
                id=vm_id,
                type=vm_type,
                controller=controller,
                public_key_multibase=public
            )
            vm_objs.append(vm_obj)

        # Compose DemoDIDDocument instance (not a dict) - matching CLI pattern
        diddoc = DemoDIDDocument(
            id=did,
            verification_method=vm_objs,
            authentication=[vm_objs[0].id] if vm_objs else [],
            service=[],
            metadata={
                "organizationName": organization_name,
                "jurisdiction": jurisdiction,
                "tier": tier,
                "createdBy": addr
            }
        )

        # Call backend.add_diddoc with proper BaseModel instance
        backend.add_diddoc(diddoc)

        # If backend.add_diddoc returns success, normalize for response
        response_payload = {"status": "created", "did": did}
        # Serialize the DemoDIDDocument to dict for JSON response
        try:
            response_payload["diddoc"] = diddoc.model_dump()
        except VerityError:
            response_payload["diddoc"] = repr(diddoc)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        # Sign after create (optional)
        if sign_after_create == "1":
            try:
                # backend.sign_diddoc accepts the DemoDIDDocument instance
                res = backend.sign_diddoc(diddoc)
                if res:
                    response_payload["signed"] = True
                else:
                    response_payload["signed"] = False
            except VerityError as e:
                response_payload["signed"] = False
                response_payload.setdefault("notes", []).append(f"signing failed: {str(e)}")

        # Register after create (placeholder)
        if register_after_create == "1":
            # Backend may not implement remote registration; do placeholder
            # Mirror CLI behavior by returning a placeholder success message
            response_payload["registered"] = True
            response_payload.setdefault("notes", []).append("Registration performed " \
            "by UI placeholder. Implement backend API to register DID.")

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        # Return error details for debugging
        raise HTTPException(status_code=500, detail=f"Failed to create DID Document: {e}") from e

@app.get("/api/diddoc/list")
async def api_list_diddocs():
    """
    List all DID Documents for the current account.
    Delegates to backend.list_diddocs()
    """
    try:
        active, addr = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")

        diddocs = backend.list_diddocs()
        # Serialize DemoDIDDocument instances to dicts for JSON response
        serialized_docs = []
        if diddocs:
            for doc in diddocs:
                try:
                    serialized_docs.append(doc.model_dump())
                except VerityError:
                    serialized_docs.append(str(doc))

        return JSONResponse(
            status_code=200,
            content={
                "diddocs": serialized_docs,
                "current_account": addr
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/diddoc/sign")
async def api_sign_diddoc(diddoc_index: int = Form(...)):
    """
    Sign a DID Document at the given index with the current account's private key.
    Follows the pattern from CLI's sign_diddoc()
    """
    try:
        active, _ = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")

        # Get the DID document
        diddocs = backend.list_sessions_diddocs()
        if not diddocs or diddoc_index < 0 or diddoc_index >= len(diddocs):
            raise HTTPException(status_code=400, detail="Invalid DID Document index")

        diddoc = diddocs[diddoc_index]

        # Sign it using backend method (same as CLI)
        result = backend.sign_diddoc(diddoc)
        print(result)
        if result:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "DID Document signed successfully",
                    "diddoc": diddoc.model_dump_json()
                }
            )
        raise HTTPException(status_code=400, detail="Failed to sign DID Document")
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/api/account/issuers")
async def api_list_issuers():
    """
    List all issuers for the current account.
    Delegates to backend.issuers()
    """
    try:
        active, addr = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")
        issuer = backend.issuers(addr)
        return JSONResponse(
            status_code=200,
            content={
                "issuer": issuer,
                "current_account": addr
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ============================================================================
# Claim Management API
# ============================================================================

@app.post("/api/claims/create")
async def api_create_claim(
    issuer: str = Form(...),
    message: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None)
):
    """
    Create a claim from a message or file.
    Uses middleware.create_claim() following CLI pattern
    """
    try:
        active, _ = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")
        if message:
            claim = backend.create_claims(message=message, issuer=issuer)
        elif file:
            # Save uploaded file temporarily and create claim from it
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False,
                                             suffix=os.path.splitext(file.filename)[1]) as tmp:
                contents = await file.read()
                tmp.write(contents)
                tmp_path = tmp.name

            try:
                claim = backend.create_claims(filepath=tmp_path, issuer=issuer)
            finally:
                os.unlink(tmp_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'message' or 'file' is required"
            )

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "claim_id": claim["claim_id"],
                "claim": claim["signed_claim"]
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ============================================================================
# Data Signing/Verification API
# ============================================================================

@app.post("/api/data/sign")
async def api_sign_data(message: str = Form(...)):
    """
    Sign arbitrary data with the current account's private key.
    Delegates to backend.sign_data() following CLI pattern
    """
    try:
        active, addr = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")

        signature = backend.sign_data(message)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": message,
                "signature": signature,
                "signer": addr
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/api/data/verify")
async def api_verify_data(
    address: str = Form(...),
    signature: str = Form(...),
    message: str = Form(...)
):
    """
    Verify a signature against an address and message.
    Delegates to backend.verify_data() following CLI pattern
    """
    try:
        is_valid = backend.verify_data(address, signature, message)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "address": address,
                "message": message,
                "is_valid": is_valid
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ============================================================================
# Key Management API
# ============================================================================

@app.get("/api/keys/export")
async def api_export_private_key():
    """
    Export the private key of the current account.
    Delegates to backend.export_priv_key()
    """
    try:
        active, addr = backend.is_active()
        if not active:
            raise HTTPException(status_code=400, detail="No active session")

        priv_key = backend.export_priv_key()
        return JSONResponse(
            status_code=200,
            content={
                "private_key": priv_key,
                "warning": "Keep this key safe. Do not share it.",
                "account": addr
            }
        )
    except HTTPException:
        raise
    except VerityCliError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        active, addr = backend.is_active()
        return {
            "status": "healthy",
            "service": "verity-ui",
            "version": "1.0.0",
            "active_session": addr if active else None
        }
    except VerityError:
        return {
            "status": "unhealthy",
            "service": "verity-ui",
            "version": "1.0.0"
        }

# ============================================================================
# Startup/Shutdown
# ============================================================================

def start():
    """
    Start the UI service.
    """
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001
    )

if __name__ == "__main__":
    start()
