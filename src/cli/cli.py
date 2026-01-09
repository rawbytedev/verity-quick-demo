"""
CLI: Main interface to generate DID documents and claims, sign them, register them.
"""
import sys
import traceback
from typing import Dict, Optional
from enum import Enum
import argparse
from pydantic import BaseModel
from src.core.models import DemoDIDDocument, VerificationMethod, ServiceEndpoint
from src.core.io import ConsoleIO
from src.core.exceptions import VerityCliError
from src.middleware import create_claim, pin_claim, sign_claim, store_claim
from src.backend import VerityDemo


class MenuState(Enum):
    """Menu states for CLI navigation."""

    MAIN = "main"
    CREATE_ACCOUNT = "create_account"
    SELECT_ACCOUNT = "select_account"
    CREATE_DIDDOC = "create_diddoc"
    REGISTER_DIDDOC = "register_diddoc"
    SIGN_DATA = "sign_data"
    VERIFY_DATA = "verify_data"
    SAVE = "save_session"
    EXIT = "exit"
    LISTDID = "list_did"
    PRIVKEY = "priv_key"
    CLAIM = "create_claims"


class VerityDemoCLI:
    """Main CLI application with session management."""

    def __init__(self, io: Optional[ConsoleIO] = None):
        self.saved = False
        self.io = io or ConsoleIO()
        self.state = MenuState.MAIN
        self.verity = VerityDemo()

    def run(self):
        """Main CLI loop."""
        self.io.print("\n" + "="*50)
        self.io.print("VERITY PROTOCOL - DEMO CLI")
        self.io.print("="*50)
        state ={
            MenuState.MAIN:self.show_main_menu,
            MenuState.CREATE_ACCOUNT:self.handle_create_account,
            MenuState.SELECT_ACCOUNT:self.handle_select_account,
            MenuState.CREATE_DIDDOC:self.handle_create_diddoc,
            MenuState.SIGN_DATA:self.handle_sign_data,
            MenuState.REGISTER_DIDDOC:self.register_diddoc,
            #MenuState.SAVE:self.save_session_state,
            MenuState.LISTDID:self.list_diddocs,
            MenuState.PRIVKEY:self.export_priv_key,
            MenuState.CLAIM:self.create_claim_opts
            }
        while self.state != MenuState.EXIT:
            state[self.state]()

        print("\nThank you for using Verity Protocol Demo!")

    def show_main_menu(self):
        """Display the main menu based on current session state."""
        active, addr = self.verity.is_active()
        if active:
            self.io.print(f"\n{' CURRENT SESSION: ' + addr}")
        else:
            self.io.print(f"\n{' No active session ':-^50}")
        self.io.print("\nMAIN MENU:")
        print("1. Create new account")
        print("2. Select existing account")

        if active:
            print("3. Create DID Document")
            print("4. Sign a message")
            print("5. Verify a signature")
            print("6. List my DID Documents")
            print("7. Register DID Document")
            print("8. Save Session (Disabled)")
            print("9. Export Private Key")
            print("10. Create Claims")

        print("0. Exit")

        choice = self.io.input("\nSelect option: ").strip()
        menu = {
            "1": MenuState.CREATE_ACCOUNT,
            "2": MenuState.SELECT_ACCOUNT,
            "3": MenuState.CREATE_DIDDOC,
            "4": MenuState.SIGN_DATA,
            "5": MenuState.VERIFY_DATA,
            "6": MenuState.LISTDID,
            "7": MenuState.REGISTER_DIDDOC,
            "8": MenuState.SAVE,
            "9": MenuState.PRIVKEY,
            "10": MenuState.CLAIM,
            "0": MenuState.EXIT,
        }
        try:
            self.state = menu[choice]
        except KeyError:
            self.io.print("Invalid option. Please try again.")

    def handle_create_account(self):
        """Create a new account and set it as current session."""
        self.io.print("\n" + "-" * 30)
        self.io.print("CREATE NEW ACCOUNT")
        self.io.print("-" * 30)

        try:
            address = self.verity.create_account()
            self.io.print("\n✅ Account created successfully!")
            self.io.print(f"   Address: {address}")
            self.io.print("   Private key stored in session")

            # Ask if user wants to create a DIDDoc immediately
            create_now = (
                self.io.input("\nCreate a DID Document for "
                              "this account now? (y/N): ")
                .lower()
            )
            if create_now == "y":
                self.state = MenuState.CREATE_DIDDOC
            else:
                self.state = MenuState.MAIN
        except VerityCliError as e:
            self.io.print(f"❌ Error creating account: {e}")
            self.state = MenuState.MAIN

    def handle_select_account(self):
        """Select from existing accounts."""
        accounts= self.verity.list_account()
        if not accounts:
            print("\n❌ No accounts exist yet. Create one first.")
            self.state = MenuState.MAIN
            return

        self.io.print("\n" + "-"*30)
        self.io.print("SELECT ACCOUNT")
        self.io.print("-"*30)

        addresses = accounts[0]
        for i, addr in enumerate(addresses, 1):
            print(f"{i}. {addr}")
            try:
                doccount = accounts[1][addr]
                print(f"   ({doccount} DID Documents)")
            except KeyError:
                continue
        self.io.print("0. Back to main menu")

        try:
            choice = self.io.input("\nSelect account number: ").strip()
            if choice == "0":
                self.state = MenuState.MAIN
                return

            idx = int(choice) - 1
            if 0 <= idx < len(addresses):
                res = self.verity.select_account_by_index(idx + 1)
                if res:
                    self.io.print(f"\n✅ Switched to account: {addresses[idx]}")
                    self.state = MenuState.MAIN
            else:
                self.io.print("Invalid selection.")
        except ValueError:
            self.io.print("Please enter a valid number.")

    def handle_create_diddoc(self):
        """Interactive DID Document creation with user input."""
        active, addr = self.verity.is_active()
        if not active:
            print("❌ No active session. Please select an account first.")
            self.state = MenuState.MAIN
            return
        self.io.print("\n" + "="*50+"\nCREATE DID DOCUMENT"+"="*50)
        self.io.print(f"Creating for account: {addr}")
        ## Basic Information
        user_input = self.basic_input()
        if user_input is None:
            return
        # Create verification methods for the current account
        ### VERIFICATION
        verification_methods= self.verification_method_input(user_input, addr)

        # Get service endpoints
        ### SERVICES
        services = []
        self.io.print("\n--- Service Endpoints (optional) ---")
        while True:
            add_service = self.io.input("Add a service endpoint? (y/N): ").lower()
            if add_service != 'y':
                break

            service_id = self.io.input("Service ID "
            "[vcs]: ").strip() or "vcs"
            service_type = self.io.input("Service type [VerifiableCredentialService]: " \
            "").strip() or "VerifiableCredentialService"
            endpoint = self.io.input("Endpoint URL: ").strip()

            if endpoint:
                services.append(ServiceEndpoint(
                    id=f"{user_input["full_did"]}#{service_id}",
                    type=service_type,service_endpoint=endpoint))
                self.io.print(f"✅ Added service: {service_type}")

        # Get metadata
        ### METADATA
        self.io.print("\n--- Organization Metadata ---")
        org_name = self.io.input("Organization name: ").strip()
        jurisdiction = self.io.input("Jurisdiction (2-letter code) [US]: ").strip() or "US"
        user_input["tier"] = self.io.input("Tier (S/1/2) [S]: ").strip() or "S"

        # Create the DID Document
        diddoc = DemoDIDDocument(
            id=user_input["full_did"],
            verification_method=verification_methods,
            authentication=[user_input["vm_id"]],
            service=services,
            metadata={
                "organizationName": org_name,
                "jurisdiction": jurisdiction,
                "tier": user_input["tier"],
                "createdBy": addr
                }
            )
        res = self.verity.add_diddoc(diddoc)
        if not res:
            self.io.print("Unable to add diddoc")
        self.io.print(f"\n{'✅ SUCCESS! ':=^50}")
        self.io.print("DID Document created:")
        self.io.print(f"  DID: {user_input["full_did"]}")
        self.io.print(f"  Organization: {org_name}")
        self.io.print(f"  Verification Method: {user_input["vm_id"]}")
        self.io.print(f"  Services: {len(services)}")
        self.io.print(f"  Tier: {user_input["tier"]}")

        # Ask to sign it immediately
        sign_now = self.io.input("\nSign this DID Document now? (y/N): ").lower()
        if sign_now == 'y':
            self.sign_diddoc(diddoc)
        self.state = MenuState.MAIN

    def basic_input(self, user_input:Dict=None):
        """Takes Basic inputs"""
        if user_input is None:
            user_input = {}
        # Get basic DID information
        self.io.print("\n--- Basic Information ---")
        user_input["did_namespace"] = self.io.input("Enter namespace "
        "(gov/org/media/edu/ind) [org]: ").strip() or "org"
        user_input["did_entity"] = self.io.input("Enter entity identifier "
        "(e.g., 'election-commission'): ").strip()
        if not user_input["did_entity"]:
            print("Entity identifier is required!")
            return None
        user_input["full_did"] = "did:"\
        f"verity:{user_input["did_namespace"]}:{user_input["did_entity"]}"
        return user_input

    def verification_method_input(self, user_input:Dict, addr) -> list[VerificationMethod]:
        """Takes input for verification methods and return it all at once"""
        verification_methods:list[VerificationMethod] = []

        # First verification method (with defaults)
        user_input["vm_id"] = f'{user_input["full_did"]}#key-1'

        self.io.print("\n--- Verification Method (Primary) ---")
        self.io.print(f"Default key ID: {user_input["vm_id"]}")

        # Get key type (with default)
        user_input["vm_type"] = self.io.input("Key type "
        "[Ed25519VerificationKey2020]: ").strip() or "Ed25519VerificationKey2020"

        # Create verification method using current account's address as the public key reference
        verification_method = VerificationMethod(
            id=user_input["vm_id"],
            type=user_input["vm_type"],
            controller=user_input["full_did"],
            public_key_multibase=f"eth:{addr}"  # Simplified for demo
            )
        verification_methods.append(verification_method)

        # Allow adding additional verification methods
        vm_counter = 2
        while True:
            add_vm = self.io.input("\nAdd another verification method? (y/N): ").lower()
            if add_vm != 'y':
                break

            self.io.print(f"\n--- Additional Verification Method #{vm_counter} ---")

            vm_id = self.io.input("Verification method ID "
            f"[{user_input['full_did']}#key-{vm_counter}]: "
            "").strip() or f"{user_input['full_did']}#key-{vm_counter}"
            vm_type = self.io.input("Key type "
            "[Ed25519VerificationKey2020]: ").strip() or "Ed25519VerificationKey2020"

            controller = self.io.input("Controller DID "
            f"[{user_input['full_did']}]: ").strip() or user_input['full_did']

            public_key = self.io.input("Public key multibase (e.g., eth:0x... or z...): ").strip()

            if not public_key:
                self.io.print("⚠️  Public key is required. Skipping this verification method.")
                continue

            additional_vm = VerificationMethod(
                id=vm_id,
                type=vm_type,
                controller=controller,
                public_key_multibase=public_key
            )
            verification_methods.append(additional_vm)
            self.io.print(f"✅ Added verification method: {vm_type}")
            vm_counter += 1
        return verification_methods
    def sign_diddoc(self, diddoc: BaseModel):
        """Sign the DID Document with current account's private key."""
        try:
            res = self.verity.sign_diddoc(diddoc)
            if res:
                self.io.print("\n📝 DID Document signed successfully!")
        except VerityCliError as e:
            print(f"❌ Error signing: {e}")

    def handle_sign_data(self):
        """Sign arbitrary data with current account."""
        active, addr = self.verity.is_active()
        if not active:
            print("❌ No active session.")
            self.state = MenuState.MAIN
            return

        self.io.print("\n" + "-"*30)
        self.io.print("SIGN DATA")
        self.io.print(f"Using account: {addr}")
        self.io.print("-"*30)

        message = self.io.input("\nEnter message to sign: ").strip()
        if not message:
            print("Message cannot be empty.")
            self.state =MenuState.MAIN
            return

        try:
            res = self.verity.sign_data(message)
            if res:
                self.io.print("\n✅ Signature created:")
                self.io.print(f"   Message: {message[:50]}{'...' if len(message) > 50 else ''}")
                self.io.print("\n📋 Full output for verification:")
                self.io.print(res)
        except VerityCliError as e:
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
            is_valid = self.verity.verify_data(signer_address, signature, message)

            self.io.print(f"\n{'✅ SIGNATURE VALID' if is_valid else '❌ SIGNATURE INVALID'}")
            self.io.print(f"   Signer: {signer_address}")
            self.io.print(f"   Message: {message[:50]}{'...' if len(message) > 50 else ''}")
        except VerityCliError as e:
            print(f"❌ Error during verification: {e}")

    def list_diddocs(self, local:bool=False):
        """List all DID Documents for current session."""
        docs = self.verity.list_diddocs()
        if not docs:
            print("No DID Documents created yet.")
            self.state = MenuState.MAIN
            return

        self.io.print(f"\n📄 DID Documents for {self.verity.curr_account()}:")
        for _, doc in enumerate(docs, 1):
            self.io.print(doc)
        if not local:
            self.state = MenuState.MAIN

    def register_diddoc(self): ## improve a bit
        """Register diddocs from user selection"""
        self.list_diddocs(True)
        self.io.print("Note: Only diddocs that contains proofs(signed) are valid")
        i = int(self.io.input("~> "))
        try:
            res = self.verity.register_diddoc(i-1)
            if res:
                self.io.print("DID register successfully")
        except VerityCliError as e:
            self.io.print(f"Note: Error while registering DID Document {e}")
        self.state =MenuState.MAIN

    def export_priv_key(self):
        """Exports Priv key account to screen"""
        accs = self.verity.list_account()
        if not accs:
            return
        for i, acc in enumerate(accs[0], start=1):
            self.io.print(f"{i} - {acc}")
        inp = int(self.io.input("~> "))
        self.verity.select_account_by_index(inp)
        self.io.print(f"Private Key: {self.verity.export_priv_key()}")
        self.state =MenuState.MAIN

    def create_claim_opts(self):
        """
        Docstring for create_claim_opts
        
        :param self: Description
        """
        active, addr = self.verity.is_active()
        if active:
            self.io.print("Listing Available issuers")
            issuers = self.verity.issuers(addr)
            for iss in issuers:
                self.io.print(iss)
            issuer = self.io.input("Enter Issuer: ")
            msg = self.io.input("message(y/N): ").strip().lower()
            if msg == "y":
                message = self.io.input("Enter message(claim): ")
                self.io.print(self.verity.create_claims(issuer, message))
            else:
                path = self.io.input("Enter the path to file: ")
                self.io.print(self.verity.create_claims(issuer, filepath=path))
        self.state = MenuState.MAIN

def main():
    """Entry point for the CLI."""
    # support headless operation via env/args
    parser = argparse.ArgumentParser(prog="verity-demo",
                                     description="Verity protocol demo CLI")
    parser.add_argument("--claim-file",
                        help="Create a claim from a file and " \
                        "print the claim id and optionally store it")
    parser.add_argument("--message",
                        help="Create a claim from a short message/text")
    parser.add_argument("--issuer",
                        help="Issuer DID to use when creating claim")
    parser.add_argument("--sign-priv",
                        help="Private key hex to sign the generated claim")
    parser.add_argument("--verification-method",
                        help="Verification method identifier"
                        "to include in proof (e.g. did:...#key-1)")
    parser.add_argument("--store", action="store_true",
                        help="Store the generated (and optionally signed) claim via middleware")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Do not start interactive mode")

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
            claim = sign_claim(claim, args.sign_priv)
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
    except VerityCliError as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
