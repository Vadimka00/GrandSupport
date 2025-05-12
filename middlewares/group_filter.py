# middlewares/group_filter.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
from utils.logger import logger

ALLOWED_GROUP_IDS = {SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID}

class GroupFilterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        chat_id = None

        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id

        if chat_id and str(chat_id).startswith("-"):  # Только для групп
            if chat_id not in ALLOWED_GROUP_IDS:
                logger.warning(f"Blocked message from unknown group: {chat_id}")
                return  # Игнорируем событие

        return await handler(event, data)