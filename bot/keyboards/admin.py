from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text='🧾 Заявки "Я оплатил"', callback_data="admin:reviews")],
            [InlineKeyboardButton(text="💳 Последние оплаты", callback_data="admin:payments")],
        ]
    )


def review_actions_kb(review_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=f"admin:review:{review_id}:approve"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"admin:review:{review_id}:reject"),
            ]
        ]
    )


def review_ids_kb(review_ids: list[int]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"ID {rid}", callback_data=f"admin:review_confirm:{rid}")
        for rid in review_ids
    ]
    rows = [buttons[i : i + 5] for i in range(0, len(buttons), 5)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_pagination_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    row: list[InlineKeyboardButton] = []
    if has_prev:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:reviews:page:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"admin:reviews:page:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])
