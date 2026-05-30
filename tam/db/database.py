import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tam.db.models import Base


class Database:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, echo=False)
        self.session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _migrate_schema(self, conn) -> None:
        """Добавляет новые колонки в существующие таблицы SQLite."""
        migrations = [
            "ALTER TABLE accounts ADD COLUMN proxy_id INTEGER",
        ]
        for statement in migrations:
            try:
                await conn.execute(text(statement))
            except Exception:
                pass

    async def init_db(self) -> None:
        os.makedirs("data", exist_ok=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._migrate_schema(conn)
