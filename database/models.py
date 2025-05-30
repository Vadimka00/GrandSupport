from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from typing import List
from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)         # Telegram ID
    username = Column(String(100))                    # @username
    full_name = Column(String(255))                   # Имя + фамилия
    language_code = Column(String(3))                 # 'ru' / 'en'
    role = Column(String(50), default='user')         # 'user' / 'moderator'

    # Явно указываем, что это связь по полю SupportRequest.user_id
    requests = relationship(
        "SupportRequest",
        back_populates="user",
        foreign_keys="[SupportRequest.user_id]"
    )
    credentials = relationship("Credentials", uselist=False, back_populates="user")

class SupportRequest(Base):
    __tablename__ = "support_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    assigned_moderator_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending / in_progress / closed
    language: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    taken_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Связь на пользователя, отправившего запрос
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="requests"
    )
    # Дополнительная связь, чтобы легко получить назначенного модератора
    moderator = relationship(
        "User",
        foreign_keys=[assigned_moderator_id]
    )
    messages = relationship("MessageHistory", back_populates="request")

    messages_metadata = relationship("SupportRequestMessage", back_populates="request", cascade="all, delete-orphan")

class SupportRequestMessage(Base):
    __tablename__ = "support_request_messages"

    request_id = mapped_column(ForeignKey("support_requests.id"), primary_key=True)
    chat_id = mapped_column(BigInteger, primary_key=True)
    message_id = mapped_column(BigInteger, nullable=False)

    text = mapped_column(Text, nullable=True)           # текст, если сообщение без фото
    caption = mapped_column(Text, nullable=True)        # подпись под фото
    photo_file_id = mapped_column(String(255), nullable=True)  # если это фото

    request = relationship("SupportRequest", back_populates="messages_metadata")

class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("support_requests.id"))
    sender_id = Column(BigInteger, ForeignKey("users.id"))
    text = Column(Text, nullable=True)
    photo_file_id = Column(String(255), nullable=True)
    caption = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    request = relationship("SupportRequest", back_populates="messages")

class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), index=True)
    lang = Column(String(3))
    text = Column(Text)


class Language(Base):
    __tablename__ = "languages"

    code = Column(String(10), primary_key=True)
    name = Column(String(50), nullable=False)
    name_ru = Column(String(50), nullable=False)
    emoji = Column(String(10), default="")
    available = Column(Boolean, default=True)

class Status(Base):
    __tablename__ = "status"

    id = Column(BigInteger, primary_key=True)         # Telegram ID
    language_code = Column(String(3))                 # 'ru' / 'en'
    role = Column(String(50))
    text = Column(Text, nullable=True) 

class Credentials(Base):
    __tablename__ = "credentials"

    user_id       = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    user = relationship("User", back_populates="credentials")

class SupportGroup(Base):
    __tablename__ = "support_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    photo_url: Mapped[str] = mapped_column(String(512))

    languages: Mapped[List["SupportGroupLanguage"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    moderators: Mapped[List["ModeratorGroupLink"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

class SupportGroupLanguage(Base):
    __tablename__ = "support_group_languages"

    group_id: Mapped[int] = mapped_column(ForeignKey("support_groups.id"), primary_key=True)
    language_code: Mapped[str] = mapped_column(String(5), primary_key=True)  # 'ru', 'en', 'pl'

    group: Mapped["SupportGroup"] = relationship(back_populates="languages")

class ModeratorGroupLink(Base):
    __tablename__ = "moderator_group_links"

    moderator_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("support_groups.id"), primary_key=True)

    group: Mapped["SupportGroup"] = relationship(back_populates="moderators")