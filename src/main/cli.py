"""
CLI the main interface to generate diddocs/claims, sign them, register them
"""
import sys
import traceback
import json
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import argparse
import middleware
from signer import sign, verify, eth_key, create_new_eth, eth_addr
from shared_model import DemoDIDDocument, VerificationMethod, ServiceEndpoint
from pydantic import BaseModel

from claim_utils import (
    create_claim,
    pin_claim,
    sign_claim,
    store_claim,
)

class MenuState(Enum):
    "Menu States specifies all state taken by the menu"
    MAIN = "main"
    CREATE_ACCOUNT = "create_account"
    SELECT_ACCOUNT = "select_account"
    CREATE_DIDDOC = "create_diddoc"
    REGISTER_DIDDOC = "register_diddoc"
    SIGN_DATA = "sign_data"
    VERIFY_DATA = "verify_data"
    SAVE = "save_session"
    EXIT = "exit"

class AccountSession:
    """Manages a single account session with its keys and state."""
    def __init__(self, account_data: dict):
        self.account = account_data
        self.address = eth_addr(account_data)
        self.private_key = eth_key(account_data)
        self.diddocs: List[BaseModel] = []
        self.current_diddoc: Optional[BaseModel] = None


class ConsoleIO:
    """Thin wrapper around input/print so we can inject test doubles."""
    def input(self, prompt: str = "") -> str:
        """
        Read a string from standard input. The trailing newline is stripped.

The prompt string, if given, is printed to standard output without a
trailing newline before reading input.
        """
        return input(prompt)

    def print(self, *args, **kwargs) -> None:
        """
        Prints the values to a stream, or to sys.stdout by default.
        """
        print(*args, **kwargs)

