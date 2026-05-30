from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from tam.db.models import Proxy
from tam.services.proxy_utils import parse_proxy_line
from web.auth import get_current_user
from web.dependencies import get_db, get_proxy_manager
from web.schemas import (
    ProxyBulkImportRequest,
    ProxyCreateRequest,
    ProxyResponse,
    ProxyTestResponse,
    ProxyUpdateRequest,
)

router = APIRouter(
    prefix="/api/proxies",
    tags=["proxies"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ProxyResponse])
async def list_proxies(db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(select(Proxy).order_by(Proxy.created_at.desc()))
        return [ProxyResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy(
    payload: ProxyCreateRequest,
    db=Depends(get_db),
    proxy_manager=Depends(get_proxy_manager),
):
    try:
        if payload.raw_line:
            parsed = parse_proxy_line(payload.raw_line)
            protocol, host, port = parsed["protocol"], parsed["host"], parsed["port"]
            username, password = parsed.get("username"), parsed.get("password")
        else:
            protocol, host, port = payload.protocol, payload.host, payload.port
            username, password = payload.username, payload.password
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    async with db.session_maker() as session:
        existing = await session.execute(
            select(Proxy).where(
                Proxy.host == host,
                Proxy.port == port,
                Proxy.protocol == protocol,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Прокси уже существует")

        proxy = await proxy_manager.create_proxy(
            session,
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            password=password,
            label=payload.label,
        )
    return ProxyResponse.model_validate(proxy)


@router.post("/import", response_model=list[ProxyResponse])
async def import_proxies(
    payload: ProxyBulkImportRequest,
    db=Depends(get_db),
    proxy_manager=Depends(get_proxy_manager),
):
    try:
        async with db.session_maker() as session:
            created = await proxy_manager.import_from_text(session, payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Все прокси уже в базе")
    return [ProxyResponse.model_validate(p) for p in created]


@router.patch("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: int,
    payload: ProxyUpdateRequest,
    db=Depends(get_db),
):
    async with db.session_maker() as session:
        result = await session.execute(select(Proxy).where(Proxy.id == proxy_id))
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Прокси не найден")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(proxy, key, value)
        await session.commit()
        await session.refresh(proxy)
    return ProxyResponse.model_validate(proxy)


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int, db=Depends(get_db)):
    async with db.session_maker() as session:
        result = await session.execute(select(Proxy).where(Proxy.id == proxy_id))
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Прокси не найден")
        await session.delete(proxy)
        await session.commit()
    return {"status": "ok"}


@router.post("/{proxy_id}/test", response_model=ProxyTestResponse)
async def test_proxy(
    proxy_id: int,
    db=Depends(get_db),
    proxy_manager=Depends(get_proxy_manager),
):
    async with db.session_maker() as session:
        result = await session.execute(select(Proxy).where(Proxy.id == proxy_id))
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Прокси не найден")

        ok, error = await proxy_manager.test_proxy(proxy)
        proxy.last_checked_at = datetime.utcnow()
        proxy.is_healthy = ok
        if ok:
            proxy.fail_count = 0
        else:
            proxy.fail_count = (proxy.fail_count or 0) + 1
        await session.commit()

    return ProxyTestResponse(ok=ok, error=error)
