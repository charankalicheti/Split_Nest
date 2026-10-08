from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseSplitCreate(BaseModel):
    user_id: int
    amount: Decimal = Field(gt=0)


class ExpenseCreate(BaseModel):
    description: str = Field(
        min_length=1,
        max_length=255
    )

    amount: Decimal = Field(gt=0)

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


class ExpenseSplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
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