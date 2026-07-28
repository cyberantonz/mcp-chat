"""Application settings loaded from the environment."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration; every field is overridable via environment variables."""

    database_url: str = "postgresql+asyncpg://agents:agents@localhost:5432/agents"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000
