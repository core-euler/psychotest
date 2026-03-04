import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import SessionLocal
from bot.keyboards.payment import payment_kb
from bot.services.users import get_user, mark_result_sent

_scheduled_offer_tasks: dict[int, asyncio.Task] = {}


def media_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "media" / name


def result_links_kb(
    leading_name: str,
    leading_url: str,
    secondary_name: str | None,
    secondary_url: str | None,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=leading_name, url=leading_url)]]
    if secondary_name and secondary_url:
        rows.append([InlineKeyboardButton(text=secondary_name, url=secondary_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _is_user_paid(user_id: int) -> bool:
    async with SessionLocal() as session:
        user = await get_user(session, user_id)
        return bool(user and user.paid)


async def _send_payment_offer(bot: Bot, user_id: int, offer_text: str, payment_url: str) -> None:
    masterclass_cover = media_path("masterclass_cover.png")
    if masterclass_cover.exists():
        await bot.send_photo(
            user_id,
            photo=FSInputFile(str(masterclass_cover)),
            caption=offer_text,
            reply_markup=payment_kb(payment_url),
        )
    else:
        await bot.send_message(user_id, offer_text, reply_markup=payment_kb(payment_url))


async def _schedule_payment_flow(bot: Bot, user_id: int, offer_text: str, payment_url: str) -> None:
    try:
        # Give user 2 minutes to review materials before payment offer.
        await asyncio.sleep(120)
        if await _is_user_paid(user_id):
            return

        await _send_payment_offer(bot, user_id, offer_text, payment_url)

        # If payment is still missing, send reminder in 1 hour.
        await asyncio.sleep(3600)
        if await _is_user_paid(user_id):
            return

        await bot.send_message(
            user_id,
            "Напоминание: доступ к мастер-классу открыт по кнопке ниже.",
            reply_markup=payment_kb(payment_url),
        )
    finally:
        _scheduled_offer_tasks.pop(user_id, None)


async def send_result_and_offer(
    bot: Bot,
    session: AsyncSession,
    user_id: int,
    leading_code: str,
    secondary_code: str | None,
    test_data: dict,
    payment_url: str,
    *,
    is_paid: bool = False,
    masterclass_link: str | None = None,
    channel_link: str | None = None,
) -> None:
    types = test_data["types"]
    leading = types[leading_code]
    secondary = types.get(secondary_code) if secondary_code else None

    secondary_name = secondary["name"] if secondary else "—"
    result_caption = (
        f"Твой ведущий тип: {leading['name']}\n"
        f"Второстепенный тип: {secondary_name}\n\n"
        f"{leading['short_description']}"
    )

    type_image = media_path(leading["image"])
    if type_image.exists():
        await bot.send_photo(chat_id=user_id, photo=FSInputFile(str(type_image)), caption=result_caption)
    else:
        await bot.send_message(user_id, result_caption)

    await bot.send_message(
        user_id,
        "Описание твоих психотипов:",
        reply_markup=result_links_kb(
            leading_name=leading["name"],
            leading_url=leading["telegra_ph_url"],
            secondary_name=secondary["name"] if secondary else None,
            secondary_url=secondary["telegra_ph_url"] if secondary else None,
        ),
    )

    await bot.send_message(user_id, "ТУТ БУДЕТ ВИДЕО")

    if is_paid and masterclass_link and channel_link:
        await send_access_message(bot, user_id, masterclass_link, channel_link)
    else:
        offer_text = test_data.get("masterclass_offer_message", "Доступ к обучению открыт ниже.")
        existing = _scheduled_offer_tasks.get(user_id)
        if existing and not existing.done():
            existing.cancel()
        _scheduled_offer_tasks[user_id] = asyncio.create_task(
            _schedule_payment_flow(bot, user_id, offer_text, payment_url)
        )

    await mark_result_sent(session, user_id)


async def send_access_message(bot: Bot, user_id: int, masterclass_link: str, channel_link: str) -> None:
    await bot.send_message(
        user_id,
        "Оплата подтверждена. Доступы:\n"
        f"- Мастер-класс: {masterclass_link}\n"
        f"- Канал участников: {channel_link}",
    )
