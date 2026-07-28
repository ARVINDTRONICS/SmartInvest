import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "SmartInvest AI Engine"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartinvest"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI (OpenAI / Gemini / Groq / OpenRouter)
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None
    LLM_MODEL_NAME: str = "gpt-4o-mini"


    # Telegram
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    TELEGRAM_ALERT_SYMBOLS: str = "NIFTY50,DOW"

    # API Security
    API_KEY: str | None = None




settings = Settings()

