from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import func, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

# Supabase installe PostGIS dans le schéma `extensions` : les fonctions spatiales
# sont qualifiées pour ne pas dépendre du `search_path` du rôle connecté.
postgis = func.extensions


def create_database_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        make_url(database_url).set(drivername="postgresql+psycopg"),
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        # Le pooler Supabase en mode transaction ne conserve pas les requêtes préparées.
        connect_args={"prepare_threshold": None},
    )


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    engine: AsyncEngine = request.app.state.engine
    async with engine.connect() as connection:
        yield connection


ConnectionDep = Annotated[AsyncConnection, Depends(get_connection)]
