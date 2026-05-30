from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from tam.config import Settings, get_settings, verify_web_password
from tam.db.models import Account
from web.auth import create_access_token, get_current_user
from web.dependencies import get_account_manager, get_db, get_pending_auth
from web.schemas import (
    AccountAuth2FARequest,
    AccountAuthResponse,
    AccountAuthStartRequest,
    AccountAuthStartResponse,
    AccountAuthVerifyRequest,
    AccountResponse,
    LoginRequest,
    LoginResponse,
)
from web.security import get_client_ip, login_rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    client_ip = get_client_ip(request)
    login_rate_limiter.check(client_ip)

    if not verify_web_password(payload.password, settings):
        login_rate_limiter.record_failure(client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный пароль")

    return LoginResponse(access_token=create_access_token(settings))


@router.get("/me")
async def me(_: str = Depends(get_current_user)):
    return {"username": "admin", "role": "admin"}


auth_accounts_router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)


@auth_accounts_router.get("", response_model=list[AccountResponse])
async def list_accounts(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    db=Depends(get_db),
):
    async with db.session_maker() as session:
        result = await session.execute(select(Account).order_by(Account.created_at.desc()))
        accounts = result.scalars().all()

    if search:
        query = search.strip().lower().lstrip("@")
        accounts = [
            account
            for account in accounts
            if query in (account.username or "").lower()
            or query in (account.first_name or "").lower()
            or query in (account.last_name or "").lower()
            or query in account.phone.lower()
        ]

    return [AccountResponse.model_validate(account) for account in accounts]


@auth_accounts_router.post("/auth/start", response_model=AccountAuthStartResponse)
async def start_account_auth(
    payload: AccountAuthStartRequest,
    account_manager=Depends(get_account_manager),
    pending_auth=Depends(get_pending_auth),
):
    phone = payload.phone.strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"

    client, auth_status = await account_manager.add_account(phone)
    if auth_status == "authorized":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Аккаунт уже авторизован")

    session_id = pending_auth.create(client, phone)
    return AccountAuthStartResponse(session_id=session_id, status="code_sent")


@auth_accounts_router.post("/auth/verify", response_model=AccountAuthResponse)
async def verify_account_auth(
    payload: AccountAuthVerifyRequest,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
    pending_auth=Depends(get_pending_auth),
):
    pending = pending_auth.get(payload.session_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия авторизации не найдена или истекла",
        )

    pending_auth.set_code(payload.session_id, payload.code.strip())
    result, auth_status = await account_manager.verify_code(
        pending.client,
        pending.phone,
        payload.code.strip(),
    )

    if auth_status == "password_required":
        return AccountAuthResponse(status="password_required", message="Требуется пароль 2FA")

    if auth_status == "invalid_code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код")

    if auth_status != "success" or not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка авторизации")

    async with db.session_maker() as session:
        existing = await session.execute(select(Account).where(Account.phone == result["phone"]))
        if existing.scalar_one_or_none():
            await pending_auth.discard(payload.session_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Аккаунт уже добавлен")

        account = Account(**result)
        session.add(account)
        await session.commit()
        await session.refresh(account)

    await pending_auth.discard(payload.session_id)
    return AccountAuthResponse(status="success", account=AccountResponse.model_validate(account))


@auth_accounts_router.post("/auth/2fa", response_model=AccountAuthResponse)
async def verify_account_2fa(
    payload: AccountAuth2FARequest,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
    pending_auth=Depends(get_pending_auth),
):
    pending = pending_auth.get(payload.session_id)
    if not pending or not pending.code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия авторизации не найдена",
        )

    result, auth_status = await account_manager.verify_code(
        pending.client,
        pending.phone,
        pending.code,
        payload.password,
        skip_sign_in=True,
    )

    if auth_status != "success" or not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль 2FA")

    async with db.session_maker() as session:
        existing = await session.execute(select(Account).where(Account.phone == result["phone"]))
        if existing.scalar_one_or_none():
            await pending_auth.discard(payload.session_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Аккаунт уже добавлен")

        account = Account(**result)
        session.add(account)
        await session.commit()
        await session.refresh(account)

    await pending_auth.discard(payload.session_id)
    return AccountAuthResponse(status="success", account=AccountResponse.model_validate(account))


@auth_accounts_router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    async with db.session_maker() as session:
        result = await session.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аккаунт не найден")

        account.is_active = False
        await session.commit()

    await account_manager.remove_account(account_id)
    return {"status": "ok"}
