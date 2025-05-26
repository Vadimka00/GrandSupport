import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("❌ Переменная OPENAI_API_KEY не найдена в окружении")

client = AsyncOpenAI(api_key=openai_api_key)

async def translate_with_gpt(text: str, lang_name: str) -> str:
    system_msg = (
        f"Ты — профессиональный переводчик и носитель языка ({lang_name}).\n"
        f"Твоя задача — перевести сообщение для службы поддержки на {lang_name}.\n\n"
        f"Переводи так, как сказал бы реальный человек. Разрешён лёгкий неформальный стиль, если он уместен.\n\n"
        f"Важно:\n"
        f"- Не добавляй ничего лишнего. Ответ — только перевод оригинального текста."
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": text}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip() if response.choices else text