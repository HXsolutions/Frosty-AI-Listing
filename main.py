import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from routers import listings, export
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Frosty Connections — AI Listing System",
    version="2.0.0",
    # Disable public API docs in production
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# CORS — restrict to your domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# --- Optional API Key Auth ---
# Set ADMIN_API_KEY in .env to enable. Leave blank to disable (dev only).
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """
    If ADMIN_API_KEY is set in .env, all API requests must include
    the header: X-API-Key: <your_key>
    If not set, auth is disabled (useful for local dev).
    """
    if settings.admin_api_key:
        if not api_key or api_key != settings.admin_api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


app.include_router(listings.router, dependencies=[Depends(verify_api_key)])
app.include_router(export.router, dependencies=[Depends(verify_api_key)])

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_admin():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    # Never expose sensitive config in health endpoint
    return {
        "status": "ok",
        "system": "Frosty Connections AI Listing System",
        "version": "2.0.0",
        "env": settings.app_env,
    }
