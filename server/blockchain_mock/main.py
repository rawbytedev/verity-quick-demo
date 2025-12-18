from base64 import b64encode
import base64
from pydantic import BaseModel
from db_lmdb import DB, DBError
import asyncio, json
import os
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from utils import hexhash

app = FastAPI()
db = DB()
class FileRequest(BaseModel):
    ifps_hash:str
class FileResponse(BaseModel):
    status:int
    error:str
    data:bytes

class FileUpload(BaseModel):
    checksum:str
    data:bytes
    name:str

class FileUploadResponse(BaseModel):
    status: int
    error:str
    checksum:str
    ifps_hash:str

## smart contract models
class LinkDID(BaseModel):
    address: str
    did_hash:bytes
@app.get("/retrieve")
def retrieve_file(req: FileRequest):
    retrieve(req.ifps_hash)

@app.post("/add_doc")
def add_doc(req:FileUpload):
    if hexhash(req.data) == req.checksum:
        ifps_hash = store(req.name, req.data, req.checksum)
        return FileUploadResponse(checksum=req.checksum, ifps_hash=ifps_hash, status=200, error="")
    return FileUploadResponse(checksum=req.checksum, ifps_hash="", status=304, error="Invalid Request")
@app.post("/block/link_did")
def didlink(req: LinkDID):
    pass

## adds key to database
def append(key:bytes, data:bytes):
    db.put(key, data)

def get_db(key:bytes):
    pass
def store(name,data, checksum):
    ifps = gen_ifps_hash(name,checksum)
    with open(f"store/{ifps}", "xb") as f:
        f.write(b"name:"+name.encode()+b"\n")
        f.write(data)
        return ifps
def retrieve(ifps):
    try:
        with open(f"store/{ifps}", "rb") as f:
            name = f.readline().removeprefix(b'name:').rstrip(b"\n")
            data = f.read()
            ## small check
            check = hexhash(data)
            if gen_ifps_hash(name.decode(), check) != ifps:
                return ""
    except Exception as e:
        print(e)
        return ""
    return FileResponse(status=200, error="", data=data)

def gen_ifps_hash(name, checksum):
    return hexhash(f"{name}{checksum}")

