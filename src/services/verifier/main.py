"""
Docstring for src.services.verifier.main
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from src.core.constants import (ADDHOST, VERIFYPORT)
from .verifier import setup_verification_app

app = FastAPI(
    title="Verity Protocol Demo",
    description="Cryptographic provenance for election integrity",
    version="1.0.0"
)

# Setup verification routes and UI
setup_verification_app(app)

# Mount static files
app.mount("/verifier_ui/static", StaticFiles(directory="verifier_ui/static"), name="static")
templates = Jinja2Templates(directory="verifier_ui/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render main HTML interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "verity-demo",
        "version": "1.0.0",
        "endpoints": ["/verify/post/claim", "/verify/claim/{id}"]
    }

def start():
    """
    Docstring for start
    """
    uvicorn.run(
        app,
        host=ADDHOST,
        port=VERIFYPORT
    )
