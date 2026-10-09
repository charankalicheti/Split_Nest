from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.schemas.expense import ExpenseCreate
from app.schemas.group import GroupCreate
from app.services.expense_service import create_expense
from app.services.group_service import create_group


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_equal_expense_splits_evenly_between_named_participants(db):
    group = create_group(
        db,
        GroupCreate(name="Trip", member_names=["Alex", "Sam", "Jo"]),
    )
    payer = group.members[0]

    expense = create_expense(
        db,
        group.id,
        payer.id,
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("10.00"),
            paid_by=payer.id,
            split_type="equal",
        ),
    )

    assert expense.paid_by == payer.id
    assert [split.member_id for split in expense.splits] == [
        member.id for member in group.members
    ]
    assert [split.amount for split in expense.splits] == [
        Decimal("3.34"),
        Decimal("3.33"),
        Decimal("3.33"),
    ]


def test_custom_split_requires_exact_amounts_and_group_participants(db):
    group = create_group(
        db,
        GroupCreate(name="Trip", member_names=["Alex", "Sam"]),
    )
    alex, sam = group.members

    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("24.00"),
            paid_by=alex.id,
            split_type="custom",
        )

    expense = create_expense(
        db,
        group.id,
        alex.id,
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("24.00"),
            paid_by=alex.id,
            split_type="custom",
            splits=[
                {"member_id": sam.id, "amount": "14.50"},
                {"member_id": alex.id, "amount": "9.50"},
            ],
        ),
    )

    assert {split.member_id: split.amount for split in expense.splits} == {
        alex.id: Decimal("9.50"),
        sam.id: Decimal("14.50"),
    }


def test_expense_requires_a_group_participant_as_payer(db):
    group = create_group(
        db,
        GroupCreate(name="Trip", member_names=["Alex"]),
    )

    with pytest.raises(Exception, match="payer must be a participant"):
        create_expense(
            db,
            group.id,
            999,
            ExpenseCreate(
                description="Dinner",
                amount=Decimal("10.00"),
                paid_by=999,
                split_type="equal",
            ),
        )


def test_expense_amount_rejects_more_than_two_decimal_places():
    with pytest.raises(ValidationError):
        ExpenseCreate(
            description="Dinner",
            amount=Decimal("1.001"),
            paid_by=1,
            split_type="equal",
        )
