from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    omdb_api_key: str = ""
    tmdb_api_key: str = ""
    rawg_api_key: str = ""
    rapidapi_key: str = ""

    api_keys: list[str] = []          # keys allowed to call write/admin endpoints
    cache_ttl_seconds: int = 300
    rate_limit_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()