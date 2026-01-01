import pytest
import requests

from middleware import register, store, resolve, retrieve, MiddlewareError
from shared_model import (
    DIDRegistryRegisterResponse,
    IPFSStoreResponse,
    IPFSRetrieveResponse,
)


class DummyResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if not 200 <= self.status_code < 300:
            raise requests.HTTPError(f"Status {self.status_code}")

    def json(self):
        return self._data


def test_register_success(monkeypatch):
    expected = {
        "status": "success",
        "did": "did:verity:demo:1",
        "doc_cid": "cid123",
        "timestamp": "2025-01-01T00:00:00"
    }

    def fake_post(url, data, headers, timeout):
        return DummyResponse(expected)

    monkeypatch.setattr("middleware.requests.post", fake_post)

    resp = register("did:verity:demo:1", "cid123")
    assert isinstance(resp, DIDRegistryRegisterResponse)
    assert resp.did == "did:verity:demo:1"


def test_store_and_retrieve_success(monkeypatch):
    store_resp = {"cid": "cid-xyz", "size_bytes": 123}
    retrieve_resp = {
        "cid": "cid-xyz",
        "document": {"foo": "bar"},
        "retrieved_at": "2025-01-01T00:00:00",
        "exists": True,
    }

    def fake_post(url, data, headers, timeout):
        return DummyResponse(store_resp)

    def fake_get(url, timeout):
        return DummyResponse(retrieve_resp)

    monkeypatch.setattr("middleware.requests.post", fake_post)
    monkeypatch.setattr("middleware.requests.get", fake_get)

    s = store({"foo": "bar"})
    assert isinstance(s, IPFSStoreResponse)
    assert s.cid == "cid-xyz"

    r = retrieve("cid-xyz")
    assert isinstance(r, IPFSRetrieveResponse)
    assert r.document["foo"] == "bar"


def test_resolve_failure_raises(monkeypatch):
    def fake_get(url, timeout):
        raise requests.RequestException("network")

    monkeypatch.setattr("middleware.requests.get", fake_get)

    with pytest.raises(MiddlewareError):
        resolve("did:not:found")
