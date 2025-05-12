# handlers/moderator.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import crud
from services.i18n import t
from utils.logger import logger
from services.cache import (
    get_user_cached,
    get_active_request_by_moderator_cached,
    get_initial_message_cached,
    get_request_by_id_cached,
    t_cached
)

router = Router()

@router.callback_query(F.data.startswith("take:"))
async def take_request(callback: CallbackQuery):
    request_id = int(callback.data.split(":")[1])

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

    # Пересылаем модератору оригинальное сообщение пользователя
    initial = await get_initial_message_cached(request_id)
    if initial:
        if initial.photo_file_id:
            await callback.bot.send_photo(
                moderator.id,
                photo=initial.photo_file_id,
                caption=initial.caption or initial.text
            )
        else:
            await callback.bot.send_message(
                moderator.id,
                initial.text or initial.caption or ""
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
    taken_by = f"@{moderator.username}" if moderator.username else str(moderator.id)
    template = await t_cached("taken_by", user_lang)
    taken_text = template.replace("{moderator}", taken_by)

    if callback.message.photo:
        orig_caption = callback.message.caption or ""
        new_caption = f"{orig_caption}\n\n{taken_text}"
        if new_caption != orig_caption:
            await callback.message.edit_caption(new_caption)
    else:
        orig_text = callback.message.text or ""
        new_text = f"{orig_text}\n\n{taken_text}"
        if new_text != orig_text:
            await callback.message.edit_text(new_text)

    # Убираем inline-кнопки группы
    try:
        await callback.message.edit_reply_markup()
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Unexpected TelegramBadRequest: {e}")
            raise

    # Ответ успешного взятия
    success_text = await t_cached("taken_success", lang)
    await callback.answer(success_text)

