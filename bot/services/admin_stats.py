from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.services.test_data import load_test_data
from bot.services.users import type_distribution


async def build_stats_text(session: AsyncSession) -> str:
    type_names = {code: data["name"] for code, data in load_test_data().base["types"].items()}

    total = (await session.execute(select(func.count(User.id)))).scalar_one()
    completed = (await session.execute(select(func.count(User.id)).where(User.test_completed.is_(True)))).scalar_one()
    paid = (await session.execute(select(func.count(User.id)).where(User.paid.is_(True)))).scalar_one()
    conv = (paid / completed * 100) if completed else 0.0

    leading = await type_distribution(session, "leading_type")
    secondary = await type_distribution(session, "secondary_type")

    lead_text = "\n".join([f"- {type_names.get(k, k)}: {v}" for k, v in leading]) or "- нет данных"
    sec_text = "\n".join([f"- {type_names.get(k, k)}: {v}" for k, v in secondary]) or "- нет данных"

    return (
        "Статистика:\n"
        f"- Пользователей: {total}\n"
        f"- Завершили тест: {completed}\n"
        f"- Оплатили: {paid}\n"
        f"- Конверсия в оплату: {conv:.1f}%\n\n"
        "Ведущий тип:\n"
        f"{lead_text}\n\n"
        "Второстепенный тип:\n"
        f"{sec_text}"
    )
