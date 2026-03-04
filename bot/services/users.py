from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User


async def upsert_user(session: AsyncSession, user_id: int, first_name: str, username: str | None) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, first_name=first_name, username=username)
        session.add(user)
    else:
        user.first_name = first_name
        user.username = username
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def save_test_results(
    session: AsyncSession,
    user_id: int,
    leading_type: str,
    secondary_type: str,
    secondary_types: list[str] | None = None,
) -> None:
    user = await session.get(User, user_id)
    if not user:
        return
    user.leading_type = leading_type
    user.secondary_type = secondary_type
    user.secondary_types = secondary_types
    user.result_type = leading_type
    user.test_completed = True
    user.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def mark_result_sent(session: AsyncSession, user_id: int) -> None:
    user = await session.get(User, user_id)
    if not user:
        return
    user.last_result_sent_at = datetime.now(timezone.utc)
    await session.commit()


async def mark_paid(session: AsyncSession, user_id: int, payment_id: str) -> bool:
    user = await session.get(User, user_id)
    if not user:
        return False
    if user.paid:
        return False
    user.paid = True
    user.paid_at = datetime.now(timezone.utc)
    user.payment_id = payment_id
    user.payment_status = "confirmed"
    await session.commit()
    return True


async def type_distribution(session: AsyncSession, field: str) -> list[tuple[str, int]]:
    col = getattr(User, field)
    rows = await session.execute(select(col, User.id).where(col.is_not(None)))
    acc: dict[str, int] = {}
    for code, _ in rows.all():
        acc[code] = acc.get(code, 0) + 1
    return sorted(acc.items(), key=lambda x: x[0])
