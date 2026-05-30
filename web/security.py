from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self._attempts: dict[str, list[datetime]] = defaultdict(list)

    def _prune(self, client_ip: str, now: datetime) -> None:
        self._attempts[client_ip] = [
            attempt for attempt in self._attempts[client_ip] if now - attempt < self.window
        ]

    def check(self, client_ip: str) -> None:
        now = datetime.now(timezone.utc)
        self._prune(client_ip, now)
        if len(self._attempts[client_ip]) >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток входа. Попробуйте позже.",
            )

    def record_failure(self, client_ip: str) -> None:
        now = datetime.now(timezone.utc)
        self._prune(client_ip, now)
        self._attempts[client_ip].append(now)


login_rate_limiter = LoginRateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def safe_telegram_error(exc: Exception, *, not_found: bool = False) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ValueError):
        status_code = status.HTTP_404_NOT_FOUND if not_found else status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=status_code, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Ошибка при обращении к Telegram API",
    )
