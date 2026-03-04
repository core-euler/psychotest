from aiogram import Bot


async def notify_admins(bot: Bot, admin_ids: set[int], text: str, reply_markup=None) -> None:
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            # Notification errors are non-blocking by requirement.
            pass
