# database/base.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DB_URL

# Параметры пула:
#   pool_size     — сколько соединений держим в пуле
#   max_overflow  — сколько «сверхпула» может создаться временно
#   pool_timeout  — сколько ждать свободного соединения, прежде чем упасть
#   pool_recycle  — сколько секунд «жить» соединению, прежде чем пересоздать
engine = create_async_engine(
    DB_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    # опционально добавьте pre_ping для живых соединений:
    pool_pre_ping=True
)

# сессии теперь будут брать соединения из пула
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,      # можно выключить, если не нужен
    future=True           # рекомендуемая опция
)

class Base(DeclarativeBase):
    pass