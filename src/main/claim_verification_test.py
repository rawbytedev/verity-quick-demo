from signer import create_new_eth, eth_addr, eth_key, verify
from claim_utils import create_claim, sign_claim
from shared_model import DemoDIDDocument, VerificationMethod


def _extract_address_from_vm(vm: VerificationMethod) -> str:
    """Helper to extract an Ethereum address from verification method's public_key_multibase.

    For this demo/tests we encode addresses as plain text (e.g. '0xabc...') or 'eth:0xabc...'.
    """
    pk = vm.public_key_multibase
    if pk.startswith("eth:"):
        return pk.split(":", 1)[1]
    return pk


def test_claim_verification_success():
    issuer = "did:example:org-verify"
    # create a claim
    claim = create_claim(message="Verify me",issuer_did=issuer)

    # create a new keypair to sign
    acct = create_new_eth()
    addr = eth_addr(acct)
    priv = eth_key(acct)

    # create a DID doc for the issuer that contains the verification method pointing to this address
    vm_id = f"{issuer}#key-1"
    vm = VerificationMethod(id=vm_id, type="Ed25519VerificationKey2020", controller=issuer, public_key_multibase=f"eth:{addr}")
    diddoc = DemoDIDDocument(id=issuer, verification_method=[vm], authentication=[vm_id], service=[])
    message = claim.model_dump_json()
    # sign the claim with our private key and attach proof
    signed = sign_claim(claim, priv, vm_id)
    # verify: recover address from signature and ensure it matches a key in the diddoc
    sig = signed.proof.get("proofValue")
    
    print(verify(addr, sig, message))
    # check each verification method in diddoc
    matched = False
    matched_vm = None
    for method in diddoc.verification_method:
        candidate_addr = _extract_address_from_vm(method)
        if verify(candidate_addr, sig, message):
            matched = True
            matched_vm = method.id
            break
    assert matched is True
    assert matched_vm == vm_id


def test_claim_verification_fails_with_wrong_key():
    issuer = "did:example:org-verify"
    claim = create_claim(message="Do not verify me", issuer_did=issuer)

    # signer uses one keypair
    signer_acct = create_new_eth()
    signer_priv = eth_key(signer_acct)

    # DID doc lists a different key
    other_acct = create_new_eth()
    other_addr = eth_addr(other_acct)
    vm_id = f"{issuer}#key-1"
    vm = VerificationMethod(id=vm_id, type="Ed25519VerificationKey2020", controller=issuer, public_key_multibase=f"eth:{other_addr}")
    diddoc = DemoDIDDocument(id=issuer, verification_method=[vm], authentication=[vm_id], service=[])
    message = claim.model_dump_json()
    signed = sign_claim(claim, signer_priv, vm_id)
    sig = signed.proof.get("proofValue")
    

    verified_any = any(verify(_extract_address_from_vm(m), sig, message) for m in diddoc.verification_method)
    assert verified_any is False

def test_claim_verification_with_diff_keys():
    issuer = "did:example:org-verify"
    claim = create_claim(message="Do not verify me", issuer_did=issuer)

    # signer uses one keypair
    signer_acct = create_new_eth()
    signer_priv = eth_key(signer_acct)
    signer_addr = eth_addr(signer_acct)
    m_vm_id = f"{issuer}#key-1"
    m_vm = VerificationMethod(id=m_vm_id, type="Ed25519VerificationKey2020", controller=issuer,
    public_key_multibase=f"eth:{signer_addr}")
    # DID doc lists a different key
    other_acct = create_new_eth()
    other_priv = eth_key(other_acct)
    other_addr = eth_addr(other_acct)
    vm_id = f"{issuer}#key-2"
    vm = VerificationMethod(id=vm_id, type="Ed25519VerificationKey2020", controller="Masters", public_key_multibase=f"eth:{other_addr}")
    ## add both keys to DIDDOC
    diddoc = DemoDIDDocument(id=issuer, verification_method=[m_vm ,vm], authentication=[m_vm_id], service=[])

    message = claim.model_dump_json()
    signed = sign_claim(claim, other_priv, vm_id)
    sig = signed.proof.get("proofValue")
    

    # check each verification method in diddoc
    matched = False
    matched_vm = None
    for method in diddoc.verification_method:
        candidate_addr = _extract_address_from_vm(method)
        if verify(candidate_addr, sig, message):
            matched = True
            matched_vm = method.id
            break

    assert matched is True
    assert matched_vm == vm_id
