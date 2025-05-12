# handlers/start.py
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from services.i18n import t, load_translations
from database import crud
from utils.logger import logger

router = Router()

async def get_language_keyboard() -> InlineKeyboardMarkup:
    langs = await crud.get_available_languages()
    buttons = [
        [InlineKeyboardButton(text=f"{lang.emoji} {lang.name}", callback_data=f"lang:{lang.code}")]
        for lang in langs
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=await t("contact_support", lang)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user = await crud.upsert_user(message.from_user)
    logger.info(f"User {message.from_user.id} started bot (/start)")

    if user.language_code:
        lang = user.language_code
        greeting = await t("welcome_back", lang)
        kb = await get_main_keyboard(lang)
        await message.answer(greeting, reply_markup=kb)
    else:
        lang_kb = await get_language_keyboard()
        await message.answer("Выберите язык / Choose your language:", reply_markup=lang_kb)

@router.message(F.text == "/reload_translations")
async def cmd_reload_translations(message: Message):
    user = await crud.get_user(message.from_user.id)
    if not user or user.role != "moderator":
        await message.answer("❌ Команда доступна только модераторам.")
        logger.warning(f"Unauthorized /reload_translations attempt by {message.from_user.id}")
        return

    await load_translations()
    await message.answer("✅ Переводы успешно обновлены.")
    logger.info(f"Moderator {message.from_user.id} reloaded translations")

@router.callback_query(F.data.startswith("lang:"))
async def language_selected(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    await crud.set_user_language(callback.from_user.id, lang)
    logger.info(f"User {callback.from_user.id} selected language: {lang}")
    text = await t("language_selected", lang)

    kb = await get_main_keyboard(lang)
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()