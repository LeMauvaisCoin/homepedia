from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import URL, func
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

# Supabase installs PostGIS in the `extensions` schema: spatial functions are
# qualified so they do not depend on the connected role's `search_path`.
postgis = func.extensions


def create_database_engine(url: URL) -> AsyncEngine:
    return create_async_engine(
        url,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
        # The Supabase pooler in transaction mode does not keep prepared statements.
        connect_args={"prepare_threshold": None},
    )


async def get_connection(request: Request) -> AsyncIterator[AsyncConnection]:
    engine: AsyncEngine = request.app.state.engine
    async with engine.connect() as connection:
        yield connection


ConnectionDep = Annotated[AsyncConnection, Depends(get_connection)]
