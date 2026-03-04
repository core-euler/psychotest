from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def payment_kb(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить мастер-класс", url=payment_url)],
            [InlineKeyboardButton(text="Я оплатил", callback_data="payment:paid_check")],
        ]
    )
