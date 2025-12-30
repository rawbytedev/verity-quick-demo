import json
from typing import Dict
from fastapi.encoders import jsonable_encoder
import uvicorn
from db_lmdb import DB, DBError
from fastapi import FastAPI
from shared_model import DIDRegistryRegisterRequest, DIDRegistryRegisterResponse, DIDRegistryResolveResponse, Demo, IPFSStoreRequest, IPFSStoreResponse, IPFSRetrieveResponse
from utils import *
from config import *
app = FastAPI()
db = DB()

"""
Smart Contract(mock) did -> diddoc registration
"""
@app.post("/register", response_model=DIDRegistryRegisterResponse)
def register(req: DIDRegistryRegisterRequest):
    try:
        db.put(req.did, req.doc_cid)
        return DIDRegistryRegisterResponse(status="success", did=req.did, doc_cid=req.doc_cid)
    except DBError:
        return DIDRegistryRegisterResponse(status="error", did=req.did, doc_cid=req.doc_cid)
    
@app.get("/resolve/{did}", response_model=DIDRegistryResolveResponse)
def resolve(did:str):
    try:
        data = db.get(did)
        return DIDRegistryResolveResponse(did=did, doc_cid=data, status="success")
    except DBError:
        return DIDRegistryResolveResponse(did=did,status="error")

@app.get("/health")
def health():
    return {"status":200}    
"""
IFPS server Implementation
"""
@app.post("/store", response_model=IPFSStoreResponse)
def store_cid(req:IPFSStoreRequest):
    jsondoc = jsonable_encoder(req.document)
    if req.document:
        doc = json.dumps(jsondoc)
        size = len(doc)
        checksum = hexhash(doc)
        cid = gen_ifps_hash(checksum)
        with open(cid, "w") as f:
            f.write(doc)
        return IPFSStoreResponse(cid=cid, size_bytes=size)
    return IPFSStoreResponse(cid="0x0", size_bytes=0)

@app.get("/retrieve/{cid}", response_model=IPFSRetrieveResponse)
def retrieve_cid(cid:str):
    try:
        with open(cid, "r") as f:
            di = json.loads(f.read())
            return IPFSRetrieveResponse(cid=cid, document=di, exists=True)
    except FileNotFoundError:
        return IPFSRetrieveResponse(cid=cid,document={"0":""}, exists=False)

def gen_ifps_hash(checksum):
    return "cid_"+checksum

def verify_signature(sig):
    pass

if __name__ == "__main__":
    #a = Demo.model_dump()
    #store_cid(IPFSStoreRequest(document=a))
    uvicorn.run(app, port=PORT, host=HOST)