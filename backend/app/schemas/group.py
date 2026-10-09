
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


SUPPORTED_CURRENCIES = {
    "AED": "UAE Dirham",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "EUR": "Euro",
    "GBP": "British Pound",
    "INR": "Indian Rupee",
    "NZD": "New Zealand Dollar",
    "SGD": "Singapore Dollar",
    "USD": "US Dollar",
}


def validate_currency(value: str) -> str:
    currency = value.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError("Select a supported currency.")
    return currency


# -----------------------------
# Create Group
# -----------------------------

class GroupCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )
    currency: str = "USD"
    member_names: list[str] = Field(default_factory=lambda: ["Me"], min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be empty.")
        return value

    @field_validator("currency")
    @classmethod
    def validate_group_currency(cls, value: str) -> str:
        return validate_currency(value)

    @field_validator("member_names")
    @classmethod
    def validate_member_names(cls, values: list[str]) -> list[str]:
        names = [name.strip() for name in values]
        if any(not name or len(name) > 100 for name in names):
            raise ValueError("Participant names must contain 1 to 100 characters.")
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("Participant names must be unique within a group.")
        return names


# -----------------------------
# Add a participant
# -----------------------------

class GroupMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Participant name cannot be empty.")
        return value


# -----------------------------
# Participant information
# -----------------------------

class GroupMemberResponse(BaseModel):
    id: int
    name: str
    joined_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# -----------------------------
# Group response
# -----------------------------

class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    currency: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# -----------------------------
# Group details with members
# -----------------------------

class GroupDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None
    currency: str
    created_at: datetime
    members: list[GroupMemberResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True
    )
