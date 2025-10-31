from __future__ import annotations

from fastapi import FastAPI

from .api.v1.routes.health import router as health_router
from .api.v1.routes.generate import router as generate_router
from .api.v1.routes.jobs import router as jobs_router
from .api.v1.routes.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="OpenSchema Backend", version="0.1.0")
    app.include_router(health_router, prefix="/v1")
    app.include_router(auth_router, prefix="/v1")
    app.include_router(generate_router, prefix="/v1")
    app.include_router(jobs_router, prefix="/v1")
    return app


app = create_app()


