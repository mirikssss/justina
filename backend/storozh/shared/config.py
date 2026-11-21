"""Настройки всего приложения. Читаются из окружения и из .env (корень репо, затем backend/)."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
REPO_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_DIR / ".env", BASE_DIR / ".env"), extra="ignore")

    env: str = "dev"  # dev | demo
    docs_enabled: bool = True  # T8: /docs, /redoc, /openapi.json; в prod-оверлее DOCS_ENABLED=false
    rate_limit_enabled: bool = True  # T8: лимиты на вход и подтверждение (shared/ratelimit.py)
    log_json: bool = True  # False — читаемые текстовые логи при локальной отладке
    database_url: str = "postgresql://storozh:storozh@localhost:5433/storozh"

    # --- безопасность (shared/crypto, внутренние эндпоинты) ---
    master_key: str = ""  # base64, 32 байта: конвертное шифрование AES-256-GCM
    pinfl_hmac_key: str = ""  # отдельный ключ для поиска ПИНФЛ по HMAC
    ingest_hmac_key: str = ""  # подпись X-Signature у POST /internal/ingest/snapshots
    remote_ingest_hmac_key: str = ""  # ключ подписи удалённого сервера для `documents sync` (INGEST_HMAC_KEY сервера)
    callback_hmac_key: str = ""  # подпись callback_data в Telegram

    # --- каналы ---
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    public_web_url: str = "http://localhost:3000"
    api_internal_url: str = "http://localhost:8000"  # куда сборщик шлёт снимки
    mygov_base_url: str = "https://my.gov.uz"  # для разработки: http://localhost:8765 (макет, documents mockportal)
    birdarcha_base_url: str = "https://new.birdarcha.uz"
    soliq_base_url: str = "https://my.soliq.uz"
    browser_profiles_dir: Path = BASE_DIR / "data" / "browser_profiles"  # постоянный профиль Chromium на гражданина (см. adapters/browser.py)
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
