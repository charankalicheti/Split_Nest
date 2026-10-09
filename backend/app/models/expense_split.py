from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_splits_positive_amount"),
        UniqueConstraint(
            "expense_id",
            "member_id",
            name="uq_expense_split_member",
        ),
        Index("ix_expense_splits_member_id", "member_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("group_members.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2, asdecimal=True),
        nullable=False,
    )

    expense = relationship("Expense", back_populates="splits")
