import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(__name__)


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


PROBLEM_RESPONSE: dict[str, Any] = {"model": Problem, "content": {PROBLEM_MEDIA_TYPE: {}}}


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


async def _database_unavailable_handler(_request: Request, exc: Exception) -> JSONResponse:
    # Le message du pilote nomme l'hôte et le port : il va dans les logs, pas dans la réponse.
    logger.error("Base de données injoignable : %s", exc)
    return _problem_response(
        Problem(
            title="Service indisponible",
            status=503,
            detail="La base de données est injoignable. Réessayez dans quelques instants.",
        )
    )


class UnhandledErrorMiddleware:
    """Répond 500 au format du contrat quand une exception n'a aucun gestionnaire.

    Un gestionnaire `Exception` classique répondrait depuis `ServerErrorMiddleware`, à
    l'extérieur du middleware CORS : le navigateur masquerait la réponse au frontend.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_and_track(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_and_track)
        except Exception:
            if response_started:
                raise
            logger.exception("Erreur inattendue sur %s %s", scope["method"], scope["path"])
            response = _problem_response(Problem(title="Erreur interne", status=500))
            await response(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(HTTPException, _http_handler)
    app.add_exception_handler(OperationalError, _database_unavailable_handler)
    app.add_exception_handler(PoolTimeoutError, _database_unavailable_handler)
    app.add_middleware(UnhandledErrorMiddleware)
