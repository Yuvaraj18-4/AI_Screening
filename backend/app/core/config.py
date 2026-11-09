from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.url import normalize_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./shortlist.db"
    JWT_SECRET: str = "dev-insecure-secret-key-change-in-production-min32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:8000,http://127.0.0.1:5173,http://127.0.0.1:8000"
    )

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    MAX_UPLOAD_MB: int = 5
    WORKER_CONCURRENCY: int = 3
    PROMPT_VERSION: str = "v1"
    SEED_DEMO_DATA: bool = False

    @model_validator(mode="before")
    @classmethod
    def strip_empty_env_strings(cls, data: object) -> object:
        if isinstance(data, dict):
            # Strip empty strings so default values apply for unpopulated env vars
            return {k: v for k, v in data.items() if v != ""}
        return data

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.is_production:
            secret = (self.JWT_SECRET or "").strip()
            if not secret or len(secret) < 32 or "dev-insecure" in secret.lower() or "change-in-production" in secret.lower():
                raise ValueError(
                    "Production security error: JWT_SECRET must be set to a secure secret of at least 32 characters, and cannot contain default dev tokens."
                )
            self.COOKIE_SECURE = True
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        default_dev = "http://localhost:5173,http://localhost:8000,http://127.0.0.1:5173,http://127.0.0.1:8000"
        if self.is_production and default_dev == self.CORS_ORIGINS:
            # Default same-origin in production
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())


settings = Settings()
