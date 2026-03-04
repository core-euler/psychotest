from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(Text, default="prodamus")
    provider_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    status: Mapped[str] = mapped_column(Text, default="created")
    amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
