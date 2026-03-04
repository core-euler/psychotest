from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.services.messaging import send_access_message
from bot.services.notifications import notify_admins
from bot.services.payment import create_manual_review
from bot.services.users import get_user

router = Router()
settings = get_settings()


@router.callback_query(F.data == "payment:paid_check")
async def paid_check(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    user = await get_user(session, user_id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if user.paid:
        await send_access_message(
            callback.bot,
            user_id,
            settings.masterclass_link,
            settings.channel_invite_link,
        )
        await callback.answer("Доступ уже открыт")
        return

    review = await create_manual_review(session, user_id)
    await notify_admins(
        callback.bot,
        settings.admin_ids,
        (
            "Новая заявка 'Я оплатил'\n"
            f"user_id: {user_id}\n"
            f"username: @{user.username if user.username else '-'}\n"
            f"review_id: {review.id}\n"
            "Перейдите в /admin_panel -> 🧾 Заявки \"Я оплатил\""
        ),
    )
    await callback.message.answer("Платеж пока не подтвержден автоматически. Заявка отправлена администратору.")
    await callback.answer()
