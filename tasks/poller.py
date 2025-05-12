import asyncio
from aiogram import Bot
from services.i18n import t
from database import crud
from aiogram.types import ReplyKeyboardRemove
from services.cache import get_main_keyboard
from utils.logger import logger
from config import ADMIN_WEB

async def poll_status_table(bot: Bot):
    while True:
        entries = await crud.get_pending_statuses()
        for entry in entries:
            try:
                # Основной текст для любой роли
                if entry.role == "admin":
                    text = await t("assigned_admin", entry.language_code)
                    # Если в статусе есть текст (email + пароль), добавляем его
                    if entry.text:
                        text += f"\n\n{ADMIN_WEB}"
                        text += f"\n\n{entry.text}"
                    reply_markup = ReplyKeyboardRemove()

                elif entry.role == "moderator":
                    text = await t("assigned_mod", entry.language_code)
                    reply_markup = ReplyKeyboardRemove()

                else:  # обычный пользователь
                    text = await t("assigned_user", entry.language_code)
                    reply_markup = await get_main_keyboard(entry.language_code)

                await bot.send_message(entry.id, text, reply_markup=reply_markup)
                logger.info(f"Уведомление ({entry.role}) отправлено пользователю {entry.id}")

            except Exception as e:
                logger.error(f"Ошибка при отправке пользователю {entry.id}: {e}")

            # Убираем запись, чтобы не дублировать
            await crud.delete_status_by_id(entry.id)

        await asyncio.sleep(5)