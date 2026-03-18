from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.test import start_test_kb
from bot.services.messaging import media_path, send_result_and_offer
from bot.services.test_data import load_test_data
from bot.services.users import get_user, upsert_user

router = Router()
settings = get_settings()
test_data = load_test_data().base


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    tg_user = message.from_user
    if not tg_user:
        return

    user = await upsert_user(session, tg_user.id, tg_user.first_name, tg_user.username)
    await state.clear()

    if user.test_completed and user.leading_type and user.secondary_type:
        await send_result_and_offer(
            message.bot,
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
        )
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
