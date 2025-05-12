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
        if isinstance(event, Message):
            chat = event.chat
            if chat.type in {"group", "supergroup"} and chat.id not in ALLOWED_GROUP_IDS:
                logger.warning(f"Blocked message from unknown group: {chat.id}")
                return  # блокируем

        if isinstance(event, CallbackQuery):
            chat = event.message.chat
            if chat.type in {"group", "supergroup"} and chat.id not in ALLOWED_GROUP_IDS:
                logger.warning(f"Blocked callback from unknown group: {chat.id}")
                return  # блокируем

        return await handler(event, data)