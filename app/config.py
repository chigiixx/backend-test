"""
Централизованная конфигурация приложения.

Все настройки читаются из переменных окружения (.env), что соответствует
12-factor подходу: код не содержит секретов и хардкод-значений.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Developer Landing Backend"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: str = "*"  # список через запятую, либо "*"

    # --- Хранение данных (файловое) ---
    data_dir: str = "data"

    # --- AI ---
    ai_provider: str = "openai"  # openai | none
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 10.0

    # --- Email ---
    email_backend: str = "mock"  # mock | smtp
    owner_email: str = "owner@example.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@example.com"
    smtp_use_tls: bool = True

    # --- Rate limiting ---
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 600  # 10 минут

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings кешируются на процесс — .env читается один раз."""
    return Settings()
