from aiogram import Router, types, F
from aiogram.filters import Command
from database import crud
from services.cache import(
    get_user_cached,
    get_support_group_cached
)  
from database.models import SupportGroup

admin_router = Router()

@admin_router.message(Command("add_group"))
async def add_group_cmd(message: types.Message):
    user = await get_user_cached(message.from_user.id)
    
    if not user or user.role != "admin":
        return await message.reply("❌ У вас нет доступа к этой команде.")

    chat = message.chat
    group_id = chat.id
    title = chat.title or chat.full_name or chat.username or "Без названия"

    # Получаем фото чата через get_chat
    photo_url = None
    try:
        chat_info = await message.bot.get_chat(chat.id)
        if chat_info.photo:
            file = await message.bot.get_file(chat_info.photo.big_file_id)
            photo_url = f"{file.file_path}"
    except Exception as e:
        photo_url = None  # необязательно, но на всякий случай
        # можно залогировать: logger.warning(f"Не удалось получить фото группы: {e}")

    # Проверка — уже есть в базе?
    exists = await get_support_group_cached(group_id)
    if exists:
        return await message.reply("ℹ️ Эта группа уже зарегистрирована.")

    # Добавление в БД
    await crud.create_support_group(
        group_id=group_id,
        title=title,
        photo_url=photo_url
    )

    await message.reply("✅ Группа успешно зарегистрирована.")