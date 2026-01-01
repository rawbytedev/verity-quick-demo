"""
Bridge communication between the frontend and the backend(IFPS+DIDregistry)
"""
import logging
import time
from typing import Optional, Union
from pydantic import BaseModel
import requests
from config import HOST, PORT

from shared_model import (
    DIDRegistryRegisterRequest,
    DIDRegistryRegisterResponse,
    DIDRegistryResolveResponse,
    IPFSStoreRequest,
    IPFSStoreResponse,
    IPFSRetrieveResponse,
)

logger = logging.getLogger(__name__)

# endpoints are appended to host:port
_ENDPOINTS = {
    "reg": "/register",
    "res": "/resolve/",
    "str": "/store",
    "ret": "/retrieve/",
    "heal":"/health"
}

# sensible defaults
DEFAULT_TIMEOUT = 5.0
DEFAULT_RETRIES = 2


class MiddlewareError(Exception):
    """Raised when middleware HTTP operations fail."""


def _finalize_url(key: str, val: Optional[str] = None) -> str:
    try:
        part = _ENDPOINTS[key]
    except KeyError as exc:
        raise ValueError(f"Unknown endpoint key: {key}") from exc

    # HOST may include scheme, e.g. http://127.0.0.1
    base = f"{HOST}:{PORT}"
    url = f"{base}{part}"
    if val:
        url = url + str(val)
    return url


def _post_json(url: str, payload: dict, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES):
    headers = {"Content-Type": "application/json"}
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.debug("POST %s attempt %d", url, attempt)
            resp = requests.post(url, data=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            last_exc = e
            logger.warning("Request failed (attempt %d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(0.2 * attempt)
    raise MiddlewareError(f"POST {url} failed after {retries} attempts: {last_exc}")


def _get_json(url: str, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.debug("GET %s attempt %d", url, attempt)
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            last_exc = e
            logger.warning("Request failed (attempt %d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(0.2 * attempt)
    raise MiddlewareError(f"GET {url} failed after {retries} attempts: {last_exc}")


def register(did: str, cid: str, signature: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT) -> DIDRegistryRegisterResponse:
    """Register a DID -> CID mapping on the registry service.

    Returns a `DIDRegistryRegisterResponse` on success or raises `MiddlewareError` on failure.
    """
    url = _finalize_url("reg")
    data = DIDRegistryRegisterRequest(did=did, doc_cid=cid, signature=signature).model_dump_json()
    j = _post_json(url, data, timeout=timeout)
    return DIDRegistryRegisterResponse.model_validate(j)


def resolve(did: str, timeout: float = DEFAULT_TIMEOUT) -> DIDRegistryResolveResponse:
    """Resolve a DID to its current CID and metadata.

    Returns a `DIDRegistryResolveResponse`.
    """
    url = _finalize_url("res", val=did)
    j = _get_json(url, timeout=timeout)
    return DIDRegistryResolveResponse.model_validate(j)


def store(model: Union[BaseModel, dict], timeout: float = DEFAULT_TIMEOUT) -> IPFSStoreResponse:
    """Store a document (DID Document or claim) on the IPFS mock gateway.

    `model` may be a pydantic `BaseModel` or a plain dict. Returns `IPFSStoreResponse`.
    """
    url = _finalize_url("str")
    if isinstance(model, BaseModel):
        json_model = model.model_dump()
    else:
        json_model = model

    payload = IPFSStoreRequest(document=json_model).model_dump_json()
    j = _post_json(url, payload, timeout=timeout)
    return IPFSStoreResponse.model_validate(j)


def retrieve(cid: str, timeout: float = DEFAULT_TIMEOUT) -> IPFSRetrieveResponse:
    """Retrieve a stored document by CID from the IPFS mock gateway."""
    url = _finalize_url("ret", val=cid)
    j = _get_json(url, timeout=timeout)
    return IPFSRetrieveResponse.model_validate(j)


def health(timeout: float = DEFAULT_TIMEOUT):
    """Checks the Health of backend"""
    url = _finalize_url("heal")
    j = _get_json(url, timeout=timeout)
    if j["status"] == 200:
        return True
    return False

if __name__ == "__main__":
    # small demo when run directly (keeps previous CLI-style prints for convenience)
    try:
        DIDresp = register("did:dz", cid="dffe")
        print(DIDresp.model_dump())
    except Exception as e:
        print("register failed:", e)
