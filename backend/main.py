import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from database import init_db
from health_check import start_health_checker
from log_cleanup import start_log_cleanup
from channel_manager import router as channel_router
from key_manager import router as key_router
from router import router as proxy_router
from admin_api import router as admin_router
from api_key_manager import router as api_key_router
from auth import router as auth_router
from config import PORT, HOST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# Paths that require JWT auth (admin endpoints)
AUTH_REQUIRED_PREFIXES = ("/api/channels/", "/api/keys/", "/api/admin/", "/api/auth/change-password", "/api/auth/me", "/api/api-keys/")
# Paths that do NOT require auth
AUTH_EXEMPT_PATHS = ("/api/auth/login", "/api/auth/status", "/api/auth/setup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_health_checker()
    await start_log_cleanup()
    yield


app = FastAPI(title="KeyRouter", description="API Key Smart Routing Proxy", lifespan=lifespan)


# JWT auth middleware - check auth for protected admin API paths
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Proxy endpoints (/v1/) - auth is handled inside router (external ApiKey validation)
    if path.startswith("/v1/"):
        return await call_next(request)

    # Auth login/status/setup - no auth needed
    for exempt in AUTH_EXEMPT_PATHS:
        if path == exempt:
            return await call_next(request)

    # Static files / root - no auth needed
    if path == "/" or path.startswith("/assets") or path.startswith("/favicon") or path.startswith("/icons"):
        return await call_next(request)

    # Check if path requires admin JWT auth
    needs_auth = False
    for prefix in AUTH_REQUIRED_PREFIXES:
        if path.startswith(prefix):
            needs_auth = True
            break

    if not needs_auth:
        # Other paths (SPA fallback, etc) - no auth
        return await call_next(request)

    # Verify JWT token for admin endpoints
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    token = auth_header[7:]
    try:
        from jose import jwt, JWTError
        from config import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
    except JWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    # Token valid - proceed
    response = await call_next(request)
    return response


# API routers — these must be registered before the catch-all static handler
app.include_router(auth_router)
app.include_router(channel_router)
app.include_router(key_router)
app.include_router(proxy_router)
app.include_router(admin_router)
app.include_router(api_key_router)

# Serve frontend static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        return FileResponse(index_path)

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = os.path.join(static_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # SPA fallback
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        raise HTTPException(404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)