class VerityDemoCLI:
    """Main CLI application with session management."""

    def __init__(self, io: Optional[ConsoleIO] = None):
        self.saved = False
        self.io = io or ConsoleIO()
        self.sessions: Dict[str, AccountSession] = {}  # address -> session
        self.current_session: Optional[AccountSession] = None
        self.state = MenuState.MAIN

    def run(self):
        """Main CLI loop."""
        self.io.print("\n" + "="*50)
        self.io.print("VERITY PROTOCOL - DEMO CLI")
        self.io.print("="*50)

        while self.state != MenuState.EXIT:
            if self.state == MenuState.MAIN:
                self.show_main_menu()
            elif self.state == MenuState.CREATE_ACCOUNT:
                self.handle_create_account()
            elif self.state == MenuState.SELECT_ACCOUNT:
                self.handle_select_account()
            elif self.state == MenuState.CREATE_DIDDOC:
                self.handle_create_diddoc()
            elif self.state == MenuState.SIGN_DATA:
                self.handle_sign_data()
            elif self.state == MenuState.VERIFY_DATA:
                self.handle_verify_data()
            elif self.state == MenuState.REGISTER_DIDDOC:
                self.register_diddoc()
            elif self.state == MenuState.SAVE:
                self.save_session_state()

        print("\nThank you for using Verity Protocol Demo!")

    def show_main_menu(self):
        """Display the main menu based on current session state."""
        self.io.print(f"\n{' CURRENT SESSION: ' + self.current_session.address if self.current_session else ' No active session ':-^50}")
        self.io.print("\nMAIN MENU:")
        print("1. Create new account")
        print("2. Select existing account")

        if self.current_session:
            print("3. Create DID Document")
            print("4. Sign a message")
            print("5. Verify a signature")
            print("6. List my DID Documents")
            print("7. Register DID Document")
            print("8. Save Session")

        print("0. Exit")

        choice = self.io.input("\nSelect option: ").strip()

        if choice == "1":
            self.state = MenuState.CREATE_ACCOUNT
        elif choice == "2":
            self.state = MenuState.SELECT_ACCOUNT
        elif self.current_session:
            if choice == "3":
                self.state = MenuState.CREATE_DIDDOC
            elif choice == "4":
                self.state = MenuState.SIGN_DATA
            elif choice == "5":
                self.state = MenuState.VERIFY_DATA
            elif choice == "6":
                self.list_diddocs()
            elif choice == "7":
                self.state = MenuState.REGISTER_DIDDOC
            elif choice == "8":
                self.state = MenuState.SAVE
            elif choice == "0":
                self.state = MenuState.EXIT
        else:
            self.io.print("Invalid option. Please try again.")

    def handle_create_account(self):
        """Create a new account and set it as current session."""
        self.io.print("\n" + "-"*30)
        self.io.print("CREATE NEW ACCOUNT")
        self.io.print("-"*30)

        try:
            # Use your existing createNew function
            new_account = create_new_eth()
            address = eth_addr(new_account)

            session = AccountSession(new_account)
            self.sessions[address] = session
            self.current_session = session

            self.io.print("\n✅ Account created successfully!")
            self.io.print(f"   Address: {address}")
            self.io.print("   Private key stored in session")

            # Ask if user wants to create a DIDDoc immediately
            create_now = self.io.input("\nCreate a DID Document for this account now? (y/N): ").lower()
            if create_now == 'y':
                self.state = MenuState.CREATE_DIDDOC
            else:
                self.state = MenuState.MAIN
        except Exception as e:
            self.io.print(f"❌ Error creating account: {e}")
            self.state = MenuState.MAIN

    def handle_select_account(self):
        """Select from existing accounts."""
        if not self.sessions:
            print("\n❌ No accounts exist yet. Create one first.")
            self.state = MenuState.MAIN
            return

        self.io.print("\n" + "-"*30)
        self.io.print("SELECT ACCOUNT")
        self.io.print("-"*30)

        addresses = list(self.sessions.keys())
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")
            if self.sessions[addr].diddocs:
                print(f"   ({len(self.sessions[addr].diddocs)} DID Documents)")

        self.io.print("0. Back to main menu")

        try:
            choice = self.io.input("\nSelect account number: ").strip()
            if choice == "0":
                self.state = MenuState.MAIN
                return

            idx = int(choice) - 1
            if 0 <= idx < len(addresses):
                self.current_session = self.sessions[addresses[idx]]
                self.io.print(f"\n✅ Switched to account: {addresses[idx]}")
                self.state = MenuState.MAIN
            else:
                self.io.print("Invalid selection.")
        except ValueError:
            self.io.print("Please enter a valid number.")

    def handle_create_diddoc(self): ## split into multiple components
        """Interactive DID Document creation with user input."""
        if not self.current_session:
            print("❌ No active session. Please select an account first.")
            self.state = MenuState.MAIN
            return

        self.io.print("\n" + "="*50)
        self.io.print("CREATE DID DOCUMENT")
        self.io.print("="*50)
        self.io.print(f"Creating for account: {self.current_session.address}")

        try:
            # Get basic DID information
            self.io.print("\n--- Basic Information ---")
            did_namespace = self.io.input("Enter namespace (gov/org/media/edu/ind) [org]: ").strip() or "org"
            did_entity = self.io.input("Enter entity identifier (e.g., 'election-commission'): ").strip()
            if not did_entity:
                print("Entity identifier is required!")
                return

            full_did = f"did:verity:{did_namespace}:{did_entity}"

            # Create verification method for the current account
            vm_id = f"{full_did}#key-1"

            self.io.print("\n--- Verification Method ---")
            self.io.print(f"Default key ID: {vm_id}")

            # Get key type (with default)
            vm_type = self.io.input("Key type [Ed25519VerificationKey2020]: ").strip() or "Ed25519VerificationKey2020"

            # Create verification method using current account's address as the public key reference
            # In a real implementation, you'd use the actual public key
            verification_method = VerificationMethod(
                id=vm_id,
                type=vm_type,
                controller=full_did,
                public_key_multibase=f"eth:{self.current_session.address}"  # Simplified for demo
            )

            # Get service endpoints
            services = []
            self.io.print("\n--- Service Endpoints (optional) ---")
            while True:
                add_service = self.io.input("Add a service endpoint? (y/N): ").lower()
                if add_service != 'y':
                    break

                service_id = self.io.input("Service ID [vcs]: ").strip() or "vcs"
                service_type = self.io.input("Service type [VerifiableCredentialService]: ").strip() or "VerifiableCredentialService"
                endpoint = self.io.input("Endpoint URL: ").strip()

                if endpoint:
                    services.append(ServiceEndpoint(
                        id=f"{full_did}#{service_id}",type=service_type,service_endpoint=endpoint))
                    self.io.print(f"✅ Added service: {service_type}")

            # Get metadata
            self.io.print("\n--- Organization Metadata ---")
            org_name = self.io.input("Organization name: ").strip()
            jurisdiction = self.io.input("Jurisdiction (2-letter code) [US]: ").strip() or "US"
            tier = self.io.input("Tier (S/1/2) [S]: ").strip() or "S"

            # Create the DID Document
            diddoc = DemoDIDDocument(
                id=full_did,
                verification_method=[verification_method],
                authentication=[vm_id],
                service=services,
                metadata={
                    "organizationName": org_name,
                    "jurisdiction": jurisdiction,
                    "tier": tier,
                    "createdBy": self.current_session.address
                }
            )

            self.current_session.diddocs.append(diddoc)
            self.current_session.current_diddoc = diddoc
            self.io.print(f"\n{'✅ SUCCESS! ':=^50}")
            self.io.print("DID Document created:")
            self.io.print(f"  DID: {full_did}")
            self.io.print(f"  Organization: {org_name}")
            self.io.print(f"  Verification Method: {vm_id}")
            self.io.print(f"  Services: {len(services)}")
            self.io.print(f"  Tier: {tier}")

            # Ask to sign it immediately
            sign_now = self.io.input("\nSign this DID Document now? (y/N): ").lower()
            if sign_now == 'y':
                self.sign_diddoc(diddoc)

            self.state = MenuState.MAIN

        except Exception as e:
            self.io.print(f"\n❌ Error creating DID Document: {e}")
            traceback.print_exc()
            self.state = MenuState.MAIN

    def sign_diddoc(self, diddoc: BaseModel):
        """Sign the DID Document with current account's private key."""
        try:
            # Serialize the DID Document for signing
            message = diddoc.model_dump_json()

            # Use sign function
            signature = sign(self.current_session.private_key, message)

            self.io.print("\n📝 DID Document signed successfully!")
            self.io.print(f"   Signature: {signature[:50]}...")
            diddoc.proof = {
                "type": "Ed25519Signature2020",
                "created": datetime.now().isoformat(),
                "verificationMethod": diddoc.verification_method[0].id,
                "proofValue": signature,
                "signer": self.current_session.address
            }
        except Exception as e:
            print(f"❌ Error signing: {e}")

    def handle_sign_data(self):
        """Sign arbitrary data with current account."""
        if not self.current_session:
            print("❌ No active session.")
            self.state = MenuState.MAIN
            return

        self.io.print("\n" + "-"*30)
        self.io.print("SIGN DATA")
        self.io.print(f"Using account: {self.current_session.address}")
        self.io.print("-"*30)

        message = self.io.input("\nEnter message to sign: ").strip()
        if not message:
            print("Message cannot be empty.")
            self.state =MenuState.MAIN
            return

        try:
            signature = sign(self.current_session.private_key, message)
            self.io.print("\n✅ Signature created:")
            self.io.print(f"   Message: {message[:50]}{'...' if len(message) > 50 else ''}")
            self.io.print(f"   Signature: {signature}")
            self.io.print("\n📋 Full output for verification:")
            self.io.print(json.dumps({
                "message": message,
                "signature": signature,
                "signer": self.current_session.address,
                "timestamp": datetime.now().isoformat()
            }, indent=2))

        except Exception as e:
            print(f"❌ Error signing: {e}")

    def handle_verify_data(self):
        """Verify a signature."""
        self.io.print("\n" + "-"*30)
        self.io.print("VERIFY SIGNATURE")
        self.io.print("-"*30)

        try:
            signer_address = self.io.input("Signer's address: ").strip()
            signature = self.io.input("Signature (hex): ").strip()
            message = self.io.input("Original message: ").strip()

            if not all([signer_address, signature, message]):
                print("All fields are required.")
                return

            # Use your existing verify function
            is_valid = verify(signer_address, signature, message)

            self.io.print(f"\n{'✅ SIGNATURE VALID' if is_valid else '❌ SIGNATURE INVALID'}")
            self.io.print(f"   Signer: {signer_address}")
            self.io.print(f"   Message: {message[:50]}{'...' if len(message) > 50 else ''}")
        except Exception as e:
            print(f"❌ Error during verification: {e}")

    def list_diddocs(self):
        """List all DID Documents for current session."""
        if not self.current_session or not self.current_session.diddocs:
            print("No DID Documents created yet.")
            return
        self.io.print(f"\n📄 DID Documents for {self.current_session.address}:")
        for i, docs in enumerate(self.current_session.diddocs, 1):
            doc = docs.model_dump()
            has_proof = "✓ Signed" if 'proofValue' in doc['proof'] else "✗ Unsigned"
            self.io.print(f"{i}. {doc['id']} - {has_proof}")
            if 'metadata' in doc:
                self.io.print(f"   Org: {doc['metadata'].get('organizationName', 'Unknown')}")

    def register_diddoc(self): ## improve a bit
        """Register diddocs from user selection"""
        self.list_diddocs()
        self.io.print("Note: Only diddocs that contains proofs(signed) are valid")
        i = int(self.io.input("~> "))
        try:
            doc = self.current_session.diddocs[i-1]
            res=middleware.store(doc, 5)
            middleware.register(doc.id, res.cid)
            self.io.print("DID register successfully")
        except Exception as e:
            self.io.print(f"Note: Error while registering DID Document {e}")
        self.state =MenuState.MAIN

    def save_session_state(self, filename="verity_sessions.json"): ## Improve it
        """Save sessions to file for persistence."""
        try:
            state = {
                "sessions": {
                    addr: {
                        "address": session.address,
                        "privatekey":session.private_key.hex(),
                        "diddocs": [docs.model_dump_json() for docs in session.diddocs]
                    }
                    for addr, session in self.sessions.items()
                },
                "current_address": self.current_session.address if self.current_session else None
            }
            with open(filename, 'w', encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self.io.print(f"\n💾 Session state saved to {filename}")
            self.saved = True
        except Exception as e:
            self.io.print(f"Note: Could not save session state: {e}")
        self.state =MenuState.MAIN

def main():
    """Entry point for the CLI."""
    # support headless operation via env/args
    parser = argparse.ArgumentParser(prog="verity-demo", description="Verity protocol demo CLI")
    parser.add_argument("--claim-file", help="Create a claim from a file and print the claim id and optionally store it")
    parser.add_argument("--message", help="Create a claim from a short message/text")
    parser.add_argument("--issuer", help="Issuer DID to use when creating claim")
    parser.add_argument("--sign-priv", help="Private key hex to sign the generated claim")
    parser.add_argument("--verification-method", help="Verification method identifier to include in proof (e.g. did:...#key-1)")
    parser.add_argument("--store", action="store_true", help="Store the generated (and optionally signed) claim via middleware")
    parser.add_argument("--no-interactive", action="store_true", help="Do not start interactive mode")

    args = parser.parse_args()

    # Headless flow: if claim-file or message provided, do create/sign/store and exit
    if args.claim_file or args.message:
        if not args.issuer:
            print("--issuer is required for headless claim creation")
            sys.exit(2)

        if args.claim_file:
            claim = create_claim(file_path=args.claim_file, issuer_did=args.issuer)
        else:
            claim = create_claim(message=args.message, issuer_did=args.issuer)

        print(f"Created claim id: {claim.claim_id}")

        if args.sign_priv:
            vm = args.verification_method or f"{args.issuer}#key-1"
            claim = sign_claim(claim, args.sign_priv, vm)
            print(f"Signed claim; proof created (verification_method={vm})")

        if args.store:
            cid = store_claim(claim)
            print(f"Stored claim; cid={cid}")
            pin_claim(claim.claim_id,cid)

        # do not continue to interactive mode
        if args.no_interactive:
            return

    cli = VerityDemoCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        if not cli.saved:
            print("\n\n⚠️  Demo interrupted. Sessions were not saved.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
