from aiocache import cached, Cache, caches
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from services.i18n import t
from database import crud

# Глобальная настройка кеша
caches.set_config({
    "default": {
        "cache": "aiocache.SimpleMemoryCache",
        "ttl": 60
    }
})

@cached(ttl=60, cache=Cache.MEMORY)
async def get_user_cached(user_id: int):
    return await crud.get_user(user_id)

@cached(ttl=60, cache=Cache.MEMORY)
async def get_active_request_by_user_cached(user_id: int):
    return await crud.get_active_request_by_user(user_id)

@cached(ttl=60, cache=Cache.MEMORY)
async def get_active_request_by_moderator_cached(mod_id: int):
    return await crud.get_active_request_by_moderator(mod_id)

@cached(ttl=30, cache=Cache.MEMORY)
async def get_initial_message_cached(request_id: int):
    return await crud.get_initial_message(request_id)

@cached(ttl=30, cache=Cache.MEMORY)
async def get_request_by_id_cached(request_id: int):
    return await crud.get_request_by_id(request_id)

@cached(ttl=300, cache=Cache.MEMORY)
async def get_language_keyboard() -> InlineKeyboardMarkup:
    langs = await crud.get_available_languages()
    buttons = [
        [InlineKeyboardButton(text=f"{lang.emoji} {lang.name}", callback_data=f"lang:{lang.code}")]
        for lang in langs
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@cached(ttl=60, cache=Cache.MEMORY)
async def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    btn = KeyboardButton(text=await t("contact_support", lang))
    builder.add(btn)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

@cached(ttl=300, cache=Cache.MEMORY)
async def t_cached(key: str, lang: str):
    return await t(key, lang)

@cached(ttl=300, cache=Cache.MEMORY)
async def get_close_text(lang: str):
    return await t("close_button", lang)