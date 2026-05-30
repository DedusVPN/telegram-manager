from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from tam.config import Settings, get_settings

security = HTTPBearer(auto_error=False)


def create_access_token(settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": "admin", "exp": expire}
    return jwt.encode(payload, settings.web_secret, algorithm="HS256")


def verify_token(token: str, settings: Settings) -> None:
    try:
        jwt.decode(token, settings.web_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    verify_token(credentials.credentials, settings)
    return credentials.credentials
