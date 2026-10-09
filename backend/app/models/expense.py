from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_positive_amount"),
        CheckConstraint(
            "split_type IN ('equal', 'custom')",
            name="ck_expenses_split_type",
        ),
        Index("ix_expenses_group_created_at", "group_id", "created_at"),
        Index("ix_expenses_paid_by", "paid_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    paid_by: Mapped[int] = mapped_column(
        ForeignKey("group_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2, asdecimal=True),
        nullable=False,
    )
    split_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    splits = relationship(
        "ExpenseSplit",
        back_populates="expense",
        cascade="all, delete-orphan",
    )
