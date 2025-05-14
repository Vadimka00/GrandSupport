# handlers/user_request.py

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards.inline import take_request_kb
from utils.logger import logger

from database import crud
from services.i18n import t
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID

import asyncio
from services.cache import get_user_cached

router = Router()

class SupportRequestStates(StatesGroup):
    waiting_for_message = State()

@router.message(F.text.in_(["✉️ Обратиться в поддержку", "✉️ Contact support"]))
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
        return  # ничего не отправляем

    # Сохраняем запрос
    request = await crud.create_support_request(user.id, user.language_code)

    # Фоновая запись сообщения в БД
    asyncio.create_task(crud.save_message(request.id, user.id, message))
    logger.info(f"New support request created: req_id={request.id}, user_id={user.id}")

    # Выбираем группу
    group_id = SUPPORT_GROUP_RU_ID if user.language_code == 'ru' else SUPPORT_GROUP_EN_ID

    # Формируем текст запроса
    request_text = await t("new_request_text", user.language_code)
    request_text = request_text.replace("\\n", "\n").replace("{text}", message.text or message.caption or "")

    # Inline клавиатура для модераторов
    kb = await take_request_kb(request.id, user.language_code)

    # Пересылаем в группу
    if message.photo:
        await message.bot.send_photo(
            group_id,
            photo=message.photo[-1].file_id,
            caption=request_text,
            reply_markup=kb
        )
    else:
        await message.bot.send_message(
            group_id,
            request_text,
            reply_markup=kb
        )

    # Подтверждение пользователю
    request_sent = await t("request_sent", user.language_code)
    request_sent = request_sent.replace("\\n", "\n")

    await message.answer(
        request_sent,
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
