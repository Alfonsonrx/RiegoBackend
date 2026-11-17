from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",  # the project's, whatever the cwd
        env_ignore_empty=True,      # `DB_PW=` copied from .env.example counts as missing, not as ""
        extra="ignore",
        hide_input_in_errors=True,  # a missing setting is named; no value is ever printed
    )

    # Database (002 FR-3): no defaults for the credentials (profile rule 3)
    DB_USER: str
    DB_PW: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "db_riego"

    # Tokens (001)
    SECRET_KEY: str  # no default: refuse to sign tokens with a guessable key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
