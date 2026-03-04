from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str] = mapped_column(Text)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    test_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    leading_type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    secondary_type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    secondary_types: Mapped[list[str] | None] = mapped_column(ARRAY(String(1)), nullable=True)
    result_type: Mapped[str | None] = mapped_column(String(1), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_result_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
