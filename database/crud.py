# database/crud.py
from sqlalchemy import select, update, delete, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.mysql import insert
from database.base import async_session
from database.models import User, SupportRequest, MessageHistory, Language, Status, SupportGroup, SupportRequestMessage
from datetime import datetime
from aiogram.types import Message
from utils.logger import logger
from typing import Optional
import traceback

async def upsert_user(tg_user):
    try:
        async with async_session() as session:
            stmt = insert(User).values(
                id=tg_user.id,
                username=tg_user.username,
                full_name=f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip(),
            ).on_duplicate_key_update(
                username=tg_user.username,
                full_name=f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip(),
            )
            await session.execute(stmt)
            await session.commit()

            # Получение и возврат обновлённого пользователя
            result = await session.execute(select(User).where(User.id == tg_user.id))
            user = result.scalar_one()
            logger.info(f"User {tg_user.id} upserted successfully.")
            return user  # <- обязательно вернуть user
    except Exception as e:
        logger.error(f"Error in upsert_user: {e}\n{traceback.format_exc()}")
        return None

async def get_user(user_id: int) -> Optional[User]:
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error in get_user({user_id}): {e}\n{traceback.format_exc()}")
        return None

async def set_user_language(user_id: int, lang: str):
    try:
        async with async_session() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(language_code=lang)
            )
            await session.commit()
            logger.info(f"User {user_id} language set to {lang}")
    except Exception as e:
        logger.error(f"Error in set_user_language({user_id}, {lang}): {e}\n{traceback.format_exc()}")

async def create_support_request(user_id: int, lang: str) -> Optional[SupportRequest]:
    try:
        async with async_session() as session:
            req = SupportRequest(user_id=user_id, language=lang, status="pending")
            session.add(req)
            await session.commit()
            await session.refresh(req)
            logger.info(f"SupportRequest {req.id} created for user {user_id}")
            return req
    except Exception as e:
        logger.error(f"Error in create_support_request({user_id}, {lang}): {e}\n{traceback.format_exc()}")
        return None

async def save_message(
    request_id: int,
    sender_id: int,
    text: str | None = None,
    caption: str | None = None,
    photo_file_id: str | None = None
):
    try:
        async with async_session() as session:
            msg = MessageHistory(
                request_id=request_id,
                sender_id=sender_id,
                text=text,
                caption=caption,
                photo_file_id=photo_file_id
            )
            session.add(msg)
            await session.commit()
            logger.info(f"Message saved for request {request_id} from {sender_id}")
    except Exception as e:
        logger.error(f"Error in save_message(request_id={request_id}, sender_id={sender_id}): {e}\n{traceback.format_exc()}")

async def assign_request_to_moderator(request_id: int, moderator_id: int) -> bool:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SupportRequest).where(SupportRequest.id == request_id)
            )
            req = result.scalar_one_or_none()
            if not req or req.status != "pending":
                return False

            req.status = "in_progress"
            req.assigned_moderator_id = moderator_id
            req.taken_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Request {request_id} assigned to moderator {moderator_id}")
            return True
    except Exception as e:
        logger.error(f"Error in assign_request_to_moderator({request_id}, {moderator_id}): {e}\n{traceback.format_exc()}")
        return False

async def get_request_by_id(request_id: int) -> Optional[SupportRequest]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SupportRequest).where(SupportRequest.id == request_id)
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error in get_request_by_id({request_id}): {e}\n{traceback.format_exc()}")
        return None

async def get_active_request_by_user(user_id: int) -> Optional[SupportRequest]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SupportRequest)
                .where(
                    SupportRequest.user_id == user_id,
                    or_(
                        SupportRequest.status == "in_progress",
                        SupportRequest.status == "pending"
                    )
                )
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(
            f"Error in get_active_request_by_user({user_id}): {e}\n{traceback.format_exc()}"
        )
        return None

async def get_active_request_by_moderator(moderator_id: int) -> Optional[SupportRequest]:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SupportRequest)
                .where(SupportRequest.assigned_moderator_id == moderator_id, SupportRequest.status == "in_progress")
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error in get_active_request_by_moderator({moderator_id}): {e}\n{traceback.format_exc()}")
        return None

async def close_request(request_id: int):
    try:
        async with async_session() as session:
            await session.execute(
                update(SupportRequest)
                .where(SupportRequest.id == request_id)
                .values(status="closed", closed_at=datetime.utcnow())
            )
            await session.commit()
            logger.info(f"Request {request_id} closed.")
    except Exception as e:
        logger.error(f"Error in close_request({request_id}): {e}\n{traceback.format_exc()}")

async def get_initial_message(request_id: int) -> Optional[MessageHistory]:
    """
    Возвращает первое сообщение (инициирующее запрос) для данного request_id.
    """
    try:
        async with async_session() as session:
            result = await session.execute(
                select(MessageHistory)
                .where(MessageHistory.request_id == request_id)
                .order_by(MessageHistory.id)
                .limit(1)
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error in get_initial_message({request_id}): {e}")
        return None
    
async def get_available_languages():
    async with async_session() as session:
        result = await session.execute(select(Language).where(Language.available == True))
        return result.scalars().all()

async def get_language_codes_with_russian_names() -> list[dict[str, str]]:
    async with async_session() as session:
        result = await session.execute(
            select(Language.code, Language.name_ru).where(Language.available == True)
        )
        return [{"code": code, "name_ru": name_ru} for code, name_ru in result.all()]

async def get_pending_statuses():
    async with async_session() as session:
        result = await session.execute(select(Status))
        return result.scalars().all()

async def delete_status_by_id(user_id: int):
    async with async_session() as session:
        await session.execute(delete(Status).where(Status.id == user_id))
        await session.commit()

async def get_support_group(group_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(SupportGroup).where(SupportGroup.id == group_id)
        )
        return result.scalar_one_or_none()

async def create_or_update_support_group(group_id: int, title: str, photo_url: str | None):
    async with async_session() as session:
        existing = await session.get(SupportGroup, group_id)

        if existing:
            existing.title = title
            existing.photo_url = photo_url
        else:
            session.add(SupportGroup(id=group_id, title=title, photo_url=photo_url))

        await session.commit()
    
async def get_all_groups_with_languages():
    async with async_session() as session:
        result = await session.execute(
            select(SupportGroup)
            .options(selectinload(SupportGroup.languages))
        )
        groups = result.scalars().all()

        return [
            {
                "group_id": group.id,
                "group_name": group.title,
                "languages": [lang.language_code for lang in group.languages]
            }
            for group in groups
        ]
    
async def save_request_message(
    request_id: int,
    chat_id: int,
    message_id: int,
    text: str | None = None,
    caption: str | None = None,
    photo_file_id: str | None = None
):
    async with async_session() as session:
        session.add(SupportRequestMessage(
            request_id=request_id,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            caption=caption,
            photo_file_id=photo_file_id
        ))
        await session.commit()


async def get_request_messages(request_id: int) -> list[SupportRequestMessage]:
    async with async_session() as session:
        result = await session.execute(
            select(SupportRequestMessage)
            .where(SupportRequestMessage.request_id == request_id)
        )
        return result.scalars().all()