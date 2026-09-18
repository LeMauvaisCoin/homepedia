import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from homepedia_api.db import create_database_engine
from homepedia_api.errors import PROBLEM_RESPONSE, register_error_handlers
from homepedia_api.routes import health, territories
from homepedia_api.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_database_engine(str(settings.database_url.get_secret_value()))
    app.state.engine = engine
    try:
        if settings.environment == "local":
            try:
                async with asyncio.timeout(3), engine.connect():
                    pass
            except (OperationalError, TimeoutError):
                raise RuntimeError(
                    "Impossible de se connecter à PostgreSQL : l'API ne peut pas démarrer. "
                    "Vérifiez que Docker fonctionne, puis lancez `bun run supabase:start` "
                    "depuis la racine du dépôt et relancez l'API. "
                    "Si vous utilisez une autre base, vérifiez DATABASE_URL dans apps/api/.env."
                ) from None
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Construit l'application sans lire la configuration : l'export OpenAPI reste hors ligne."""
    app = FastAPI(
        title="Homepedia API",
        version="0.1.0",
        description="Exploration immobilière territoriale.",
        lifespan=_lifespan,
        responses={500: PROBLEM_RESPONSE},
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
