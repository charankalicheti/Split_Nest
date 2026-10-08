"""
Database model for recorded settlements between group members.

A settlement records a completed repayment.
Creating this record does not transfer money through a bank or UPI.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_settlements_positive_amount",
        ),
        CheckConstraint(
            "payer_id <> payee_id",
            name="ck_settlements_different_participants",
        ),
        UniqueConstraint(
            "group_id",
            "created_by",
            "idempotency_key",
            name="uq_settlements_submission",
        ),
        Index(
            "ix_settlements_group_created_at",
            "group_id",
            "created_at",
        ),
        Index(
            "ix_settlements_group_payer",
            "group_id",
            "payer_id",
        ),
        Index(
            "ix_settlements_group_payee",
            "group_id",
            "payee_id",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    group_id = Column(
        Integer,
        ForeignKey("groups.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Member who sends the repayment.
    payer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Member who receives the repayment.
    payee_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Exact decimal storage for currencies such as INR and USD.
    # Example: Decimal("1000.50")
    amount = Column(
        Numeric(precision=14, scale=2, asdecimal=True),
        nullable=False,
    )

    # The service copies this from the group's currency.
    currency = Column(
        String(3),
        nullable=False,
    )

    note = Column(
        String(500),
        nullable=True,
    )

    # Authenticated user who recorded this repayment.
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # A unique submission identifier supplied with the request.
    # Reuse the same key when retrying the same payment submission.
    idempotency_key = Column(
        String(36),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Settlement("
            f"id={self.id}, "
            f"group_id={self.group_id}, "
            f"payer_id={self.payer_id}, "
            f"payee_id={self.payee_id}, "
            f"amount={self.amount}, "
            f"currency={self.currency}"
            f")>"
        )