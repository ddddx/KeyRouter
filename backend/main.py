import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
from database import init_db
from health_check import start_health_checker
from channel_manager import router as channel_router
from key_manager import router as key_router
from router import router as proxy_router
from admin_api import router as admin_router
from config import PORT, HOST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_health_checker()
    yield


app = FastAPI(title="KeyRouter", description="API Key Smart Routing Proxy", lifespan=lifespan)

# API routers — these must be registered before the catch-all static handler
app.include_router(channel_router)
app.include_router(key_router)
app.include_router(proxy_router)
app.include_router(admin_router)

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