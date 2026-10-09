from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pydantic import ValidationError
import pytest

from app.core.database import Base
from app.core.config import Settings
from app.models import Expense, ExpenseSplit, Group, GroupMember, Settlement
from app.schemas.group import GroupCreate, SUPPORTED_CURRENCIES
from app.services.group_service import create_group


def test_schema_has_no_account_tables_or_user_references():
    assert set(Base.metadata.tables) == {
        "groups",
        "group_members",
        "expenses",
        "expense_splits",
        "settlements",
    }
    assert "users" not in Base.metadata.tables
    assert "created_by" not in Group.__table__.c
    assert "name" in GroupMember.__table__.c
    assert "user_id" not in GroupMember.__table__.c
    assert next(iter(Expense.__table__.c.paid_by.foreign_keys)).target_fullname == "group_members.id"
    assert next(iter(ExpenseSplit.__table__.c.member_id.foreign_keys)).target_fullname == "group_members.id"
    assert all(
        foreign_key.target_fullname != "users.id"
        for table in Base.metadata.tables.values()
        for column in table.columns
        for foreign_key in column.foreign_keys
    )
    assert Settlement.__table__.c.payer_id.foreign_keys


@pytest.mark.parametrize("currency", SUPPORTED_CURRENCIES)
def test_group_accepts_supported_currencies(currency):
    assert GroupCreate(name="Trip", currency=currency).currency == currency


def test_group_normalizes_lowercase_currency_and_participant_names():
    group = GroupCreate(
        name=" Trip ",
        currency="eur",
        member_names=[" Alex ", "Sam"],
    )

    assert group.name == "Trip"
    assert group.currency == "EUR"
    assert group.member_names == ["Alex", "Sam"]


def test_group_rejects_unsupported_currency_and_duplicate_participants():
    with pytest.raises(ValidationError, match="supported currency"):
        GroupCreate(name="Trip", currency="JPY")

    with pytest.raises(ValidationError, match="unique"):
        GroupCreate(name="Trip", member_names=["Sam", " sam "])


def test_group_creation_saves_named_participants_and_currency():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            group = create_group(
                db,
                GroupCreate(
                    name="Travel",
                    currency="EUR",
                    member_names=["Alex", "Sam"],
                ),
            )
            saved_group = db.get(Group, group.id)
            participants = db.scalars(
                select(GroupMember)
                .where(GroupMember.group_id == group.id)
                .order_by(GroupMember.id)
            ).all()

            assert saved_group is not None
            assert saved_group.currency == "EUR"
            assert [participant.name for participant in participants] == ["Alex", "Sam"]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_localhost_frontend_cors_accepts_both_loopback_names():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite://",
        CORS_ORIGINS="http://localhost:5173",
    )

    assert settings.cors_origins_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
