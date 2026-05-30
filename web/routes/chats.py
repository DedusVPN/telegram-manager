from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select

from tam.db.models import Account
from web.auth import get_current_user
from web.dependencies import get_account_manager, get_db
from web.schemas import (
    BotCommandResponse,
    ChatMessageResponse,
    DialogResponse,
    MessageClickRequest,
    MessageKeyboardResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from web.security import safe_telegram_error

router = APIRouter(prefix="/api/accounts", tags=["chats"], dependencies=[Depends(get_current_user)])


async def _get_active_account(account_id: int, db) -> Account:
    async with db.session_maker() as session:
        result = await session.execute(
            select(Account).where(Account.id == account_id, Account.is_active == True)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аккаунт не найден")
        return account


@router.get("/{account_id}/dialogs", response_model=list[DialogResponse])
async def get_dialogs(
    account_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    dialogs = await account_manager.get_dialogs(
        account.id,
        account.session_string,
        limit=limit,
        search=search,
    )
    return [DialogResponse.model_validate(dialog) for dialog in dialogs]


@router.get("/{account_id}/lookup", response_model=DialogResponse)
async def lookup_username(
    account_id: int,
    username: str = Query(min_length=1, max_length=100),
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    try:
        result = await account_manager.search_by_username(
            account.id,
            account.session_string,
            username,
        )
    except (LookupError, ValueError) as exc:
        raise safe_telegram_error(exc, not_found=isinstance(exc, LookupError)) from exc
    except Exception as exc:
        raise safe_telegram_error(exc) from exc
    return DialogResponse.model_validate(result)


@router.post("/{account_id}/chats/{chat_id}/read")
async def mark_chat_read(
    account_id: int,
    chat_id: str,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    try:
        return await account_manager.mark_chat_read(
            account.id,
            account.session_string,
            chat_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise safe_telegram_error(exc) from exc


@router.get("/{account_id}/chats/{chat_id}/avatar")
async def get_chat_avatar(
    account_id: int,
    chat_id: str,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    try:
        avatar = await account_manager.get_chat_avatar(
            account.id,
            account.session_string,
            chat_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise safe_telegram_error(exc) from exc

    if not avatar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аватар не найден")

    return Response(
        content=avatar,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/{account_id}/chats/{chat_id}/keyboard", response_model=MessageKeyboardResponse | None)
async def get_active_keyboard(
    account_id: int,
    chat_id: str,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    keyboard = await account_manager.get_active_reply_keyboard(
        account.id,
        account.session_string,
        chat_id,
    )
    if not keyboard:
        return None
    return MessageKeyboardResponse.model_validate(keyboard)


@router.get("/{account_id}/chats/{chat_id}/commands", response_model=list[BotCommandResponse])
async def get_bot_commands(
    account_id: int,
    chat_id: str,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    commands = await account_manager.get_bot_commands(
        account.id,
        account.session_string,
        chat_id,
    )
    return [BotCommandResponse.model_validate(command) for command in commands]


@router.get("/{account_id}/chats/{chat_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    account_id: int,
    chat_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset_id: int = Query(default=0, ge=0),
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    messages = await account_manager.get_messages(
        account.id,
        account.session_string,
        chat_id,
        limit=limit,
        offset_id=offset_id,
    )
    return [ChatMessageResponse.model_validate(message) for message in messages]


@router.post("/{account_id}/chats/{chat_id}/messages", response_model=SendMessageResponse)
async def send_chat_message(
    account_id: int,
    chat_id: str,
    payload: SendMessageRequest,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    result = await account_manager.send_chat_message(
        account.id,
        account.session_string,
        chat_id,
        payload.text,
        parse_mode=payload.parse_mode,
    )
    return SendMessageResponse.model_validate(result)


@router.post("/{account_id}/chats/{chat_id}/messages/{message_id}/click")
async def click_message_button(
    account_id: int,
    chat_id: str,
    message_id: int,
    payload: MessageClickRequest,
    db=Depends(get_db),
    account_manager=Depends(get_account_manager),
):
    account = await _get_active_account(account_id, db)
    try:
        return await account_manager.click_message_button(
            account.id,
            account.session_string,
            chat_id,
            message_id,
            row=payload.row,
            col=payload.col,
            text=payload.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise safe_telegram_error(exc) from exc
