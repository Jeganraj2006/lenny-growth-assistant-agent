import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "The Lenny Growth Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # LLM & Embedding Settings
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_LLM_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text:latest"
    EMBEDDING_DIM: int = 768  # Verified 768 dimensions for nomic-embed-text:latest

    # RAG & Transcript Ingestion Settings
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "transcripts")
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_THRESHOLD: float = 0.55

    # Database Settings (Explicit 127.0.0.1:5433 to target Docker container)
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "lenny_growth_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/lenny_growth_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
