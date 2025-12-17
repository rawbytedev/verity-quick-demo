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
class FileRequest(BaseModel):
    ifps_hash:str
class FileResponse(BaseModel):
    status:int
    error:str
    data:str ## base64encoded content

class FileUpload(BaseModel):
    checksum:str
    data:str
    name:str

class FileUploadResponse(BaseModel):
    status: int
    error:str
    checksum:str
    ifps_hash:str

@app.get("/retrieve")
def retrieve_file(req: FileRequest):
    retrieve(req.ifps_hash)

@app.post("/add_doc")
def add_doc(req:FileUpload):
    if hexhash(req.data) == req.checksum:
        ifps_hash = store(req.name, req.data, req.checksum)
        return FileUploadResponse(checksum=req.checksum, ifps_hash=ifps_hash, status=200, error="")
    return FileUploadResponse(checksum=req.checksum, ifps_hash="", status=304, error="Invalid Request")

def store(name,data, checksum):
    ifps = gen_ifps_hash(name,checksum)
    with open(f"store/{ifps}", "xb") as f:
        f.write(b"name:"+name.encode()+b"\n")
        f.write(data.encode())
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
    return data
def gen_ifps_hash(name, checksum):
    return hexhash(f"{name}{checksum}")

