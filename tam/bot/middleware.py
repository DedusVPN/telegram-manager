from aiogram import BaseMiddleware, Router
from aiogram.types import CallbackQuery, Message, TelegramObject
from typing import Any, Awaitable, Callable

from tam.config import Settings


class AdminAccessMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if self.settings.allow_insecure or not self.settings.admin_ids:
            return await handler(event, data)

        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None or user_id not in self.settings.admin_ids:
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещён")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён", show_alert=True)
            return None

        return await handler(event, data)
