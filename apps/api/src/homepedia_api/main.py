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
    engine = create_database_engine(settings.sqlalchemy_url)
    app.state.engine = engine
    try:
        if settings.environment == "local":
            try:
                async with asyncio.timeout(3), engine.connect():
                    pass
            except (OperationalError, TimeoutError):
                raise RuntimeError(
                    "Cannot connect to PostgreSQL: the API cannot start. "
                    "Check that Docker is running, then run `bun run supabase:start` "
                    "from the repository root and restart the API. "
                    "If you use another database, check DATABASE_URL in apps/api/.env."
                ) from None
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Build the app without reading the configuration: the OpenAPI export stays offline."""
    app = FastAPI(
        title="Homepedia API",
        version="0.1.0",
        description="Territorial real estate exploration.",
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
