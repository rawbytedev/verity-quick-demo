
from pydantic import BaseModel


## those are model used to make requests
## Requests
class FileRequest(BaseModel): ## request a file from server
    ifps_hash:str
class FileUpload(BaseModel): ## upload to server
    checksum:str
    data:bytes
    name:str

## Responses
class FileUploadResponse(BaseModel): 
    status: int
    error:str
    checksum:str
    ifps_hash:str

class FileResponse(BaseModel):
    status:int
    error:str
    data:bytes

## Custom models used to Parse DIDDOC