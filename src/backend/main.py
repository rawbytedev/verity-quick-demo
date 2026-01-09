"""
Backend service for Verity: Session management, DID documents, claims, and signing.
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from src.middleware.claim_utils import generate_verification_url
from src.core import (sign_message, verify_signature,
                      create_ethereum_account, get_ethereum_address, get_ethereum_private_key)
from src.core.models import DemoDIDDocument
from src.core.io import ConsoleIO
from src.core.exceptions import VerityBackendError
from src.middleware import (
    create_claim,
    pin_claim,
    register,
    sign_claim,
    store,
    store_claim,
)
from .logs import setup_logging


class AccountSession:
    """Manages a single account session with its keys and state."""
    def __init__(self, account_data: dict):
        self.account = account_data
        self.address = get_ethereum_address(account_data)
        self.private_key = get_ethereum_private_key(account_data)
        self.diddocs: List[BaseModel] = []
        self.current_diddoc: Optional[BaseModel] = None

    def set_current_diddoc(self, diddoc: BaseModel):
        """
        Set the current diddoc for signing.

        Args:
            diddoc: DID document to set as current.
        """
        if diddoc is None:
            return
        self.current_diddoc = diddoc

    def add_diddoc(self, diddoc: BaseModel):
        """
        Add a new diddoc to session.

        Args:
            diddoc: DID document to add.
        """
        if diddoc is None:
            return
        self.diddocs.append(diddoc)
        self.set_current_diddoc(diddoc)

class VerityDemo:
    """Main backend service with session and DID document management."""
    def __init__(self, io: Optional[ConsoleIO] = None):
        self.saved = False
        self.io = io or ConsoleIO()
        setup_logging()
        self.sessions: Dict[str, AccountSession] = {}  # address -> session
        self.current_session: Optional[AccountSession] = None

    def is_active(self):
        """
        Check if there is an active session.

        Returns:
            Tuple of (is_active: bool, address: str).
        """
        if self.current_session:
            return (True, self.current_session.address)
        return (False, "0x0")

    def create_account(self) -> str:
        """
        Create a new account and set it as current session.

        Returns:
            Ethereum address of the new account.

        Raises:
            VerityBackendError: If account creation fails.
        """
        try:
            new_account = create_ethereum_account()
            address = get_ethereum_address(new_account)

            session = AccountSession(new_account)
            self.sessions[address] = session
            self.current_session = session
            return address
        except Exception as e:
            raise VerityBackendError(f"Failed to create account: {e}") from e

    def list_account(self):
        """
        List all existing accounts and their DID document counts.

        Returns:
            Tuple of (addresses: list, diddoc_counts: dict) or None if no accounts.
        """
        if not self.sessions:
            return None
        addresses = list(self.sessions.keys())
        diddoc = {}
        for _, addr in enumerate(addresses):
            if self.sessions[addr].diddocs:
                diddoc[addr] = {len(self.sessions[addr].diddocs)}
        return (addresses, diddoc)

    def select_account_by_index(self, idx: int) -> bool:
        """
        Select account by index (1-based).

        Args:
            idx: Account index (1-based).

        Returns:
            True if successful, False otherwise.
        """
        try:
            addresses = list(self.sessions.keys())
            self.current_session = self.sessions[addresses[idx - 1]]
            return True
        except (IndexError, KeyError) as e:
            logging.log(logging.WARNING, "Invalid selection: %s", e)
            return False

    def select_account(self, address: str) -> bool:
        """
        Select account by address.

        Args:
            address: Ethereum address of account to select.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.current_session = self.sessions[address]
            return True
        except KeyError as e:
            logging.log(logging.WARNING, "Invalid selection: %s", e)
            return False

    def add_diddoc(self, diddoc: DemoDIDDocument) -> bool:
        """
        Add a DID document to the current account session.

        Args:
            diddoc: DID document to add.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.current_session.add_diddoc(diddoc)
            return True
        except (AttributeError, VerityBackendError):
            return False

    def sign_diddoc(self, diddoc: BaseModel) -> bool:
        """
        Sign the DID Document with current account's private key.

        Args:
            diddoc: DID document to sign.

        Returns:
            True on success, False otherwise.
        """
        try:
            # Serialize the DID Document for signing
            message = diddoc.model_dump_json()
            # Use sign function
            signature = sign_message(self.current_session.private_key, message)
            diddoc.proof = {
                "type": "Ed25519Signature2020",
                "created": datetime.now().isoformat(),
                "proofValue": signature,
                "signer": self.current_session.address,
            }
            return True
        except (AttributeError, VerityBackendError) as e:
            logging.log(logging.WARNING, "Error signing: %s", e)
            return False

    def sign_data(self, message: str) -> Optional[str]:
        """
        Sign arbitrary data with current account.

        Args:
            message: Message to sign.

        Returns:
            JSON string with signature details, or None if error.
        """
        try:
            signature = sign_message(self.current_session.private_key, message)
            return json.dumps(
                {
                    "message": message,
                    "signature": signature,
                    "signer": self.current_session.address,
                    "timestamp": datetime.now().isoformat(),
                },
                indent=2,
            )
        except (AttributeError, VerityBackendError) as e:
            logging.log(logging.WARNING, "Error signing: %s",e)
            return None

    def verify_data(
        self, signer_address: str, signature: str, message: str
    ) -> bool:
        """
        Verify signature against signer address and message.

        Args:
            signer_address: Ethereum address of signer.
            signature: Signature as hex string.
            message: Original message.

        Returns:
            True if signature is valid, False otherwise.
        """
        try:
            if not all([signer_address, signature, message]):
                return False
            return verify_signature(signer_address, signature, message)
        except VerityBackendError as e:
            logging.log(logging.WARNING, "Error during verification: %s", e)
            return False

    def curr_account(self) -> str:
        """
        Get current account address.

        Returns:
            Current account address or "0x0" if none active.
        """
        if self.current_session:
            return self.current_session.address
        return "0x0"

    def list_diddocs(self) -> Optional[List[str]]:
        """
        List all DID Documents for current session.

        Returns:
            List of formatted DID document strings, or None if no session.
        """
        if not self.current_session or not self.current_session.diddocs:
            return None
        result = []
        for i, docs in enumerate(self.current_session.diddocs, 1):
            doc = docs.model_dump()
            has_proof = (
                "✓ Signed" if doc.get("proof", {}).get("proofValue") else "✗ Unsigned"
            )
            if "metadata" in doc:
                result.append(
                    f"{i}. {doc['id']} - {has_proof} "
                    f"Org: {doc['metadata'].get('organizationName', 'Unknown')}"
                )
            else:
                result.append(f"{i}. {doc['id']} - {has_proof}")
        return result

    def register_diddoc(self, idx: int) -> bool:
        """
        Register a DID document at the given index.

        Args:
            idx: 1-based index of DID document to register.

        Returns:
            True if successful, False otherwise.
        """
        try:
            doc = self.current_session.diddocs[idx - 1]
            res = store(doc, 5)
            register(doc.id, res.cid)
            logging.log(logging.INFO, "DID registered successfully")
            return True
        except (IndexError, VerityBackendError) as e:
            logging.log(logging.ERROR, "Error registering DID Document: %s",e)
            return False

    def save_session_state(self, filename: str = "verity_sessions.json") -> None:
        """
        Save all sessions to a file for persistence.

        Args:
            filename: Path to save sessions to.
        """
        try:
            state = {
                "sessions": {
                    addr: {
                        "address": session.address,
                        "privatekey": session.private_key.hex(),
                        "diddocs": [docs.model_dump_json() for docs in session.diddocs],
                    }
                    for addr, session in self.sessions.items()
                },
                "current_address": (
                    self.current_session.address if self.current_session else None
                ),
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self.io.print(f"\n💾 Session state saved to {filename}")
            self.saved = True
        except (IOError, VerityBackendError) as e:
            logging.log(logging.ERROR, "Could not save session state: %s", e)

    def export_priv_key(self) -> str:
        """
        Export private key of current account.

        Returns:
            Private key as hex string.
        """
        if not self.current_session:
            raise VerityBackendError("No active session")
        return self.current_session.private_key.hex()

    def create_claims(
        self, issuer: str, message: Optional[str] = None, filepath: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create, sign, and store a claim.

        Args:
            issuer: Issuer DID.
            message: Message to claim (optional).
            filepath: Path to file to claim (optional).

        Returns:
            Dict with claim details or None if error.
        """
        try:
            if message:
                claim_obj = create_claim(issuer, message=message)
            else:
                claim_obj = create_claim(issuer, file_path=filepath)
            signed_claim = sign_claim(claim_obj, self.current_session.private_key)
            claim_cid = store_claim(signed_claim)
            pin_claim(signed_claim.claim_id, claim_cid)
            verification_url = generate_verification_url(signed_claim)
            signed_claim.verification_url = verification_url
            return {
                "claim_id": signed_claim.claim_id,
                "cid": claim_cid,
                "verification_url": verification_url,
                "issuer": issuer,
                "signed_at": (
                    signed_claim.proof.get("created")
                    if signed_claim.proof
                    else None
                ),
                "signed_claim": signed_claim.model_dump() if signed_claim else None
            }
        except VerityBackendError as e:
            logging.log(logging.ERROR, "Error creating claims: %s", e)
            return None

    def list_diddocs_all(self) -> List[BaseModel]:
        """
        List all DID documents across all sessions.

        Returns:
            List of all DID documents.
        """
        docs: List[BaseModel] = []
        for _, accs in self.sessions.items():
            for doc in accs.diddocs:
                docs.append(doc)
        return docs

    def list_sessions_diddocs(self) -> List[BaseModel]:
        """
        List all Diddocs of an active session
        
        Returns:
            List of all DID sessions documents
        """
        address = self.current_session.address
        session_docs: List[BaseModel] = []
        diddocs = self.list_diddocs_all()
        for docs in diddocs:
            doc = docs.model_dump()

            for vm in doc.get("verification_method", []):
                public_address = vm.get("public_key_multibase")
                if public_address.startswith("eth:"):
                    if public_address == f"eth:{address}":
                        session_docs.append(docs)
                else:
                    if public_address == address:
                        session_docs.append(docs)
        return session_docs

    def issuers(self, address: str) -> List[str]:
        """
        Get list of issuer DIDs for a given address.

        Args:
            address: Ethereum address.

        Returns:
            List of issuer DIDs.
        """
        res = self.select_account(address)
        issuers_list = []
        if res:
            for _, docs in enumerate(self.current_session.diddocs):
                doc = docs.model_dump()
                issuers_list.append(doc["id"])
        diddocs = self.list_diddocs_all()
        for docs in diddocs:
            doc = docs.model_dump()
            for vm in doc.get("verification_method", []):
                if vm.get("public_key_multibase") == f"eth:{address}":
                    issuers_list.append(doc["id"])
        return issuers_list
