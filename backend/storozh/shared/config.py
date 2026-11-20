"""Настройки всего приложения. Читаются из окружения и из .env (корень репо, затем backend/)."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
REPO_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_DIR / ".env", BASE_DIR / ".env"), extra="ignore")

    env: str = "dev"  # dev | demo
    database_url: str = "postgresql://storozh:storozh@localhost:5433/storozh"

    # --- безопасность (shared/crypto, внутренние эндпоинты) ---
    master_key: str = ""  # base64, 32 байта: конвертное шифрование AES-256-GCM
    pinfl_hmac_key: str = ""  # отдельный ключ для поиска ПИНФЛ по HMAC
    ingest_hmac_key: str = ""  # подпись X-Signature у POST /internal/ingest/snapshots
    callback_hmac_key: str = ""  # подпись callback_data в Telegram

    # --- каналы ---
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    public_web_url: str = "http://localhost:3000"
    api_internal_url: str = "http://localhost:8000"  # куда сборщик шлёт снимки
    collector_headless: bool = True  # False — видеть браузер сборщика при отладке

    # --- Помощник: RAG по lex.uz ---
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
