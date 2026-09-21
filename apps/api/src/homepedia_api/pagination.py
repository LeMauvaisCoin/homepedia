from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: Annotated[int, Query(ge=1, le=100)] = 20
    offset: Annotated[int, Query(ge=0)] = 0


PaginationDep = Annotated[Pagination, Depends()]
