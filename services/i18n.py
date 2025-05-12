# services/i18n.py
from sqlalchemy import select
from database.base import async_session
from database.models import Translation

_translation_cache = {}

async def load_translations():
    global _translation_cache
    async with async_session() as session:
        result = await session.execute(select(Translation))
        _translation_cache = {}
        for row in result.scalars():
            _translation_cache.setdefault(row.key, {})[row.lang] = row.text

async def t(key: str, lang: str) -> str:
    if not _translation_cache:
        await load_translations()

    return _translation_cache.get(key, {}).get(lang) or f"[{key}]"