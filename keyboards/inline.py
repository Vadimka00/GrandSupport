# keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.i18n import t

async def take_request_kb(request_id: int, lang: str) -> InlineKeyboardMarkup:
    text = await t("take_request_button", lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"take:{request_id}"
                )
            ]
        ]
    )


