import pytest
import requests
from middleware import MiddlewareError, health, register, resolve, retrieve, store
from shared_model import DIDRegistryRegisterResponse, IPFSRetrieveResponse, IPFSStoreResponse

def test_register_success():
    if _is_alive() == False:
        pytest.skip(reason="Server needs to be online")

    resp = register("did:verity:demo:1", "cid123")
    assert isinstance(resp, DIDRegistryRegisterResponse)
    assert resp.did == "did:verity:demo:1"


def test_store_and_retrieve_success():
    if _is_alive() == False:
        pytest.skip(reason="Server needs to be online")
    cid = "cid_426fc04f04bf8fdb5831dc37bbb6dcf70f63a37e05a68c6ea5f63e85ae579376"

    s = store({"foo": "bar"})
    assert isinstance(s, IPFSStoreResponse)
    assert s.cid == cid

    r = retrieve(cid)
    assert isinstance(r, IPFSRetrieveResponse)
    assert r.document["foo"] == "bar"


def test_resolve_failure_raises():
    if _is_alive() == True:
        pytest.skip(reason="Server needs to be down or unreachable")
    with pytest.raises(MiddlewareError):
        resolve("did:not:found")

def _is_alive():
    try:
        if health():
            return True
        return False
    except Exception:
        return False