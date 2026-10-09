from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.group import Group
from app.models.group_member import GroupMember
from app.schemas.expense import ExpenseCreate
from app.utils.calculations import (
    calculate_equal_split,
    validate_custom_split,
)


def _get_group_members(db: Session, group_id: int) -> list[GroupMember]:
    if db.get(Group, group_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )
    return list(
        db.scalars(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.id)
        ).all()
    )


def _calculate_splits(
    members: list[GroupMember],
    paid_by_member_id: int,
    expense_data: ExpenseCreate,
) -> dict[int, Decimal]:
    member_ids = {member.id for member in members}

    if paid_by_member_id not in member_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The payer must be a participant in this group.",
        )

    if expense_data.split_type == "equal":
        if expense_data.splits:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Splits should not be provided for equal split.",
            )
        try:
            return calculate_equal_split(
                expense_data.amount,
                sorted(member_ids),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    if not expense_data.splits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom split requires splits.",
        )

    split_amounts = {
        split.member_id: split.amount
        for split in expense_data.splits
    }
    if set(split_amounts) - member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more participants are not in this group.",
        )
    try:
        validate_custom_split(expense_data.amount, split_amounts)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return split_amounts


def _replace_expense_splits(
    db: Session,
    expense_id: int,
    calculated_splits: dict[int, Decimal],
) -> None:
    existing_splits = db.scalars(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
    ).all()
    for split in existing_splits:
        db.delete(split)
    db.flush()

    db.add_all(
        ExpenseSplit(
            expense_id=expense_id,
            member_id=member_id,
            amount=amount,
        )
        for member_id, amount in calculated_splits.items()
    )


def create_expense(
    db: Session,
    group_id: int,
    paid_by_member_id: int,
    expense_data: ExpenseCreate,
) -> Expense:
    members = _get_group_members(db, group_id)
    calculated_splits = _calculate_splits(
        members,
        paid_by_member_id,
        expense_data,
    )

    expense = Expense(
        group_id=group_id,
        paid_by=paid_by_member_id,
        description=expense_data.description,
        amount=expense_data.amount,
        split_type=expense_data.split_type,
    )
    db.add(expense)
    db.flush()

    db.add_all(
        ExpenseSplit(
            expense_id=expense.id,
            member_id=member_id,
            amount=amount,
        )
        for member_id, amount in calculated_splits.items()
    )
    db.commit()
    db.refresh(expense)
    return expense


def update_expense(
    db: Session,
    expense_id: int,
    expense_data: ExpenseCreate,
) -> Expense:
    expense = get_expense(db, expense_id)
    members = _get_group_members(db, expense.group_id)
    calculated_splits = _calculate_splits(
        members,
        expense_data.paid_by,
        expense_data,
    )

    expense.description = expense_data.description
    expense.amount = expense_data.amount
    expense.paid_by = expense_data.paid_by
    expense.split_type = expense_data.split_type
    _replace_expense_splits(db, expense.id, calculated_splits)

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense_id: int) -> None:
    expense = get_expense(db, expense_id)
    existing_splits = db.scalars(
        select(ExpenseSplit).where(ExpenseSplit.expense_id == expense_id)
    ).all()
    for split in existing_splits:
        db.delete(split)
    db.flush()
    db.delete(expense)
    db.commit()


def get_group_expenses(db: Session, group_id: int) -> list[Expense]:
    _get_group_members(db, group_id)
    return list(
        db.scalars(
            select(Expense)
            .where(Expense.group_id == group_id)
            .order_by(Expense.created_at.desc())
        ).all()
    )


def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found.",
        )
    return expense
