from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import uuid4

from telethon import TelegramClient


@dataclass
class PendingLogin:
    client: TelegramClient
    phone: str
    code: str | None = None
    created_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class PendingAuthStore:
    def __init__(self, ttl_minutes: int = 10):
        self._store: dict[str, PendingLogin] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def _cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            session_id
            for session_id, pending in self._store.items()
            if now - pending.created_at > self.ttl
        ]
        for session_id in expired:
            self.discard(session_id)

    def create(self, client: TelegramClient, phone: str) -> str:
        self._cleanup()
        session_id = str(uuid4())
        self._store[session_id] = PendingLogin(client=client, phone=phone)
        return session_id

    def get(self, session_id: str) -> PendingLogin | None:
        self._cleanup()
        return self._store.get(session_id)

    def set_code(self, session_id: str, code: str) -> None:
        pending = self.get(session_id)
        if pending:
            pending.code = code

    async def discard(self, session_id: str) -> None:
        pending = self._store.pop(session_id, None)
        if pending:
            await pending.client.disconnect()
