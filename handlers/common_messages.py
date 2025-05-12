from aiogram import Router, F
from aiogram.types import Message, ContentType
from aiogram.enums import ChatType
from database import crud
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
from utils.logger import logger
from services.i18n import t
from handlers.start import get_main_keyboard

router = Router()

@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.content_type.in_([ContentType.TEXT, ContentType.PHOTO])
)
async def unified_handler(message: Message):
    sender = await crud.get_user(message.from_user.id)
    if not sender:
        return

    # --- МОДЕРАТОР: проверяем, не нажал ли он «Закрыть» ---
    if sender.role == "moderator":
        close_text = await t("close_button", sender.language_code)
        if message.text == close_text:
            # 1) Закрываем тикет
            req = await crud.get_active_request_by_moderator(sender.id)
            if not req:
                return await message.answer(await t("no_active_request", sender.language_code))
            await crud.close_request(req.id)
            logger.info(f"Moderator {sender.id} closed request {req.id}")

            # 2) Подтверждаем модератору + основная клавиатура
            confirm = await t("request_closed_confirm", sender.language_code)
            mod_kb = await get_main_keyboard(sender.language_code)
            await message.answer(confirm, reply_markup=mod_kb)

            # 3) Уведомляем пользователя + его основная клавиатура
            user_lang = req.language
            notify = await t("request_closed", user_lang)
            user_kb = await get_main_keyboard(user_lang)
            await message.bot.send_message(req.user_id, notify, reply_markup=user_kb)
            return

        # если это не кнопка «Закрыть», а обычный ответ модератора
        req = await crud.get_active_request_by_moderator(sender.id)
        if not req:
            return
        await crud.save_message(req.id, sender.id, message)
        logger.info(f"Moderator reply saved: mod_id={sender.id}, request_id={req.id}")

        # пересылаем пользователю
        caption = f"📨 {message.caption or message.text or ''}"
        if message.photo:
            await message.bot.send_photo(req.user_id, message.photo[-1].file_id, caption=caption)
        else:
            await message.bot.send_message(req.user_id, caption)
        return

    # --- ПОЛЬЗОВАТЕЛЬ: обычное сообщение в рамках тикета ---
    if sender.role == "user":
        req = await crud.get_active_request_by_user(sender.id)
        if not req:
            # если нет активного тикета — игнорим
            return

        await crud.save_message(req.id, sender.id, message)
        logger.info(f"User message saved: user_id={sender.id}, request_id={req.id}")

        caption = f"📨 {message.caption or message.text or ''}"
        # если назначен модератор — шлём ему, иначе в группу
        target = req.assigned_moderator_id or (
            SUPPORT_GROUP_RU_ID if sender.language_code == 'ru' else SUPPORT_GROUP_EN_ID
        )
        if message.photo:
            await message.bot.send_photo(target, message.photo[-1].file_id, caption=caption)
        else:
            await message.bot.send_message(target, caption)
        return
