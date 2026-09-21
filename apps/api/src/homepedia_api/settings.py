from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, PostgresDsn, Secret
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL, make_url


def _split_origins(value: object) -> object:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


class Settings(BaseSettings):
    """API configuration, read from the environment, then from `apps/api/.env`."""

    # A validation error names the variable without ever echoing its value.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    environment: Literal["local", "test", "production"] = "local"
    # `Secret` masks the password in `repr(settings)`, hence in logs and tracebacks.
    database_url: Secret[PostgresDsn]
    cors_allowed_origins: Annotated[list[str], NoDecode, BeforeValidator(_split_origins)] = Field(
        default_factory=list
    )

    @property
    def sqlalchemy_url(self) -> URL:
        """Database URL on the psycopg 3 driver. `URL` masks the password when displayed."""
        return make_url(str(self.database_url.get_secret_value())).set(
            drivername="postgresql+psycopg"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
