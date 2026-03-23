import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.test import start_test_kb
from bot.services.messaging import (
    is_user_subscribed,
    media_path,
    send_pre_result_subscription_prompt,
    send_result_and_offer,
)
from bot.services.test_data import load_test_data
from bot.services.users import get_user, upsert_user

router = Router()
settings = get_settings()
test_data = load_test_data().base
logger = logging.getLogger(__name__)
_result_delivery_locks: set[int] = set()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    tg_user = message.from_user
    if not tg_user:
        return

    user = await upsert_user(session, tg_user.id, tg_user.first_name, tg_user.username)
    await state.clear()

    if user.test_completed and user.leading_type and user.secondary_type:
        await send_pre_result_subscription_prompt(message.bot, user.id, settings.channel_invite_link)
        return

    start_cover = media_path("start_cover.png")
    if start_cover.exists():
        await message.answer_photo(
            photo=FSInputFile(str(start_cover)),
            caption=test_data.get("welcome_message", "Готов пройти тест?"),
            reply_markup=start_test_kb(),
        )
        return

    await message.answer(test_data.get("welcome_message", "Готов пройти тест?"), reply_markup=start_test_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Этот бот определяет ведущий и второстепенный психотип и открывает доступ к мастер-классу.")


@router.message(F.text & ~F.text.startswith("/"))
async def text_fallback(message: Message):
    await message.answer("Используй кнопки ниже.")


@router.callback_query(F.data.startswith("stale:"))
async def stale_cb(callback):
    await callback.answer()


@router.callback_query(F.data == "result:check_subscription")
async def check_subscription_and_send_result(callback, session: AsyncSession):
    user_id = callback.from_user.id
    if user_id in _result_delivery_locks:
        await callback.answer("Результат уже готовится")
        return

    await callback.answer("Проверяю подписку...")

    if settings.channel_chat_id is None:
        await callback.message.answer("Проверка подписки пока не настроена. Напиши @vladyslav234.")
        return

    is_subscribed = await is_user_subscribed(callback.bot, user_id, settings.channel_chat_id)
    if not is_subscribed:
        await callback.message.answer("СПЕРВА ПОДПИШИСЬ НА КАНАЛ ТАМ МНОГО ПОЛЕЗНОГО")
        return

    user = await get_user(session, user_id)
    if not user or not user.test_completed or not user.leading_type or not user.secondary_type:
        await callback.message.answer("Результат пока недоступен. Напиши @vladyslav234, если проблема повторится.")
        return

    _result_delivery_locks.add(user_id)
    try:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            logger.debug("Subscription prompt already removed for user %s", user_id)

        await send_result_and_offer(
            callback.bot,
            session,
            user.id,
            user.leading_type,
            user.secondary_type,
            test_data,
            is_paid=user.paid,
            masterclass_link=settings.masterclass_link,
            channel_link=settings.channel_invite_link,
            shop_id=settings.yookassa_shop_id,
            secret_key=settings.yookassa_secret_key,
            payment_amount=settings.yookassa_payment_amount,
            return_url=settings.yookassa_return_url,
            admin_ids=settings.admin_ids,
        )
    finally:
        _result_delivery_locks.discard(user_id)
