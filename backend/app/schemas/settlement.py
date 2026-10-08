"""Request and response schemas for group settlements."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# Matches Numeric(14, 2) in the settlement database model.
SettlementAmount = Annotated[
    Decimal,
    Field(
        gt=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    ),
]


class SettlementCreate(BaseModel):
    """Data submitted when recording a completed repayment."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    payer_id: int = Field(
        gt=0,
        description="User ID of the member sending money.",
    )

    payee_id: int = Field(
        gt=0,
        description="User ID of the member receiving money.",
    )

    amount: SettlementAmount

    # Required so retrying a submission does not create another payment.
    idempotency_key: UUID

    note: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Store an empty note as None."""
        if value is None:
            return None

        return value.strip() or None

    @model_validator(mode="after")
    def validate_participants(self) -> "SettlementCreate":
        """A member cannot settle a payment with themselves."""
        if self.payer_id == self.payee_id:
            raise ValueError("Payer and payee must be different members.")

        return self


class SettlementResponse(BaseModel):
    """Settlement details returned after saving or listing payments."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    payer_id: int
    payee_id: int
    amount: SettlementAmount
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    note: str | None
    created_by: int
    idempotency_key: UUID
    created_at: datetime