from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import RowMapping, Select, func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from homepedia_api.db import postgis
from homepedia_api.tables import t_territories as territories


@dataclass(frozen=True, slots=True)
class TerritoryFilters:
    level: str | None = None
    q: str | None = None


def territory_selection(filters: TerritoryFilters) -> Select:
    """Sélection filtrée, sans tri ni pagination : page, total et exports en dérivent."""
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
    if filters.q is not None:
        selection = selection.where(territories.c.name.icontains(filters.q, autoescape=True))
    return selection


async def list_territories(
    connection: AsyncConnection, filters: TerritoryFilters, *, limit: int, offset: int
) -> tuple[Sequence[RowMapping], int]:
    selection = territory_selection(filters)
    page = selection.order_by(territories.c.name, territories.c.code).limit(limit).offset(offset)
    total = select(func.count()).select_from(selection.subquery())
    rows = (await connection.execute(page)).mappings().all()
    return rows, (await connection.execute(total)).scalar_one()
