from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import RowMapping, Select, func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from homepedia_api.db import postgis
from homepedia_api.pagination import Pagination
from homepedia_api.tables import t_territories as territories

TerritoryLevel = Literal["commune", "departement", "region"]


@dataclass(frozen=True, slots=True)
class TerritoryFilters:
    level: TerritoryLevel | None = None
    name_contains: str | None = None


def territory_selection(filters: TerritoryFilters) -> Select:
    """Filtered selection, unordered and unpaginated: page, total and exports derive from it."""
    selection = select(
        territories.c.code,
        territories.c.level,
        territories.c.name,
        territories.c.department_code,
        territories.c.region_code,
        territories.c.population,
        postgis.st_x(territories.c.centroid).label("longitude"),
        postgis.st_y(territories.c.centroid).label("latitude"),
    )
    if filters.level is not None:
        selection = selection.where(territories.c.level == filters.level)
    if filters.name_contains is not None:
        selection = selection.where(
            territories.c.name.icontains(filters.name_contains, autoescape=True)
        )
    return selection


async def list_territories(
    connection: AsyncConnection, filters: TerritoryFilters, pagination: Pagination
) -> tuple[Sequence[RowMapping], int]:
    selection = territory_selection(filters)
    page = (
        selection.order_by(territories.c.name, territories.c.code)
        .limit(pagination.limit)
        .offset(pagination.offset)
    )
    total = select(func.count()).select_from(selection.subquery())
    rows = (await connection.execute(page)).mappings().all()
    return rows, (await connection.execute(total)).scalar_one()
