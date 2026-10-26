import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_accounts_balance_nonnegative"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    transactions = relationship("Transaction", back_populates="account")
