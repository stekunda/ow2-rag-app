from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OW2 Hero Intelligence"
    openai_api_key: str | None = None
    langchain_api_key: str | None = None
    langchain_project: str = "ow2-rag"
    langchain_tracing_v2: bool = True
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "ow2_hero_intel"
    vector_store: str = "chroma"
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
