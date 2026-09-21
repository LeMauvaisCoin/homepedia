from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from homepedia_api.db import ConnectionDep
from homepedia_api.errors import PROBLEM_RESPONSE

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/health", operation_id="getHealth", summary="Check that the API responds")
async def get_health() -> Health:
    return Health()


@router.get(
    "/health/ready",
    operation_id="getReadiness",
    summary="Check that the API reaches the database",
    responses={503: PROBLEM_RESPONSE},
)
async def get_readiness(connection: ConnectionDep) -> Health:
    await connection.execute(select(1))
    return Health()
