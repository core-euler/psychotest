from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.test import question_kb
from bot.services.messaging import send_result_and_offer
from bot.services.scoring import add_scores, compute_type_from_scores
from bot.services.test_data import load_test_data
from bot.services.users import save_test_results
from bot.states import TestFlow

router = Router()
settings = get_settings()
loaded = load_test_data()
base_data = loaded.base
TYPE_ORDER = base_data["type_order"]


def _question_text(q_idx: int) -> tuple[str, list[dict]]:
    q = base_data["questions"][q_idx]
    return q["text"], q["options"]


async def _send_question(callback: CallbackQuery, q_idx: int, pick_no: int, exclude_option_id: str | None = None):
    text, options = _question_text(q_idx)
    visible_options = [o for o in options if o["id"] != exclude_option_id]
    options_text = "\n".join([f"{o['id']}) {o['text']}" for o in visible_options])
    step_label = "первый" if pick_no == 1 else "второй"
    prefix = f"Вопрос {q_idx + 1}/8\nВыбери {step_label} вариант ответа.\n\n"
    body = prefix + text + "\n\n" + options_text
    try:
        await callback.message.edit_text(
            body,
            reply_markup=question_kb(q_idx, pick_no, options, exclude_option_id=exclude_option_id),
        )
    except TelegramBadRequest as e:
        # Happens when callback comes from media message (photo/video) with caption.
        if "there is no text in the message to edit" in str(e):
            await callback.message.answer(
                body,
                reply_markup=question_kb(q_idx, pick_no, options, exclude_option_id=exclude_option_id),
            )
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                pass
        else:
            raise


@router.callback_query(F.data == "test:start")
async def test_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TestFlow.in_test)
    await state.update_data(q_index=0, pick_no=1, scores={}, first_pick_option=None)
    await _send_question(callback, 0, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("test:ans:"))
async def answer_question(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer()
        return

    _, _, q_idx_s, pick_s, option_code = parts
    cb_q_idx = int(q_idx_s)
    cb_pick = int(pick_s)

    data = await state.get_data()
    q_index = data.get("q_index")
    pick_no = data.get("pick_no")
    if q_index != cb_q_idx or pick_no != cb_pick:
        await callback.answer()
        return

    q = base_data["questions"][q_index]
    selected = next((o for o in q["options"] if o["id"] == option_code), None)
    if not selected:
        await callback.answer()
        return
    selected_scores = selected["scores"]

    scores = add_scores(data.get("scores", {}), selected_scores)
    await state.update_data(scores=scores)

    # First pick for this question: hide picked option, request second pick.
    if pick_no == 1:
        await state.update_data(pick_no=2, first_pick_option=option_code)
        await _send_question(callback, q_index, 2, exclude_option_id=option_code)
        await callback.answer()
        return

    # Second pick: move to next question.
    next_index = q_index + 1
    if next_index < 8:
        await state.update_data(q_index=next_index, pick_no=1, first_pick_option=None)
        await _send_question(callback, next_index, 1)
        await callback.answer()
        return

    all_data = await state.get_data()
    total_scores = all_data.get("scores", {})
    leading_type = compute_type_from_scores(total_scores, TYPE_ORDER)

    remaining_codes = [code for code in TYPE_ORDER if code != leading_type]
    secondary_type = compute_type_from_scores(total_scores, remaining_codes) if remaining_codes else leading_type
    secondary_max = total_scores.get(secondary_type, 0)
    secondary_types = [code for code in remaining_codes if total_scores.get(code, 0) == secondary_max]
    if not secondary_types:
        secondary_types = [secondary_type]

    user_id = callback.from_user.id
    await save_test_results(session, user_id, leading_type, secondary_type, secondary_types)
    await state.clear()

    await callback.message.delete()
    await send_result_and_offer(
        callback.bot,
        session,
        user_id,
        leading_type,
        secondary_type,
        base_data,
        channel_link=settings.channel_invite_link,
        shop_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
        payment_amount=settings.yookassa_payment_amount,
        return_url=settings.yookassa_return_url,
    )
    await callback.answer()
