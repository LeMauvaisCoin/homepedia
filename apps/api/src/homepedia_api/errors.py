from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


class InvalidParameter(BaseModel):
    location: str = Field(description="Emplacement du paramètre fautif.", examples=["query.limit"])
    message: str = Field(examples=["Input should be less than or equal to 100"])


class Problem(BaseModel):
    """Erreur structurée, au format RFC 9457."""

    type: str = Field(default="about:blank", description="Identifiant du type d'erreur.")
    title: str = Field(examples=["Paramètres invalides"])
    status: int = Field(examples=[422])
    detail: str | None = None
    errors: list[InvalidParameter] = Field(default_factory=list)


def _problem_response(problem: Problem) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(), status_code=problem.status, media_type=PROBLEM_MEDIA_TYPE
    )


async def _validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = [
        InvalidParameter(
            location=".".join(str(part) for part in error["loc"]), message=error["msg"]
        )
        for error in exc.errors()
    ]
    return _problem_response(Problem(title="Paramètres invalides", status=422, errors=errors))


async def _http_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        raise exc
    return _problem_response(Problem(title=exc.detail, status=exc.status_code))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(HTTPException, _http_handler)
