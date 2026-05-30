from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tam.db.models import Account, Proxy
from tam.services.proxy_manager import ProxyManager


async def resolve_proxy_for_account(
    session: AsyncSession,
    account: Account,
) -> dict | None:
    if not account.proxy_id:
        return None
    result = await session.execute(
        select(Proxy).where(Proxy.id == account.proxy_id, Proxy.is_active == True)
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        return None
    return ProxyManager.proxy_row_to_dict(proxy)
