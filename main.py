import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_CHAT_ID, ADMIN_IDS
from database import init_db
from admin_handlers import router as admin_router
from user_handlers import router as user_router


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_BOT_TOKEN_HERE":
        raise RuntimeError("Заполните BOT_TOKEN в файле .env")
    if not ADMIN_CHAT_ID or not ADMIN_IDS:
        raise RuntimeError("Заполните ADMIN_CHAT_ID и ADMIN_IDS в файле .env")

    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(admin_router)
    dispatcher.include_router(user_router)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
