
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    group_id = Column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationship with Group
    group = relationship(
        "Group",
        back_populates="members"
    )

    # Relationship with User
    user = relationship(
        "User",
        foreign_keys=[user_id]
    )

    # Same user cannot join the same group twice
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "user_id",
            name="uq_group_member"
        ),
    )
