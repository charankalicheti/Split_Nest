from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.group_member import GroupMember
from app.schemas.expense import ExpenseCreate
from app.utils.calculations import (
    calculate_equal_split,
    validate_custom_split,
)


def create_expense(
    db: Session,
    group_id: int,
    current_user_id: int,
    expense_data: ExpenseCreate,
) -> Expense:

    # Check whether the current user belongs to the group
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user_id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )

    # Validate split data
    if expense_data.split_type == "equal":

        if expense_data.splits:
            raise HTTPException(
                status_code=400,
                detail="Splits should not be provided for equal split.",
            )

        # Get all group members
        members = db.scalars(
            select(GroupMember).where(
                GroupMember.group_id == group_id
            )
        ).all()

        if not members:
            raise HTTPException(
                status_code=400,
                detail="Group has no members.",
            )

        user_ids = [
            member.user_id
            for member in members
        ]

        calculated_splits = calculate_equal_split(
            expense_data.amount,
            user_ids,
        )

    else:

        if not expense_data.splits:
            raise HTTPException(
                status_code=400,
                detail="Custom split requires splits.",
            )

        calculated_splits = {
            split.user_id: split.amount
            for split in expense_data.splits
        }

        # Check that all split users belong to group
        members = db.scalars(
            select(GroupMember).where(
                GroupMember.group_id == group_id
            )
        ).all()

        member_ids = {
            member.user_id
            for member in members
        }

        non_members = (
            set(calculated_splits.keys())
            - member_ids
        )

        if non_members:
            raise HTTPException(
                status_code=400,
                detail="One or more users are not members of this group.",
            )

        try:
            validate_custom_split(
                expense_data.amount,
                calculated_splits,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

    # Create expense
    expense = Expense(
        group_id=group_id,
        paid_by=current_user_id,
        description=expense_data.description,
        amount=expense_data.amount,
        split_type=expense_data.split_type,
    )

    db.add(expense)
    db.flush()

    # Create split records
    for user_id, amount in calculated_splits.items():

        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=user_id,
            amount=amount,
        )

        db.add(split)

    db.commit()
    db.refresh(expense)

    return expense


def get_group_expenses(
    db: Session,
    group_id: int,
    current_user_id: int,
) -> list[Expense]:

    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user_id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )

    expenses = db.scalars(
        select(Expense)
        .where(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc())
    ).all()

    return list(expenses)


def get_expense(
    db: Session,
    expense_id: int,
    current_user_id: int,
) -> Expense:

    expense = db.scalar(
        select(Expense).where(
            Expense.id == expense_id
        )
    )

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found.",
        )

    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == expense.group_id,
            GroupMember.user_id == current_user_id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )

    return expense