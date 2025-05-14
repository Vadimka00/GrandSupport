# handlers/common_messages.py

from aiogram import Router, F
from aiogram.types import Message, ContentType, ReplyKeyboardRemove
from aiogram.enums import ChatType
from database import crud
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
from utils.logger import logger
from services.i18n import t
from handlers.start import get_main_keyboard
from services.cache import (
    get_user_cached,
    get_active_request_by_user_cached,
    get_active_request_by_moderator_cached,
    get_close_text
)
import asyncio
from aiocache import caches

router = Router()

async def _forward_caption(bot, target: int, message: Message) -> None:
    caption = f"📨 {message.caption or message.text or ''}"
    if message.photo:
        await bot.send_photo(target, message.photo[-1].file_id, caption=caption)
    else:
        await bot.send_message(target, caption)

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.content_type.in_([ContentType.TEXT, ContentType.PHOTO])
)
async def unified_handler(message: Message):
    # Получаем пользователя из кеша
    sender = await get_user_cached(message.from_user.id)
    if not sender:
        return

    role = sender.role
    lang = sender.language_code

    # Модератор
    if role in ("moderator", "admin"):
        req = await get_active_request_by_moderator_cached(sender.id)
        close_text = await get_close_text(lang)

        # Кнопка "Закрыть"
        if message.text == close_text:
            if not req:
                return await message.answer(await t("no_active_request", lang))

            await crud.close_request(req.id)
            logger.info(f"Moderator {sender.id} closed request {req.id}")

            confirm = await t("request_closed_confirm", lang)
            await message.answer(confirm, reply_markup=ReplyKeyboardRemove())

            notify = await t("request_closed", req.language)
            user_kb = await get_main_keyboard(req.language)
            await message.bot.send_message(req.user_id, notify, reply_markup=user_kb)
            await caches.get("default").delete(f"get_active_request_by_moderator_cached:{sender.id}")
            return

        # Обычный ответ модератора
        if not req:
            return
        # Фоновая запись сообщения в БД
        asyncio.create_task(crud.save_message(req.id, sender.id, message))
        logger.info(f"Moderator reply enqueued: mod_id={sender.id}, request_id={req.id}")

        await _forward_caption(message.bot, req.user_id, message)
        return

    # Пользователь
    if role == "user":
        req = await get_active_request_by_user_cached(sender.id)
        if not req:
            return

        # Фоновая запись сообщения в БД
        asyncio.create_task(crud.save_message(req.id, sender.id, message))
        logger.info(f"User message enqueued: user_id={sender.id}, request_id={req.id}")

        target = req.assigned_moderator_id or (
            SUPPORT_GROUP_RU_ID if lang == "ru" else SUPPORT_GROUP_EN_ID
        )
        await _forward_caption(message.bot, target, message)
