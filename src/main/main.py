import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from verifier import setup_verification_app

app = FastAPI(
    title="Verity Protocol Demo",
    description="Cryptographic provenance for election integrity",
    version="1.0.0"
)

# Setup verification routes and UI
setup_verification_app(app)

# Mount static files if needed
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Redirect to verification interface."""
    return RedirectResponse(url="/verify")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "verity-demo",
        "version": "1.0.0",
        "endpoints": ["/verify", "/verify/cid/{cid}", "/verify/claim/{id}"]
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Accessible from other devices
        port=8000,
    )

