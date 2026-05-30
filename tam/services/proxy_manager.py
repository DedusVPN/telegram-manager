import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.sessions import StringSession

from tam.db.models import Proxy
from tam.services.error_utils import format_exception
from tam.services.proxy_utils import parse_bulk_proxies, parse_proxy_line, proxy_to_telethon


class ProxyManager:
    def __init__(self, api_id: int, api_hash: str):
        self.api_id = api_id
        self.api_hash = api_hash

    @staticmethod
    def proxy_row_to_dict(proxy: Proxy) -> dict:
        return {
            "protocol": proxy.protocol,
            "host": proxy.host,
            "port": proxy.port,
            "username": proxy.username,
            "password": proxy.password,
        }

    async def pick_proxy(
        self,
        session: AsyncSession,
        *,
        proxy_id: int | None = None,
    ) -> Proxy | None:
        if proxy_id:
            result = await session.execute(
                select(Proxy).where(Proxy.id == proxy_id, Proxy.is_active == True)
            )
            return result.scalar_one_or_none()

        result = await session.execute(
            select(Proxy)
            .where(Proxy.is_active == True, Proxy.is_healthy == True)
            .order_by(Proxy.last_used_at.asc().nullsfirst(), Proxy.id.asc())
        )
        proxies = result.scalars().all()
        if not proxies:
            result = await session.execute(
                select(Proxy).where(Proxy.is_active == True).order_by(Proxy.id.asc())
            )
            proxies = result.scalars().all()
        return proxies[0] if proxies else None

    async def mark_proxy_used(self, session: AsyncSession, proxy: Proxy) -> None:
        proxy.last_used_at = datetime.utcnow()
        proxy.usage_count = (proxy.usage_count or 0) + 1
        await session.commit()

    async def test_proxy(self, proxy: Proxy, timeout: float = 15.0) -> tuple[bool, str | None]:
        telethon_proxy = proxy_to_telethon(self.proxy_row_to_dict(proxy))
        client = TelegramClient(
            StringSession(),
            self.api_id,
            self.api_hash,
            proxy=telethon_proxy,
            connection_retries=1,
            retry_delay=1,
            timeout=timeout,
        )
        try:
            await asyncio.wait_for(client.connect(), timeout=timeout)
            if not client.is_connected():
                return False, "Не удалось подключиться"
            return True, None
        except Exception as exc:
            return False, format_exception(exc)
        finally:
            if client.is_connected():
                await client.disconnect()

    async def create_proxy(
        self,
        session: AsyncSession,
        *,
        protocol: str,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        label: str | None = None,
    ) -> Proxy:
        proxy = Proxy(
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
            label=label,
        )
        session.add(proxy)
        await session.commit()
        await session.refresh(proxy)
        return proxy

    async def import_from_text(self, session: AsyncSession, text: str) -> list[Proxy]:
        parsed_list = parse_bulk_proxies(text)
        created: list[Proxy] = []
        for item in parsed_list:
            existing = await session.execute(
                select(Proxy).where(
                    Proxy.host == item["host"],
                    Proxy.port == item["port"],
                    Proxy.protocol == item["protocol"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            proxy = Proxy(
                protocol=item["protocol"],
                host=item["host"],
                port=item["port"],
                username=item.get("username"),
                password=item.get("password"),
            )
            session.add(proxy)
            created.append(proxy)
        await session.commit()
        for proxy in created:
            await session.refresh(proxy)
        return created

    def parse_line(self, line: str) -> dict:
        return parse_proxy_line(line)
