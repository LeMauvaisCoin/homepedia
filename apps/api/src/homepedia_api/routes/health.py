from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from homepedia_api.db import ConnectionDep

router = APIRouter(tags=["santé"])


class Health(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/health", operation_id="getHealth", summary="Vérifier que l'API répond")
async def get_health() -> Health:
    return Health()


@router.get(
    "/health/ready",
    operation_id="getReadiness",
    summary="Vérifier que l'API atteint la base de données",
)
async def get_readiness(connection: ConnectionDep) -> Health:
    await connection.execute(select(1))
    return Health()
