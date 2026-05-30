from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tam.config import get_settings, validate_web_settings
from web.dependencies import get_db, init_services, shutdown_services
from web.routes.accounts import auth_accounts_router, router as auth_router
from web.routes.chats import router as chats_router
from web.routes.platform import router as platform_router
from web.routes.proxies import router as proxies_router
from web.routes.registration import router as registration_router

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_web_settings(settings)
    init_services(settings)
    database = get_db()
    await database.init_db()
    app.state.db = database
    yield
    await shutdown_services()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Telegram Account Manager", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.web_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth_router)
    app.include_router(auth_accounts_router)
    app.include_router(proxies_router)
    app.include_router(registration_router)
    app.include_router(chats_router)
    app.include_router(platform_router)

    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(FRONTEND_DIST / "index.html")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API endpoint not found")
            file_path = FRONTEND_DIST / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
