from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.settlement import Settlement
from app.schemas.group import GroupCreate


def create_group(db: Session, group_data: GroupCreate) -> Group:
    group = Group(
        name=group_data.name.strip(),
        description=group_data.description,
        currency=group_data.currency,
    )
    group.members = [
        GroupMember(name=name)
        for name in group_data.member_names
    ]
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def get_groups(db: Session) -> list[Group]:
    return list(
        db.scalars(select(Group).order_by(Group.created_at.desc())).all()
    )


def get_group_details(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )
    return group


def add_member(db: Session, group_id: int, name: str) -> Group:
    group = get_group_details(db, group_id)
    existing_names = db.scalars(
        select(GroupMember.name).where(GroupMember.group_id == group_id)
    ).all()
    if any(existing_name.casefold() == name.casefold() for existing_name in existing_names):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A participant with this name is already in the group.",
        )

    db.add(GroupMember(group_id=group_id, name=name))
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: int) -> None:
    group = get_group_details(db, group_id)

    settlements = db.scalars(
        select(Settlement).where(Settlement.group_id == group_id)
    ).all()
    expenses = db.scalars(
        select(Expense).where(Expense.group_id == group_id)
    ).all()

    for settlement in settlements:
        db.delete(settlement)
    for expense in expenses:
        db.delete(expense)

    db.flush()
    db.delete(group)
    db.commit()
