from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_test_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать тест", callback_data="test:start")]]
    )


def question_kb(q_index: int, pick_no: int, options: list[dict], exclude_option_id: str | None = None) -> InlineKeyboardMarkup:
    filtered = [opt for opt in options if opt["id"] != exclude_option_id]
    buttons = [
        InlineKeyboardButton(
            text=opt["id"],
            callback_data=f"test:ans:{q_index}:{pick_no}:{opt['id']}",
        )
        for opt in filtered
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
