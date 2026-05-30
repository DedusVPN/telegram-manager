import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tam.bot import AdminAccessMiddleware, router
from tam.config import get_settings, validate_bot_settings
from tam.db import Database
from tam.services import AccountManager, MessageSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main() -> None:
    settings = get_settings()
    validate_bot_settings(settings)

    os.makedirs("data", exist_ok=True)
    os.makedirs("sessions", exist_ok=True)

    db = Database(settings.database_url)
    await db.init_db()

    account_manager = AccountManager(settings.api_id, settings.api_hash, settings.encryption_key)
    message_sender = MessageSender(account_manager, db)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AdminAccessMiddleware(settings))
    dp.callback_query.middleware(AdminAccessMiddleware(settings))
    dp.include_router(router)

    @dp.message.middleware()
    async def inject_dependencies(handler, event, data):
        data["db"] = db
        data["account_manager"] = account_manager
        data["message_sender"] = message_sender
        return await handler(event, data)

    @dp.callback_query.middleware()
    async def inject_dependencies_callback(handler, event, data):
        data["db"] = db
        data["account_manager"] = account_manager
        data["message_sender"] = message_sender
        return await handler(event, data)

    try:
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await account_manager.close_all()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
