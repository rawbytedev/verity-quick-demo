from claim_utils import create_claim_from_message, create_claim_from_file, sign_claim
from claim_model import VerityClaim


def test_create_claim_from_message():
    claim = create_claim_from_message("hello world", "did:example:org1")
    assert isinstance(claim, VerityClaim)
    assert "hello world" in claim.credential_subject.get("text")
    assert claim.content_hash.startswith("sha256:")


def test_create_claim_from_file(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("file contents")
    claim = create_claim_from_file(str(p), "did:example:org1")
    assert claim.credential_subject["filename"] == "test.txt"
    assert claim.content_hash.startswith("sha256:")


def test_sign_claim():
    # use minimal claim
    claim = create_claim_from_message("sign me", "did:example:org1")
    # use a fake private key hex (signer is tested elsewhere). For unit test, just ensure proof is attached.
    fake_priv = "0x" + "1" * 64
    signed = sign_claim(claim, fake_priv, "did:example:org1#key-1")
    assert signed.proof is not None
    assert "proofValue" in signed.proof
