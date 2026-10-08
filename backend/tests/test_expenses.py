from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.expense import ExpenseCreate
from app.services.expense_service import (
    ExpenseValidationError,
    allocate_equal_splits,
    resolve_expense_splits,
)


def test_equal_split_distributes_remainder_cents_deterministically():
    splits = allocate_equal_splits(Decimal("10.00"), [9, 3, 5])

    assert splits == [
        (3, Decimal("3.34")),
        (5, Decimal("3.33")),
        (9, Decimal("3.33")),
    ]
    assert sum((amount for _, amount in splits), Decimal("0")) == Decimal("10.00")


def test_equal_split_supports_more_than_four_members():
    splits = allocate_equal_splits(Decimal("100.00"), list(range(1, 101)))

    assert len(splits) == 100
    assert sum((amount for _, amount in splits), Decimal("0")) == Decimal("100.00")


def test_equal_split_rejects_empty_members():
    with pytest.raises(ExpenseValidationError):
        allocate_equal_splits(Decimal("10.00"), [])


def test_custom_split_requires_members_and_unique_member_ids():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("24.00"),
            paid_by_user_id=1,
            split_type="custom",
        )

    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("24.00"),
            paid_by_user_id=1,
            split_type="custom",
            splits=[
                {"user_id": 2, "amount": "12.00"},
                {"user_id": 2, "amount": "12.00"},
            ],
        )


def test_custom_split_amounts_must_match_expense_total():
    expense = ExpenseCreate(
        description="Dinner",
        amount=Decimal("24.00"),
        paid_by_user_id=1,
        split_type="custom",
        splits=[
            {"user_id": 2, "amount": "10.00"},
            {"user_id": 3, "amount": "14.01"},
        ],
    )

    with pytest.raises(ExpenseValidationError, match="add up"):
        resolve_expense_splits(expense, [1, 2, 3])


def test_custom_split_preserves_exact_decimal_allocations():
    expense = ExpenseCreate(
        description="Dinner",
        amount=Decimal("24.00"),
        paid_by_user_id=1,
        split_type="custom",
        splits=[
            {"user_id": 3, "amount": "14.50"},
            {"user_id": 2, "amount": "9.50"},
        ],
    )

    assert resolve_expense_splits(expense, [1, 2, 3]) == [
        (2, Decimal("9.50")),
        (3, Decimal("14.50")),
    ]


def test_custom_split_rejects_non_group_members():
    expense = ExpenseCreate(
        description="Dinner",
        amount=Decimal("24.00"),
        paid_by_user_id=1,
        split_type="custom",
        splits=[{"user_id": 4, "amount": "24.00"}],
    )

    with pytest.raises(ExpenseValidationError, match="belong to this group"):
        resolve_expense_splits(expense, [1, 2, 3])


def test_expense_amount_rejects_more_than_two_decimal_places():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("1.001"),
            paid_by_user_id=1,
        )