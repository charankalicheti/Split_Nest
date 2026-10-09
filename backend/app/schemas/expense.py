from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExpenseSplitCreate(BaseModel):
    member_id: int
    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )


class ExpenseCreate(BaseModel):
    description: str = Field(
        min_length=1,
        max_length=255
    )

    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )
    paid_by: int = Field(gt=0)

    split_type: str

    splits: list[ExpenseSplitCreate] | None = None

    @field_validator("split_type")
    @classmethod
    def validate_split_type(cls, value: str) -> str:

        value = value.lower()

        if value not in {"equal", "custom"}:
            raise ValueError(
                "split_type must be 'equal' or 'custom'"
            )

        return value

    @model_validator(mode="after")
    def validate_splits(self) -> "ExpenseCreate":
        if self.split_type == "custom" and not self.splits:
            raise ValueError("Custom split requires splits.")
        if self.split_type == "equal" and self.splits:
            raise ValueError("Equal split does not accept explicit splits.")
        return self


class ExpenseSplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    amount: Decimal


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    paid_by: int
    description: str
    amount: Decimal
    split_type: str
    created_at: datetime
    splits: list[ExpenseSplitResponse]