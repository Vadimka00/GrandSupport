# init_db.py
import asyncio
from database.base import engine
from database.models import Base

from config import DB_URL
print("🔎 DB_URL from .env =", DB_URL)

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init())