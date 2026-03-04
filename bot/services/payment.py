from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.manual_review import PaymentManualReview
from bot.models.payment import Payment


async def upsert_payment(
    session: AsyncSession,
    user_id: int,
    provider_payment_id: str,
    status: str,
    payload: dict | None = None,
) -> Payment:
    stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        existing = Payment(
            user_id=user_id,
            provider="prodamus",
            provider_payment_id=provider_payment_id,
            status=status,
            payload=payload,
        )
        session.add(existing)
    else:
        existing.status = status
        existing.payload = payload
        existing.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(existing)
    return existing


async def create_manual_review(session: AsyncSession, user_id: int, payment_id: int | None = None) -> PaymentManualReview:
    stmt = select(PaymentManualReview).where(
        PaymentManualReview.user_id == user_id, PaymentManualReview.status == "open"
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    review = PaymentManualReview(user_id=user_id, payment_id=payment_id, status="open")
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def get_open_reviews(session: AsyncSession) -> list[PaymentManualReview]:
    stmt = (
        select(PaymentManualReview)
        .where(PaymentManualReview.status == "open")
        .order_by(PaymentManualReview.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_open_reviews(session: AsyncSession) -> int:
    stmt = select(func.count(PaymentManualReview.id)).where(PaymentManualReview.status == "open")
    return int((await session.execute(stmt)).scalar_one())


async def get_open_reviews_page(
    session: AsyncSession, page: int, page_size: int = 10
) -> tuple[list[PaymentManualReview], int]:
    total = await count_open_reviews(session)
    offset = max(0, page) * page_size
    stmt = (
        select(PaymentManualReview)
        .where(PaymentManualReview.status == "open")
        .order_by(PaymentManualReview.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list((await session.execute(stmt)).scalars().all())
    return items, total


async def resolve_review(session: AsyncSession, review_id: int, admin_id: int, approved: bool) -> PaymentManualReview | None:
    review = await session.get(PaymentManualReview, review_id)
    if not review or review.status != "open":
        return None
    review.status = "approved" if approved else "rejected"
    review.resolved_at = datetime.now(timezone.utc)
    review.resolved_by = admin_id
    await session.commit()
    await session.refresh(review)
    return review


async def recent_payments(session: AsyncSession, limit: int = 10) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
