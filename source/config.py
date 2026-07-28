from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agents:agents@localhost:5432/agents"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000
