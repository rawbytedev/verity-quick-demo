import sys
import types
from types import SimpleNamespace
import cli
from shared_model import DemoDIDDocument


class FakeIO:
    def __init__(self):
        self.outputs = []

    def input(self, prompt=""):
        raise RuntimeError("No interactive input in this test")

    def print(self, *args, **kwargs):
        self.outputs.append(" ".join(str(a) for a in args))


def test_sign_diddoc_attaches_proof(monkeypatch):
    # Prepare CLI with fake IO and a dummy session
    fake_io = FakeIO()
    app = cli.VerityDemoCLI(io=fake_io)

    # create a minimal account stub that satisfies Address/Keys access
    acct = SimpleNamespace(address="0xTESTADDR", key="0x01" * 32)
    session = cli.AccountSession.__new__(cli.AccountSession)
    # manually set expected attributes (bypass __init__ heavy logic)
    session.account = acct
    session.address = acct.address
    session.private_key = acct.key
    session.diddocs = []
    session.current_diddoc = None

    app.sessions[acct.address] = session
    app.current_session = session

    # attach a demo DID document (deep copy of the shared Demo instance)
    from shared_model import Demo
    diddoc = Demo.model_copy(deep=True)
    app.current_session.diddocs.append(diddoc)

    # monkeypatch sign() to a simple deterministic value
    def fake_sign(priv, msg):
        return "deadbeefsig"

    # monkeypatch the sign function that cli module uses
    monkeypatch.setattr(cli, "sign", fake_sign)

    # call sign_diddoc
    app.sign_diddoc(diddoc)

    # verify proof attached and uses expected keys
    assert hasattr(diddoc, "proof")
    assert isinstance(diddoc.proof, dict)
    assert "proofValue" in diddoc.proof
    assert diddoc.proof["signer"] == app.current_session.address


def test_main_headless_flow_calls_helpers(monkeypatch, capsys):
    # Prepare fake implementations and inject into cli module
    created = types.SimpleNamespace(claim_id="claim123")

    def fake_create_from_message(msg, issuer):
        return created

    def fake_sign_claim(claim, priv, vm):
        claim.proof = {"proofValue": "sig"}
        return claim

    def fake_store_claim(claim):
        return "cid-abc"

    monkeypatch.setattr(cli, "create_claim_from_message", fake_create_from_message)
    monkeypatch.setattr(cli, "sign_claim", fake_sign_claim)
    monkeypatch.setattr(cli, "store_claim", fake_store_claim)

    # set argv for headless run
    argv = ["prog", "--message", "hello", "--issuer", "did:ex:1", "--sign-priv", "0x01", "--verification-method", "did:ex:1#key-1", "--store", "--no-interactive"]
    monkeypatch.setattr(sys, "argv", argv)

    # call main (should not raise)
    cli.main()

    captured = capsys.readouterr()
    assert "Created claim id" in captured.out
    assert "Signed claim; proof created" in captured.out
    assert "Stored claim; cid=cid-abc" in captured.out
