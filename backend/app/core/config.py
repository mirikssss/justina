import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = "postgresql://justina:justina@localhost:5433/justina"
    cache_dir: Path = BASE_DIR / "data" / "lexuz_cache"

    # BAAI/bge-m3 (1024, лучше) или intfloat/multilingual-e5-small (384, лёгкая, нужны префиксы)
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    embedding_batch: int = 32
    rerank_enabled: bool = False  # cross-encoder bge-reranker-v2-m3 (~2.3 ГБ)

    hf_token: str | None = None

    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-5-5"  # выбрана по eval/models.py: качество как у Opus 5.5 при 1/4 цены


settings = Settings()

if settings.hf_token:  # huggingface_hub читает токен из окружения, а не из .env
    os.environ.setdefault("HF_TOKEN", settings.hf_token)
