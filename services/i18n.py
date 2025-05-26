# services/i18n.py
from sqlalchemy import select
from database.base import async_session
from database.models import Translation
import logging

logger = logging.getLogger(__name__)  # наверху файла

_translation_cache = {}

support_triggers: list[str] = []

async def load_translations():
    global _translation_cache, support_triggers
    async with async_session() as session:
        result = await session.execute(select(Translation))
        _translation_cache = {}
        support_triggers = []

        for row in result.scalars():
            _translation_cache.setdefault(row.key, {})[row.lang] = row.text
            if row.key == "contact_support":
                support_triggers.append(row.text)

        logger.info(f"📋 support_triggers = {support_triggers}")

async def t(key: str, lang: str) -> str:
    if not _translation_cache:
        await load_translations()

    return _translation_cache.get(key, {}).get(lang) or f"[{key}]"