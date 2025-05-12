from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import crud
from services.i18n import t
from utils.logger import logger

router = Router()

@router.callback_query(F.data.startswith("take:"))
async def take_request(callback: CallbackQuery):
    request_id = int(callback.data.split(":")[1])
    moderator = await crud.get_user(callback.from_user.id)
    if not moderator or moderator.role != "moderator":
        logger.warning(f"Non-moderator {callback.from_user.id} tried to take request")
        await callback.answer(await t("only_moderator", moderator.language_code or "en"), show_alert=True)
        return

    existing = await crud.get_active_request_by_moderator(moderator.id)
    if existing:
        await callback.answer(await t("already_in_progress_mod", moderator.language_code), show_alert=True)
        return

    updated = await crud.assign_request_to_moderator(request_id, moderator.id)
    if not updated:
        await callback.answer(await t("already_in_progress", moderator.language_code), show_alert=True)
        return

    # Уведомляем модератора в личку
    lang = moderator.language_code
    mod_msg = await t("you_assigned", lang)
    close_text = await t("close_button", lang)
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

    # Отправляем модератору оригинальное сообщение пользователя
    initial = await crud.get_initial_message(request_id)
    if initial:
        if initial.photo_file_id:
            await callback.bot.send_photo(
                moderator.id,
                photo=initial.photo_file_id,
                caption=initial.caption or initial.text
            )
        else:
            text = initial.text or initial.caption or ""
            await callback.bot.send_message(
                moderator.id,
                text
            )

    # Уведомляем пользователя
    req = await crud.get_request_by_id(request_id)
    user_lang = req.language
    await callback.bot.send_message(
        req.user_id,
        await t("moderator_connected", user_lang),
        reply_markup=ReplyKeyboardRemove()
    )

    # Обновляем сообщение в группе: добавляем информацию о том, кто взял
    taken_by = f"@{moderator.username}" if moderator.username else str(moderator.id)
    template = await t("taken_by", user_lang)
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

    await callback.answer(await t("taken_success", lang))

