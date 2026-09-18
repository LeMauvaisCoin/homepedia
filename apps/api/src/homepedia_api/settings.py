from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, PostgresDsn, Secret
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_origins(value: object) -> object:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


class Settings(BaseSettings):
    """Configuration de l'API, lue dans l'environnement puis dans `apps/api/.env`."""

    # Une erreur de validation nomme la variable sans jamais recopier sa valeur.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    environment: Literal["local", "test", "production"] = "local"
    # `Secret` masque le mot de passe dans `repr(settings)`, donc dans les logs et les tracebacks.
    database_url: Secret[PostgresDsn]
    cors_allowed_origins: Annotated[list[str], NoDecode, BeforeValidator(_split_origins)] = Field(
        default_factory=list
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
