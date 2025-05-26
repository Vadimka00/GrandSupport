# handlers/user_request.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards.inline import take_request_kb
from utils.logger import logger

from database import crud
from services.i18n import support_triggers, t
from services import openai

import asyncio
from services.cache import get_user_cached, get_all_groups_with_languages_cached

router = Router()

class SupportRequestStates(StatesGroup):
    waiting_for_message = State()

@router.message(F.text.in_(support_triggers))
async def request_support(message: Message, state: FSMContext):
    user = await get_user_cached(message.from_user.id)
    logger.info(f"User {message.from_user.id} started support request process")
    if not user:
        return await message.answer("User not found.")
    
    if user.role in ("admin", "moderator"):
        logger.info(f"Ignored support request from {user.role} {message.from_user.id}")
        return  # просто игнорируем, ничего не отвечаем

    await state.set_state(SupportRequestStates.waiting_for_message)
    await message.answer(await t("enter_request", user.language_code))

@router.message(SupportRequestStates.waiting_for_message)
async def receive_request(message: Message, state: FSMContext):
    user = await get_user_cached(message.from_user.id)
    if not user:
        return await message.answer("User not found.")

    if user.role in ("admin", "moderator"):
        logger.warning(f"Unexpected state for {user.role} {user.id}, clearing FSM")
        await state.clear()
        return

    # Сохраняем запрос и сообщение
    request = await crud.create_support_request(user.id, user.language_code)
    asyncio.create_task(crud.save_message(request.id, user.id, message))
    logger.info(f"New support request created: req_id={request.id}, user_id={user.id}")

    # Формируем текст на языке пользователя
    request_text = await t("new_request_text", user.language_code)
    request_text = request_text.replace("\\n", "\n").replace("{text}", message.text or message.caption or "")

    # Клавиатура
    kb = await take_request_kb(request.id, user.language_code)

    # Получаем все группы с этим языком
    all_groups = await get_all_groups_with_languages_cached()
    user_groups = [
        group for group in all_groups
        if user.language_code in group["languages"]
    ]

    # Ищем среди них одну группу, в которой есть и ru
    group_with_ru = next(
        (group for group in user_groups if "ru" in group["languages"]),
        None
    )

    # Получаем перевод, если он нужен
    translated = ""
    if user.language_code != "ru" and group_with_ru:
        translated = await openai.translate_with_gpt(
            text=request_text,
            lang_name="Русский"
        )

    # Рассылка
    for group in user_groups:
        group_id = group["group_id"]
        final_text = request_text

        if group_with_ru and group_id == group_with_ru["group_id"] and translated:
            final_text = f"{request_text}\n\n{translated}"

        if message.photo:
            msg = await message.bot.send_photo(
                group_id,
                photo=message.photo[-1].file_id,
                caption=final_text,
                reply_markup=kb
            )
            await crud.save_request_message(
                request_id=request.id,
                chat_id=group_id,
                message_id=msg.message_id,
                caption=final_text,
                photo_file_id=message.photo[-1].file_id
            )
        else:
            msg = await message.bot.send_message(
                group_id,
                final_text,
                reply_markup=kb
            )
            await crud.save_request_message(
                request_id=request.id,
                chat_id=group_id,
                message_id=msg.message_id,
                text=final_text
            )

    # Подтверждение пользователю
    request_sent = await t("request_sent", user.language_code)
    request_sent = request_sent.replace("\\n", "\n")
    await message.answer(request_sent, reply_markup=ReplyKeyboardRemove())
    await state.clear()