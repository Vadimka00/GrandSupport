# handlers/common_messages.py

from aiogram import Router, F
from aiogram.types import Message, ContentType, ReplyKeyboardRemove
from aiogram.enums import ChatType
from database import crud
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
from utils.logger import logger
from services.i18n import t
from services import openai
from handlers.start import get_main_keyboard
from services.cache import (
    get_user_cached,
    get_active_request_by_user_cached,
    get_active_request_by_moderator_cached,
    get_close_text,
    get_language_name_cached
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

    # ===== ФИЛЬТР допустимых сообщений =====
    if message.photo and not message.caption:
        return  # игнорируем фото без подписи

    if message.media_group_id:
        return  # игнорируем медиагруппы

    sender = await get_user_cached(message.from_user.id)
    if not sender:
        return

    role = sender.role
    sender_lang = sender.language_code
    original_text = message.caption or message.text or ""

    if role in ("moderator", "admin"):
        # ===== МОДЕРАТОР =====
        req = await get_active_request_by_moderator_cached(sender.id)
        if not req:
            return

        # Закрытие запроса по кнопке
        close_text = await get_close_text(sender_lang)
        if message.text == close_text:
            await crud.close_request(req.id)
            logger.info(f"Moderator {sender.id} closed request {req.id}")

            confirm = await t("request_closed_confirm", sender_lang)
            await message.answer(confirm, reply_markup=ReplyKeyboardRemove())

            notify = await t("request_closed", req.language)
            kb = await get_main_keyboard(req.language)
            await message.bot.send_message(req.user_id, notify, reply_markup=kb)
            await caches.get("default").delete(f"get_active_request_by_moderator_cached:{sender.id}")
            return

        # Получатель — пользователь
        recipient = await get_user_cached(req.user_id)
        recipient_lang = recipient.language_code

    elif role == "user":
        # ===== ПОЛЬЗОВАТЕЛЬ =====
        req = await get_active_request_by_user_cached(sender.id)
        if not req or not req.assigned_moderator_id:
            return

        recipient = await get_user_cached(req.assigned_moderator_id)
        recipient_lang = recipient.language_code

    else:
        return  # неизвестная роль

    # ======= Показ "печатает/отправляет" =======
    action = "upload_photo" if message.photo else "typing"
    await message.bot.send_chat_action(recipient.id, action=action)


    # ======= ПЕРЕВОД и СБОРКА =======

    if sender_lang != recipient_lang:
        languages = await get_language_name_cached()
        lang_name = next(
            (l["name_ru"] for l in languages if l["code"] == recipient_lang),
            recipient_lang
        )
        translated_text = await openai.translate_with_gpt(
            text=original_text,
            lang_name=lang_name
        )
        message_to_send = translated_text
        combined_text = f"{original_text}\n\n{translated_text}"
    else:
        message_to_send = original_text
        combined_text = original_text

    # ======= ОТПРАВКА =======

    if message.photo:
        await message.bot.send_photo(
            recipient.id,
            photo=message.photo[-1].file_id,
            caption=message_to_send
        )
    else:
        await message.bot.send_message(
            recipient.id,
            text=message_to_send
        )

    # ======= СОХРАНЕНИЕ В БАЗУ =======
    await crud.save_message(
        request_id=req.id,
        sender_id=sender.id,
        text=combined_text if not message.photo else None,
        caption=combined_text if message.photo else None,
        photo_file_id=message.photo[-1].file_id if message.photo else None
    )

    logger.info(f"{role.capitalize()} message forwarded: from {sender.id} to {recipient.id}, req_id={req.id}")
