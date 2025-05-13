# handlers/start.py
from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import (
    Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
    CallbackQuery,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from services.i18n import t, load_translations
from database import crud
from utils.logger import logger
from services.cache import get_user_cached, get_language_keyboard, get_main_keyboard, get_active_request_by_user_cached
import asyncio

router = Router()

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.text == "/start"
)
async def cmd_start(message: Message):
    # Сброс старой клавиатуры и приветствие по умолчанию
    await message.answer(
        await t("welcome", "en"),
        reply_markup=ReplyKeyboardRemove()
    )

    # Создаём или обновляем пользователя (не кешируем)
    user = await crud.upsert_user(message.from_user)
    logger.info(f"User {message.from_user.id} started bot (/start)")

    if user.language_code:
        lang = user.language_code
        greeting = await t("welcome_back", lang)

        # Проверяем роль
        if user.role not in ("admin", "moderator"):
            active_req = await get_active_request_by_user_cached(user.id)
            if active_req:
                notice = await t("you_have_active_request", lang)
                await message.answer(notice)
            else:
                kb = await get_main_keyboard(lang)
                await message.answer(greeting, reply_markup=kb)
        else:
            await message.answer(greeting)
    else:
        lang_kb = await get_language_keyboard()
        await message.answer(
            "Выберите язык / Choose your language:",
            reply_markup=lang_kb
        )

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.text == "/reload_translations"
)
async def cmd_reload_translations(message: Message):
    # Получаем пользователя из кеша
    user = await get_user_cached(message.from_user.id)
    if not user or user.role != "admin":
        await message.answer("❌ Команда доступна только администраторам.")
        logger.warning(f"Unauthorized /reload_translations attempt by {message.from_user.id}")
        return

    await load_translations()
    await message.answer("✅ Переводы успешно обновлены.")
    logger.info(f"Moderator {message.from_user.id} reloaded translations")

@router.callback_query(
    F.data.startswith("lang:")
)
async def language_selected(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    # Обновляем язык пользователя без блокировки
    asyncio.create_task(crud.set_user_language(callback.from_user.id, lang))
    logger.info(f"User {callback.from_user.id} selected language: {lang}")

    lang_text = await t("language_selected", lang)
    await callback.message.edit_text(lang_text, reply_markup=None)
    info_text = await t("welcome_info", lang)
    kb   = await get_main_keyboard(lang)
    await callback.message.answer(info_text, reply_markup=kb)
    await callback.answer()
