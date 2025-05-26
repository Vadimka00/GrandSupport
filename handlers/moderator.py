# handlers/moderator.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import crud
from services.i18n import t
from utils.logger import logger
from services import openai
from services.cache import (
    get_user_cached,
    get_active_request_by_moderator_cached,
    get_initial_message_cached,
    get_request_by_id_cached,
    t_cached,
    get_all_groups_with_languages_cached,
    get_language_name_cached
)

router = Router()

@router.callback_query(F.data.startswith("take:"))
async def take_request(callback: CallbackQuery):
    request_id = int(callback.data.split(":")[1])
    clicked_chat_id = callback.message.chat.id

    # Получаем модератора из кеша
    moderator = await get_user_cached(callback.from_user.id)
    if not moderator or moderator.role not in ("moderator", "admin"):
        logger.warning(f"Non-moderator {callback.from_user.id} tried to take request")
        text = await t_cached("only_moderator", moderator.language_code or "en")
        await callback.answer(text, show_alert=True)
        return

    # Проверяем, нет ли у модератора активного запроса
    existing = await get_active_request_by_moderator_cached(moderator.id)
    if existing:
        text = await t_cached("already_in_progress_mod", moderator.language_code)
        await callback.answer(text, show_alert=True)
        return

    # Пробуем назначить модератора
    updated = await crud.assign_request_to_moderator(request_id, moderator.id)
    if not updated:
        text = await t_cached("already_in_progress", moderator.language_code)
        await callback.answer(text, show_alert=True)
        return

    # Уведомляем модератора и отправляем клавиатуру
    lang = moderator.language_code
    mod_msg = await t_cached("you_assigned", lang)
    close_text = await t_cached("close_button", lang)
    mod_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=close_text)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.bot.send_message(
        moderator.id,
        mod_msg,
        reply_markup=mod_kb
    )
    logger.info(f"Moderator {moderator.id} assigned to request {request_id}")

    # Получаем оригинал сообщения
    initial = await get_initial_message_cached(request_id)
    original_text = initial.caption or initial.text or ""

    # Получаем язык пользователя
    req = await get_request_by_id_cached(request_id)
    user_lang = req.language
    mod_lang = moderator.language_code

    # Если языки совпадают — не переводим
    if user_lang == mod_lang:
        final_text = original_text
    else:
        languages = await get_language_name_cached()
        lang_name = next(
            (lang["name_ru"] for lang in languages if lang["code"] == mod_lang),
            mod_lang
        )
        translated = await openai.translate_with_gpt(
            text=original_text,
            lang_name=lang_name
        )
        final_text = f"{original_text}\n\n{translated}"

    # Отправляем
    if initial.photo_file_id:
        await callback.bot.send_photo(
            moderator.id,
            photo=initial.photo_file_id,
            caption=final_text
        )
    else:
        await callback.bot.send_message(
            moderator.id,
            final_text
        )

    # Уведомляем пользователя о подключении модератора
    req = await get_request_by_id_cached(request_id)
    user_lang = req.language
    connected_text = await t_cached("moderator_connected", user_lang)
    await callback.bot.send_message(
        req.user_id,
        connected_text,
        reply_markup=ReplyKeyboardRemove()
    )

    # Обновляем сообщение в группе: добавляем информацию о том, кто взял
    template = await t_cached("taken_by", user_lang)

    # Получаем все сообщения запроса
    all_messages = await crud.get_request_messages(request_id)

    # Получаем список всех групп и названий
    groups = await get_all_groups_with_languages_cached()
    group_title_map = {
        group["group_id"]: group["group_name"]
        for group in groups
    }
    accepted_group_title = group_title_map.get(clicked_chat_id, "Группа")

    # Обновляем все сообщения во всех группах
    for msg in all_messages:
        try:
            if msg.chat_id == clicked_chat_id:
                # Текущая группа: вставляем имя модератора
                taken_text = template.replace(
                    "{moderator}",
                    f"@{moderator.username}" if moderator.username else str(moderator.id)
                )
                original_text = msg.caption or msg.text or ""
                updated_text = f"{original_text}\n\n{taken_text}"

                if msg.photo_file_id:
                    await callback.bot.edit_message_caption(
                        chat_id=msg.chat_id,
                        message_id=msg.message_id,
                        caption=updated_text,
                        reply_markup=None
                    )
                else:
                    await callback.bot.edit_message_text(
                        chat_id=msg.chat_id,
                        message_id=msg.message_id,
                        text=updated_text,
                        reply_markup=None
                    )
            else:
                # Остальные группы: вставляем название группы
                taken_text = template.replace(
                    "{moderator}",
                    f"✅ {accepted_group_title}"
                )
                original_text = msg.caption or msg.text or ""
                updated_text = f"{original_text}\n\n{taken_text}"

                if msg.photo_file_id:
                    await callback.bot.edit_message_caption(
                        chat_id=msg.chat_id,
                        message_id=msg.message_id,
                        caption=updated_text,
                        reply_markup=None
                    )
                else:
                    await callback.bot.edit_message_text(
                        chat_id=msg.chat_id,
                        message_id=msg.message_id,
                        text=updated_text,
                        reply_markup=None
                    )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.warning(f"⚠ Не удалось обновить сообщение в чате {msg.chat_id}: {e}")

    # Ответ модератору
    success_text = await t_cached("taken_success", lang)
    await callback.answer(success_text)
