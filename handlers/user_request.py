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

router = Router()

class SupportRequestStates(StatesGroup):
    waiting_for_message = State()

@router.message(F.text.in_(["✉️ Обратиться в поддержку", "✉️ Contact support"]))
async def request_support(message: Message, state: FSMContext):
    user = await crud.get_user(message.from_user.id)
    logger.info(f"User {message.from_user.id} started support request process")
    if not user:
        return await message.answer("User not found.")

    await state.set_state(SupportRequestStates.waiting_for_message)
    await message.answer(await t("enter_request", user.language_code))

@router.message(SupportRequestStates.waiting_for_message)
async def receive_request(message: Message, state: FSMContext):
    user = await crud.get_user(message.from_user.id)
    if not user:
        return await message.answer("User not found.")

    # Сохраняем запрос
    request = await crud.create_support_request(user.id, user.language_code)

    # Сохраняем сообщение
    await crud.save_message(request.id, user.id, message)
    logger.info(f"New support request created: req_id={request.id}, user_id={user.id}")

    # Выбираем группу
    group_id = SUPPORT_GROUP_RU_ID if user.language_code == 'ru' else SUPPORT_GROUP_EN_ID

    # Пересылаем в группу
    request_text = await t(f"new_request_text", user.language_code)
    request_text = request_text.replace("\\n", "\n")
    request_text = request_text.replace("{text}", message.text or message.caption or "")

    kb = await take_request_kb(request.id, user.language_code)

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

    await message.answer(
        await t("request_sent", user.language_code),
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
