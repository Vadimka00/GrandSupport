import os
import json
import asyncio
from openai import AsyncOpenAI
from openai import OpenAIError, RateLimitError, APIError, Timeout
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("❌ Переменная OPENAI_API_KEY не найдена в окружении")

client = AsyncOpenAI(api_key=openai_api_key)

# Семафор для ограничения одновременных переводов
openai_semaphore = asyncio.Semaphore(5)

async def translate_with_gpt(text: str, lang_name: str, retries: int = 3, delay: float = 2.0) -> str:
    system_msg = (
        f"Ты — профессиональный переводчик и носитель языка ({lang_name}).\n"
        f"Твоя задача — перевести сообщение для службы поддержки на {lang_name}.\n\n"
        f"Переводи так, как сказал бы реальный человек. Разрешён лёгкий неформальный стиль, если он уместен.\n\n"
        f"Важно:\n"
        f"- Не добавляй ничего лишнего. Ответ — только перевод оригинального текста."
    )

    async with openai_semaphore:  # 👈 здесь лимит concurrency
        for attempt in range(1, retries + 1):
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.2
                )
                return response.choices[0].message.content.strip()
            except (RateLimitError, Timeout, APIError, OpenAIError) as e:
                if attempt == retries:
                    print(f"❌ Перевод не удался после {retries} попыток: {e}")
                    return text
                await asyncio.sleep(delay * attempt)