from typing import Annotated

from fastapi import Depends, Request
from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

type Connection = AsyncConnection[DictRow]
type Pool = AsyncConnectionPool[Connection]


def create_pool(database_url: str) -> Pool:
    return AsyncConnectionPool(
        database_url,
        connection_class=AsyncConnection[DictRow],
        kwargs={"row_factory": dict_row},
        min_size=1,
        max_size=5,
        open=False,
    )


def get_pool(request: Request) -> Pool:
    return request.app.state.pool


PoolDep = Annotated[Pool, Depends(get_pool)]
