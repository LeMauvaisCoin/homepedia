from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from homepedia_api.db import PoolDep
from homepedia_api.errors import PROBLEM_MEDIA_TYPE, Problem

router = APIRouter(prefix="/v1", tags=["territoires"])

TerritoryLevel = Literal["commune", "departement", "region"]


class Territory(BaseModel):
    code: str = Field(
        description="Code officiel géographique, conservé en chaîne (zéros initiaux).",
        examples=["01053"],
    )
    level: TerritoryLevel
    name: str = Field(examples=["Bourg-en-Bresse"])
    department_code: str | None = Field(examples=["01"])
    region_code: str | None = Field(examples=["84"])
    population: int | None = Field(description="Population municipale.", examples=[42372])
    longitude: float = Field(examples=[5.2469])
    latitude: float = Field(examples=[46.2027])


class TerritoryPage(BaseModel):
    items: list[Territory]
    total: int = Field(description="Nombre de territoires correspondant aux filtres.")
    limit: int
    offset: int


_LIST_SQL = """
select
  code,
  level,
  name,
  department_code,
  region_code,
  population,
  extensions.st_x(centroid) as longitude,
  extensions.st_y(centroid) as latitude
from public.territories
where (%(level)s::text is null or level = %(level)s)
  and (%(q)s::text is null or name ilike '%%' || %(q)s || '%%')
order by name, code
limit %(limit)s offset %(offset)s
"""

_COUNT_SQL = """
select count(*) as total
from public.territories
where (%(level)s::text is null or level = %(level)s)
  and (%(q)s::text is null or name ilike '%%' || %(q)s || '%%')
"""


@router.get(
    "/territories",
    operation_id="listTerritories",
    summary="Lister les territoires",
    responses={
        422: {"model": Problem, "content": {PROBLEM_MEDIA_TYPE: {}}},
    },
)
async def list_territories(
    pool: PoolDep,
    level: Annotated[TerritoryLevel | None, Query(description="Niveau territorial.")] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=80, description="Recherche sur le nom.", examples=["lyon"]),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TerritoryPage:
    params = {"level": level, "q": q, "limit": limit, "offset": offset}
    async with pool.connection() as connection:
        rows = await (await connection.execute(_LIST_SQL, params)).fetchall()
        count = await (await connection.execute(_COUNT_SQL, params)).fetchone()
    return TerritoryPage(
        items=[Territory.model_validate(row) for row in rows],
        total=count["total"] if count else 0,
        limit=limit,
        offset=offset,
    )
