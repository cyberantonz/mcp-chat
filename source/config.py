from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: PostgresDsn
    database_pool_size: int
    database_pool_max_overflow: int
    host: str
    port: int
    log_level: str
    rate_limit_per_ip: int
    rate_limit_per_agent: int
