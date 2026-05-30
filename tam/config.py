import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

_INSECURE_DEFAULTS = frozenset({"admin", "change_me_to_random_32_chars_key"})


def _parse_admin_ids(raw: str | None) -> frozenset[int]:
    if not raw:
        return frozenset()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return frozenset(ids)


def _allow_insecure() -> bool:
    return os.getenv("ALLOW_INSECURE", "false").lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    bot_token: str | None
    api_id: int
    api_hash: str
    encryption_key: str
    database_url: str
    admin_ids: frozenset[int]
    web_host: str
    web_port: int
    web_secret: str
    web_password: str
    web_cors_origins: list[str]
    allow_insecure: bool


def get_settings() -> Settings:
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    encryption_key = os.getenv("ENCRYPTION_KEY")

    if not api_id:
        raise ValueError("API_ID не установлен в .env файле")
    if not api_hash:
        raise ValueError("API_HASH не установлен в .env файле")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY не установлен в .env файле")

    cors_raw = os.getenv("WEB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
    allow_insecure = _allow_insecure()

    web_password = os.getenv("WEB_PASSWORD", "").strip()
    web_secret = os.getenv("WEB_SECRET", "").strip()
    if not web_secret:
        web_secret = encryption_key[:32].ljust(32, "x")

    return Settings(
        bot_token=os.getenv("BOT_TOKEN"),
        api_id=int(api_id),
        api_hash=api_hash,
        encryption_key=encryption_key,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db"),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
        web_host=os.getenv("WEB_HOST", "127.0.0.1"),
        web_port=int(os.getenv("WEB_PORT", "8080")),
        web_secret=web_secret,
        web_password=web_password,
        web_cors_origins=cors_origins,
        allow_insecure=allow_insecure,
    )


def validate_bot_settings(settings: Settings) -> None:
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN не установлен в .env файле")
    if not settings.admin_ids and not settings.allow_insecure:
        raise ValueError(
            "ADMIN_IDS не задан. Укажите Telegram ID администраторов через запятую "
            "или установите ALLOW_INSECURE=true только для локальной разработки."
        )


def validate_web_settings(settings: Settings) -> None:
    if not settings.web_password:
        raise ValueError("WEB_PASSWORD обязателен для web-платформы")
    if settings.web_password in _INSECURE_DEFAULTS and not settings.allow_insecure:
        raise ValueError(
            "WEB_PASSWORD использует небезопасное значение по умолчанию. "
            "Задайте надёжный пароль или ALLOW_INSECURE=true для локальной разработки."
        )
    if len(settings.web_password) < 8 and not settings.allow_insecure:
        raise ValueError("WEB_PASSWORD должен быть не короче 8 символов")
    if settings.web_secret in _INSECURE_DEFAULTS and not settings.allow_insecure:
        raise ValueError(
            "WEB_SECRET использует небезопасное значение по умолчанию. "
            "Сгенерируйте случайную строку длиной ≥32 символов."
        )
    if len(settings.web_secret) < 32 and not settings.allow_insecure:
        raise ValueError("WEB_SECRET должен быть не короче 32 символов")


def verify_web_password(provided: str, settings: Settings) -> bool:
    return secrets.compare_digest(provided.strip(), settings.web_password)
