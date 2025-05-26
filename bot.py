# bot.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import Bot, DefaultBotProperties
from config import BOT_TOKEN
from services.i18n import load_translations
from utils.logger import setup_logger, logger
from middlewares.group_filter import GroupFilterMiddleware
from tasks.poller import poll_status_table


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

async def main():
    setup_logger()
    logger.info("Launching bot...")

    await load_translations()
    logger.info("✅ Translations loaded")

    from handlers import start, user_request, moderator, common_messages, admin

    dp = Dispatcher()

    # # Подключаем middleware ДО запуска
    # dp.message.middleware(GroupFilterMiddleware())
    # dp.callback_query.middleware(GroupFilterMiddleware())

    # Роутеры
    dp.include_routers(
        start.router,
        user_request.router,
        moderator.router,
        common_messages.router,
        admin.admin_router,
    )

    logger.info("🚀 Bot is polling...")
    # Фоновый таск
    asyncio.create_task(poll_status_table(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())