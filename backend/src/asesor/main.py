from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from asesor.api.errors import register_error_handlers
from asesor.api.routers import health
from asesor.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="Asesor automotriz virtual",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-User-Id", "Authorization", "X-Debug-Fault"],
    )

    register_error_handlers(app)
    app.include_router(health.router)

    return app
