from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.admin import admin_panel_kb, review_ids_kb, review_pagination_kb
from bot.services.admin_stats import build_stats_text
from bot.services.payment import get_open_reviews_page, recent_payments, resolve_review
from bot.services.users import get_user, mark_paid

router = Router()
settings = get_settings()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def _render_reviews_page(callback: CallbackQuery, session: AsyncSession, page: int) -> None:
    page_size = 10
    reviews, total = await get_open_reviews_page(session, page=page, page_size=page_size)
    if total == 0:
        await callback.message.answer("Открытых заявок нет.")
        return

    total_pages = (total + page_size - 1) // page_size
    current_page = page + 1

    lines: list[str] = [f'🧾 Открытые заявки (страница {current_page}/{total_pages}):']
    review_ids: list[int] = []
    for r in reviews:
        user = await get_user(session, r.user_id)
        display_name = f"@{user.username}" if user and user.username else (user.first_name if user else "-")
        created = r.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(
            "\n"
            f"ID оплаты: {r.id}\n"
            f"ID пользователя: {r.user_id}\n"
            f"Пользователь: {display_name}\n"
            f"Дата и время: {created}"
        )
        review_ids.append(r.id)

    lines.append('\nДля подтверждения заявки - нажмите на кнопку с ID заявки')
    await callback.message.answer("\n".join(lines), reply_markup=review_ids_kb(review_ids))

    has_prev = page > 0
    has_next = (page + 1) * page_size < total
    if has_prev or has_next:
        await callback.message.answer(
            "Навигация по страницам:",
            reply_markup=review_pagination_kb(page=page, has_prev=has_prev, has_next=has_next),
        )


@router.message(Command("admin_panel"))
async def admin_panel(message: Message):
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await message.answer("🛠 Админ-панель", reply_markup=admin_panel_kb())


@router.callback_query(F.data.startswith("admin:"))
async def admin_callbacks(callback: CallbackQuery, session: AsyncSession):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    data = callback.data

    if data == "admin:stats":
        text = await build_stats_text(session)
        await callback.message.answer(text)
        await callback.answer()
        return

    if data == "admin:reviews":
        await _render_reviews_page(callback, session, page=0)
        await callback.answer()
        return

    if data.startswith("admin:reviews:page:"):
        try:
            page = int(data.rsplit(":", 1)[1])
        except ValueError:
            await callback.answer()
            return
        await _render_reviews_page(callback, session, page=max(page, 0))
        await callback.answer()
        return

    if data == "admin:payments":
        payments = await recent_payments(session)
        if not payments:
            await callback.message.answer("Платежей пока нет.")
        else:
            lines = [
                f"- id={p.id}, user_id={p.user_id}, provider_id={p.provider_payment_id}, status={p.status}"
                for p in payments
            ]
            await callback.message.answer("Последние платежи:\n" + "\n".join(lines))
        await callback.answer()
        return

    if data.startswith("admin:review_confirm:"):
        parts = data.split(":")
        if len(parts) != 3:
            await callback.answer()
            return
        review_id = int(parts[2])

        review = await resolve_review(session, review_id, callback.from_user.id, approved=True)
        if not review:
            await callback.answer("Заявка уже обработана или не найдена", show_alert=True)
            return

        await mark_paid(session, review.user_id, payment_id=f"manual-review-{review.id}")
        await callback.bot.send_message(
            review.user_id,
            "Оплата подтверждена администратором.\nТУТ БУДЕТ ССЫЛКА НА МАСТЕРКЛАСС И КАНАЛ.",
        )
        await callback.message.answer(f"✅ Заявка ID {review_id} подтверждена.")

        await callback.answer()
        return

    await callback.answer()
