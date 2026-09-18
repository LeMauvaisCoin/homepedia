from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from homepedia_api.db import ConnectionDep
from homepedia_api.errors import PROBLEM_RESPONSE
from homepedia_api.repositories import territories as repository

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


@router.get(
    "/territories",
    operation_id="listTerritories",
    summary="Lister les territoires",
    responses={422: PROBLEM_RESPONSE, 503: PROBLEM_RESPONSE},
)
async def list_territories(
    connection: ConnectionDep,
    level: Annotated[TerritoryLevel | None, Query(description="Niveau territorial.")] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=80, description="Recherche sur le nom.", examples=["lyon"]),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TerritoryPage:
    rows, total = await repository.list_territories(
        connection, repository.TerritoryFilters(level=level, q=q), limit=limit, offset=offset
    )
    return TerritoryPage(
        items=[Territory.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
