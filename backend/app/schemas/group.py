
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


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


# -----------------------------
# Join Group
# -----------------------------

class GroupJoin(BaseModel):
    group_id: int


# -----------------------------
# User information
# Used when returning members
# -----------------------------

class GroupMemberResponse(BaseModel):
    user_id: int
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
    created_by: int
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
    created_by: int
    created_at: datetime
    members: list[GroupMemberResponse] = []

    model_config = ConfigDict(
        from_attributes=True
    )
