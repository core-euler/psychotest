import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import SessionLocal
from bot.keyboards.payment import payment_kb
from bot.services.users import get_user, mark_result_sent
from bot.services.yookassa import create_payment_link

logger = logging.getLogger(__name__)

_scheduled_offer_tasks: dict[int, asyncio.Task] = {}

PAYMENT_OFFER_TEXT = (
    "Теперь ты знаешь свой тип блогера и форматы, которые тебе подходят.\n\n"
    "Но главный вопрос остаётся:\n"
    "чем их заполнять и как превратить блог в инструмент, который даёт охваты и продажи.\n\n"
    "У тебя уже есть знания и опыт.\n"
    "А вокруг — люди, которым это нужно.\n"
    "Проблема только в одном: они тебя не видят.\n\n"
    "Я помогу собрать блог, который будет:\n"
    "— привлекать внимание\n"
    "— давать результат\n"
    "— и при этом не выжигать тебя, потому что выстроен под твой тип\n\n"
    "Что внутри и какая стоимость — жми и смотри → https://clck.ru/3SaxiL\n\n"
    "Все материалы уже готовы — без ожидания, просто заходишь и начинаешь.\n\n"
    "Жми «Оплатить» и присоединяйся👇\n\n"
    "Если после оплаты доступ не пришёл — напиши сюда @vladyslav234, тебе откроют вручную\n\n"
    "Если не открывается платёжная система — включи VPN\n\n"
    "Нажимая «Оплатить», ты принимаешь условия оферты"
)

PRE_VIDEO_TEXT = (
    "Теперь самое главное - как использовать свой типаж, "
    "чтобы быстро и без сопротивления вырастить блог.\n\n"
    "✅Я записал видеоинструкцию\n\n"
    "Нажимай на кнопку👇"
)


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


async def _create_payment_url(user_id: int, shop_id: str, secret_key: str, amount: str, return_url: str) -> str | None:
    try:
        _, confirmation_url = await create_payment_link(
            shop_id=shop_id,
            secret_key=secret_key,
            amount=amount,
            user_id=user_id,
            return_url=return_url,
        )
        return confirmation_url
    except Exception:
        logger.exception("Failed to create YooKassa payment for user %s", user_id)
        return None


async def _send_payment_offer(bot: Bot, user_id: int, payment_url: str) -> None:
    await bot.send_message(user_id, PAYMENT_OFFER_TEXT, reply_markup=payment_kb(payment_url))


async def _schedule_payment_flow(
    bot: Bot,
    user_id: int,
    shop_id: str,
    secret_key: str,
    amount: str,
    return_url: str,
) -> None:
    try:
        await asyncio.sleep(120)
        if await _is_user_paid(user_id):
            return

        payment_url = await _create_payment_url(user_id, shop_id, secret_key, amount, return_url)
        if not payment_url:
            await bot.send_message(user_id, "Не удалось создать ссылку на оплату. Попробуйте позже или напишите @vladyslav234.")
            return

        await _send_payment_offer(bot, user_id, payment_url)

        await asyncio.sleep(3600)
        if await _is_user_paid(user_id):
            return

        payment_url_2 = await _create_payment_url(user_id, shop_id, secret_key, amount, return_url)
        if payment_url_2:
            await bot.send_message(
                user_id,
                "Напоминание: доступ к мастер-классу открыт по кнопке ниже.",
                reply_markup=payment_kb(payment_url_2),
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
    *,
    is_paid: bool = False,
    masterclass_link: str | None = None,
    channel_link: str | None = None,
    shop_id: str = "",
    secret_key: str = "",
    payment_amount: str = "2990.00",
    return_url: str = "",
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

    # 1. Result image + caption
    type_image = media_path(leading["image"])
    if type_image.exists():
        await bot.send_photo(chat_id=user_id, photo=FSInputFile(str(type_image)), caption=result_caption)
    else:
        await bot.send_message(user_id, result_caption)

    # 2. Telegra.ph article links
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

    # 3. Channel subscription link (free, always sent)
    if channel_link:
        await bot.send_message(
            user_id,
            "Подписывайся на наш канал:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Подписаться на канал", url=channel_link)]]
            ),
        )

    # 4. Pre-video text
    await bot.send_message(user_id, PRE_VIDEO_TEXT)

    # 5. Promo video
    promo_video = media_path("masterclass_promo.mp4")
    if promo_video.exists():
        await bot.send_video(chat_id=user_id, video=FSInputFile(str(promo_video)))
    else:
        await bot.send_message(user_id, "ТУТ БУДЕТ ВИДЕО")

    # 6. Payment offer (delayed) or access message
    if is_paid and masterclass_link:
        await send_access_message(bot, user_id, masterclass_link, channel_link or "")
    else:
        existing = _scheduled_offer_tasks.get(user_id)
        if existing and not existing.done():
            existing.cancel()
        _scheduled_offer_tasks[user_id] = asyncio.create_task(
            _schedule_payment_flow(bot, user_id, shop_id, secret_key, payment_amount, return_url)
        )

    await mark_result_sent(session, user_id)


async def send_access_message(bot: Bot, user_id: int, masterclass_link: str, channel_link: str) -> None:
    await bot.send_message(
        user_id,
        "Оплата подтверждена. Доступы:\n"
        f"- Мастер-класс: {masterclass_link}\n"
        f"- Канал участников: {channel_link}",
    )
