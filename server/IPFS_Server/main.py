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

class FileUploadResponse(BaseModel):
    checksum:str
    ifps_hash:str

@app.get("/retrieve")
def retrieve_file(req: FileRequest):
    pass

@app.post("/add_doc")
def add_doc(req:FileUpload):
    pass

def store(name,data, checksum):
    ifps = gen_ifps_hash(name,checksum)
    with open(f"store/{ifps}", "w") as f:
        f.write(f"name:{name}\n")
        f.write(data)
def retrieve(ifps):
    try:
        with open(f"store/{ifps}", "r") as f:
            name = f.readline().removeprefix('name:').rstrip("\n")
            print(name)
            data = f.read()
            print(data)
    except Exception as e:
        print(e)
        return None
def gen_ifps_hash(name, checksum):
    return hexhash(f"{name}{checksum}")

