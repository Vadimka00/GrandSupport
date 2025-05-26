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

@cached(ttl=10, cache=Cache.MEMORY)
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

    # Преобразуем в список кнопок
    buttons = [
        InlineKeyboardButton(
            text=f"{lang.emoji} {lang.name}",
            callback_data=f"lang:{lang.code}"
        ) for lang in langs
    ]

    # Группируем по 3 в ряд
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]

    return InlineKeyboardMarkup(inline_keyboard=rows)

@cached(ttl=300, cache=Cache.MEMORY)
async def get_language_name_cached() -> list[dict[str, str]]:
    langs = await crud.get_available_languages()
    return [{"code": lang.code, "name_ru": lang.name_ru} for lang in langs]


@cached(ttl=300, cache=Cache.MEMORY)
async def get_language_codes_with_russian_names_cached() -> list[dict[str, str]]:
    return await crud.get_language_codes_with_russian_names()

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

@cached(ttl=300, cache=Cache.MEMORY)
async def get_support_group_cached(group_id: int):
    return await crud.get_support_group(group_id)

@cached(ttl=300, cache=Cache.MEMORY)
async def get_allowed_group_ids_cached() -> set[int]:
    groups = await crud.get_all_groups_with_languages()
    
    if not groups:
        from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
        return {SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID}

    return {group["group_id"] for group in groups}

@cached(ttl=300, cache=Cache.MEMORY)
async def get_all_groups_with_languages_cached() -> list[dict]:
    return await crud.get_all_groups_with_languages()