import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "reference_id", name="uq_transactions_account_reference"),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint("type IN ('credit', 'debit')", name="ck_transactions_type"),
        Index("ix_transactions_history", "account_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    type: Mapped[str] = mapped_column(String(6), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    account = relationship("Account", back_populates="transactions")
