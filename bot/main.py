import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.config import get_settings
from bot.db import SessionLocal, init_db
from bot.handlers import admin, payment, start, test


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        async with SessionLocal() as session:
            data["session"] = session
            return await handler(event, data)


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    await init_db()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(test.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)

    try:
        try:
            await bot.set_my_name(name="Тест на типажи блогеров/ Малиновский")
        except Exception:
            logging.getLogger(__name__).warning("Failed to update bot name on startup", exc_info=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
