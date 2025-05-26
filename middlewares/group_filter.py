# middlewares/group_filter.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable
from services.cache import get_allowed_group_ids_cached
from config import SUPPORT_GROUP_RU_ID, SUPPORT_GROUP_EN_ID
from utils.logger import logger

class GroupFilterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            chat = event.chat if isinstance(event, Message) else event.message.chat
            if chat.type in {"group", "supergroup"}:
                allowed_ids = await get_allowed_group_ids_cached()
                if chat.id not in allowed_ids:
                    logger.warning(f"Blocked update from unknown group: {chat.id}")
                    return  # блокируем

        return await handler(event, data)