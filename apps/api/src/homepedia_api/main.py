from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from homepedia_api.db import create_pool
from homepedia_api.errors import register_error_handlers
from homepedia_api.routes import health, territories
from homepedia_api.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    pool = create_pool(str(settings.database_url))
    await pool.open()
    app.state.pool = pool
    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    """Construit l'application sans lire la configuration : l'export OpenAPI reste hors ligne."""
    app = FastAPI(
        title="Homepedia API",
        version="0.1.0",
        description="Exploration immobilière territoriale.",
        lifespan=_lifespan,
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(territories.router)
    return app


def create_configured_app() -> FastAPI:
    app = create_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    return app
