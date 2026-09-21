from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from homepedia_api.db import ConnectionDep
from homepedia_api.errors import PROBLEM_RESPONSE
from homepedia_api.pagination import PaginationDep
from homepedia_api.repositories import territories as repository

router = APIRouter(prefix="/v1", tags=["territories"])


class Territory(BaseModel):
    code: str = Field(
        description="Official geographic code, kept as a string (leading zeros).",
        examples=["01053"],
    )
    level: repository.TerritoryLevel
    name: str = Field(examples=["Bourg-en-Bresse"])
    department_code: str | None = Field(examples=["01"])
    region_code: str | None = Field(examples=["84"])
    population: int | None = Field(description="Municipal population.", examples=[42372])
    longitude: float = Field(examples=[5.2469])
    latitude: float = Field(examples=[46.2027])


class TerritoryPage(BaseModel):
    items: list[Territory]
    total: int = Field(description="Number of territories matching the filters.")
    limit: int
    offset: int


@router.get(
    "/territories",
    operation_id="listTerritories",
    summary="List territories",
    responses={422: PROBLEM_RESPONSE, 503: PROBLEM_RESPONSE},
)
async def list_territories(
    connection: ConnectionDep,
    pagination: PaginationDep,
    level: Annotated[
        repository.TerritoryLevel | None, Query(description="Territorial level.")
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=80, description="Search on the name.", examples=["lyon"]),
    ] = None,
) -> TerritoryPage:
    rows, total = await repository.list_territories(
        connection, repository.TerritoryFilters(level=level, name_contains=q), pagination
    )
    return TerritoryPage(
        items=[Territory.model_validate(row) for row in rows],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
