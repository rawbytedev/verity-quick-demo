"""
The main interface to start the storage and regsitration service
"""
import json
import uvicorn
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from db_lmdb import DB, DBError
from utils import hexhash
from shared_model import (DIDRegistryRegisterRequest, DIDRegistryRegisterResponse
, DIDRegistryResolveResponse,
IPFSStoreRequest, IPFSStoreResponse, IPFSRetrieveResponse)

from config import HOST, PORT
app = FastAPI()
db = DB()

"""
Smart Contract(mock) did -> diddoc registration
"""
@app.post("/register", response_model=DIDRegistryRegisterResponse)
def register(req: DIDRegistryRegisterRequest):
    """
    Registers a did to a CID (maps did to CID)

    :param req: Description
    :type req: DIDRegistryRegisterRequest
    """
    try:
        db.put(req.did, req.doc_cid)
        return DIDRegistryRegisterResponse(status="success", did=req.did, doc_cid=req.doc_cid)
    except DBError:
        return DIDRegistryRegisterResponse(status="error", did=req.did, doc_cid=req.doc_cid)

@app.get("/resolve/{did}", response_model=DIDRegistryResolveResponse)
def resolve(did:str):
    """
    Resolves a did to it's CID

    :param did: Description
    :type did: str
    """
    try:
        data = db.get(did)
        return DIDRegistryResolveResponse(did=did, doc_cid=data, status="success")
    except DBError:
        return DIDRegistryResolveResponse(did=did,status="error")

@app.get("/health")
def health():
    """
    Returns the current status of server
    """
    return {"status":200}
#
### IFPS server Implementation
#
@app.post("/store", response_model=IPFSStoreResponse)
def store_cid(req:IPFSStoreRequest):
    """
    Stores a document and returns the result

    :param req: Description
    :type req: IPFSStoreRequest
    """
    jsondoc = jsonable_encoder(req.document)
    if req.document:
        doc = json.dumps(jsondoc)
        size = len(doc)
        checksum = hexhash(doc)
        cid = _gen_ifps_hash(checksum)
        with open(cid, "w", encoding="utf-8") as f:
            f.write(doc)
        return IPFSStoreResponse(cid=cid, size_bytes=size)
    return IPFSStoreResponse(cid="0x0", size_bytes=0)

@app.get("/retrieve/{cid}", response_model=IPFSRetrieveResponse)
def retrieve_cid(cid:str):
    """
    Retrieve a document using its cid

    :param cid: Description
    :type cid: str
    """
    try:
        with open(cid, "r", encoding="utf-8") as f:
            di = json.loads(f.read())
            return IPFSRetrieveResponse(cid=cid, document=di, exists=True)
    except FileNotFoundError:
        return IPFSRetrieveResponse(cid=cid,document={"0":""}, exists=False)

def _gen_ifps_hash(checksum):
    return "cid_"+checksum


if __name__ == "__main__":
    #a = DEMO.model_dump()
    #store_cid(IPFSStoreRequest(document=a))
    uvicorn.run(app, port=PORT, host=HOST)
