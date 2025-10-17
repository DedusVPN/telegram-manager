import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import Database
from account_manager import AccountManager
from message_sender import MessageSender
from handlers import router

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./data/bot.db')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле")
if not API_ID:
    raise ValueError("API_ID не установлен в .env файле")
if not API_HASH:
    raise ValueError("API_HASH не установлен в .env файле")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY не установлен в .env файле")

API_ID = int(API_ID)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    os.makedirs('data', exist_ok=True)
    os.makedirs('sessions', exist_ok=True)

    db = Database(DATABASE_URL)
    await db.init_db()

    account_manager = AccountManager(API_ID, API_HASH, ENCRYPTION_KEY)
    message_sender = MessageSender(account_manager, db)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)

    @dp.message.middleware()
    async def inject_dependencies(handler, event, data):
        data['db'] = db
        data['account_manager'] = account_manager
        data['message_sender'] = message_sender
        return await handler(event, data)

    @dp.callback_query.middleware()
    async def inject_dependencies_callback(handler, event, data):
        data['db'] = db
        data['account_manager'] = account_manager
        data['message_sender'] = message_sender
        return await handler(event, data)

    try:
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await account_manager.close_all()
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
