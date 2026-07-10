import os
from abc import ABC
from typing import Final


class EnvKeys(ABC):
    """Secure environment configuration with validation"""

    @staticmethod
    def _get_required(key: str) -> str:
        val = os.getenv(key)
        if not val:
            raise ValueError(f"Missing required environment variable: {key}")
        return val

    @staticmethod
    def _get_optional(key: str, default: str = "") -> str:
        return os.getenv(key, default)

    # Telegram
    TOKEN: Final = _get_required('TOKEN')
    OWNER_ID: Final = int(_get_required('OWNER_ID'))

    # Database
    POSTGRES_DB: Final = _get_required("POSTGRES_DB")
    POSTGRES_USER: Final = _get_required("POSTGRES_USER")
    POSTGRES_PASSWORD: Final = _get_required("POSTGRES_PASSWORD")
    DB_PORT: Final = int(_get_optional("DB_PORT", "5432"))
    # This fork uses a synchronous SQLAlchemy engine (psycopg2). Do NOT default to
    # asyncpg here — it is incompatible with the sync engine in database/main.py.
    DB_DRIVER: Final = _get_optional("DB_DRIVER", "postgresql+psycopg2")

    # Redis
    REDIS_HOST: Final = _get_optional("REDIS_HOST", "localhost")
    REDIS_PORT: Final = int(_get_optional("REDIS_PORT", "6379"))
    REDIS_DB: Final = int(_get_optional("REDIS_DB", "0"))
    REDIS_PASSWORD: Final = _get_optional("REDIS_PASSWORD", "")

    # Payments
    PAY_CURRENCY: Final = _get_optional("PAY_CURRENCY", "RUB")
    MIN_AMOUNT: Final = int(_get_optional("MIN_AMOUNT", "20"))
    MAX_AMOUNT: Final = int(_get_optional("MAX_AMOUNT", "10000"))

    # Links / UI
    CHANNEL_URL: Final = _get_optional("CHANNEL_URL", "")
    CHANNEL_ID: Final = _get_optional("CHANNEL_ID", "")
    HELPER_ID: Final = _get_optional("HELPER_ID", "")
    RULES: Final = _get_optional("RULES", "")

    # Locale & logs
    BOT_LOCALE: Final = _get_optional("BOT_LOCALE", "ru")
    BOT_LOGFILE: Final = _get_optional("BOT_LOGFILE", "logs/bot.log")
    BOT_AUDITFILE: Final = _get_optional("BOT_AUDITFILE", "logs/audit.log")
    LOG_TO_STDOUT: Final = _get_optional("LOG_TO_STDOUT", "1")
    LOG_TO_FILE: Final = _get_optional("LOG_TO_FILE", "1")
    DEBUG: Final = _get_optional("DEBUG", "0")

    # Web admin panel
    MONITORING_HOST: Final = _get_optional("MONITORING_HOST", "localhost")
    MONITORING_PORT: Final = int(_get_optional("MONITORING_PORT", "9090"))

    # Security: stable secret for CSRF/replay token signing. Falls back to a random
    # per-process key when unset (tokens then don't survive restarts).
    SECRET_KEY: Final = _get_optional("SECRET_KEY", "")

    # Database (for manual deploy)
    DATABASE_URL: Final = "postgresql+psycopg2://user:password@localhost:5432/db_name"  # (setup if you deploy manually)
