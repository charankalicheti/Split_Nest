from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_group_creation_and_expenses_need_no_account(client):
    response = client.post(
        "/api/groups",
        json={
            "name": "Weekend trip",
            "currency": "USD",
            "member_names": ["Alex", "Sam"],
        },
    )

    assert response.status_code == 201
    group = response.json()
    assert [member["name"] for member in group["members"]] == ["Alex", "Sam"]

    participants = group["members"]
    expense_response = client.post(
        f"/api/expenses/groups/{group['id']}",
        json={
            "description": "Dinner",
            "amount": "24.00",
            "paid_by": participants[0]["id"],
            "split_type": "equal",
        },
    )

    assert expense_response.status_code == 201
    assert len(expense_response.json()["splits"]) == 2

    balances = client.get(f"/api/groups/{group['id']}/balances").json()
    assert [Decimal(member["net_balance"]) for member in balances["members"]] == [
        Decimal("12.00"),
        Decimal("-12.00"),
    ]


def test_groups_are_listed_and_participants_can_be_added_without_login(client):
    group = client.post(
        "/api/groups",
        json={"name": "Housemates", "member_names": ["Alex"]},
    ).json()

    added = client.post(
        f"/api/groups/{group['id']}/members",
        json={"name": "Sam"},
    )

    assert added.status_code == 201
    assert [member["name"] for member in added.json()["members"]] == [
        "Alex",
        "Sam",
    ]
    assert client.get("/api/groups").json()[0]["name"] == "Housemates"
    assert client.post("/api/auth/register", json={}).status_code == 404


def test_settlement_suggestions_show_who_pays_whom(client):
    group = client.post(
        "/api/groups",
        json={
            "name": "Trip",
            "currency": "INR",
            "member_names": ["Charan", "Gopi", "Pavan", "Vinay"],
        },
    ).json()
    group_id = group["id"]

    for member, amount in zip(group["members"], ["5000.00", "4000.00", "5000.00", "6000.00"]):
        response = client.post(
            f"/api/expenses/groups/{group_id}",
            json={
                "description": "Trip expense",
                "amount": amount,
                "paid_by": member["id"],
                "split_type": "equal",
            },
        )
        assert response.status_code == 201

    suggestions = client.get(
        f"/api/groups/{group_id}/balances/suggestions",
    )

    assert suggestions.status_code == 200
    assert suggestions.json()["suggestions"] == [
        {
            "payer_id": group["members"][1]["id"],
            "payee_id": group["members"][3]["id"],
            "amount": "1000.00",
        },
    ]


def test_group_can_be_deleted_with_its_expenses_and_settlements(client):
    group = client.post(
        "/api/groups",
        json={"name": "Old trip", "member_names": ["Alex", "Sam"]},
    ).json()
    expense = client.post(
        f"/api/expenses/groups/{group['id']}",
        json={
            "description": "Dinner",
            "amount": "20.00",
            "paid_by": group["members"][0]["id"],
            "split_type": "equal",
        },
    )
    assert expense.status_code == 201
    settlement = client.post(
        f"/api/groups/{group['id']}/settlements",
        json={
            "payer_id": group["members"][0]["id"],
            "payee_id": group["members"][1]["id"],
            "amount": "10.00",
            "idempotency_key": "1095f555-ae89-4cf0-9915-bfe4be7a3e10",
        },
    )
    assert settlement.status_code == 200

    deleted = client.delete(f"/api/groups/{group['id']}")

    assert deleted.status_code == 204
    assert client.get("/api/groups").json() == []
    assert client.get(f"/api/groups/{group['id']}").status_code == 404
    assert client.get(f"/api/expenses/groups/{group['id']}").status_code == 404
    assert client.get(f"/api/groups/{group['id']}/settlements").status_code == 404
    assert client.delete(f"/api/groups/{group['id']}").status_code == 404


def test_expense_can_be_edited_and_deleted(client):
    group = client.post(
        "/api/groups",
        json={"name": "Housemates", "member_names": ["Alex", "Sam"]},
    ).json()
    alex, sam = group["members"]
    expense = client.post(
        f"/api/expenses/groups/{group['id']}",
        json={
            "description": "Dinner",
            "amount": "20.00",
            "paid_by": alex["id"],
            "split_type": "equal",
        },
    ).json()

    updated = client.put(
        f"/api/expenses/{expense['id']}",
        json={
            "description": "Updated dinner",
            "amount": "30.00",
            "paid_by": sam["id"],
            "split_type": "equal",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated dinner"
    assert updated.json()["amount"] == "30.00"
    assert updated.json()["paid_by"] == sam["id"]
    assert [split["amount"] for split in updated.json()["splits"]] == [
        "15.00",
        "15.00",
    ]
    balances = client.get(f"/api/groups/{group['id']}/balances").json()
    assert [member["net_balance"] for member in balances["members"]] == [
        "-15.00",
        "15.00",
    ]

    custom_update = client.put(
        f"/api/expenses/{expense['id']}",
        json={
            "description": "Updated dinner",
            "amount": "20.00",
            "paid_by": sam["id"],
            "split_type": "custom",
            "splits": [
                {"member_id": alex["id"], "amount": "12.00"},
                {"member_id": sam["id"], "amount": "8.00"},
            ],
        },
    )
    assert custom_update.status_code == 200
    assert custom_update.json()["split_type"] == "custom"
    assert [split["amount"] for split in custom_update.json()["splits"]] == [
        "12.00",
        "8.00",
    ]

    deleted = client.delete(f"/api/expenses/{expense['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/api/expenses/groups/{group['id']}").json() == []
    balances_after_delete = client.get(f"/api/groups/{group['id']}/balances").json()
    assert [member["net_balance"] for member in balances_after_delete["members"]] == [
        "0.00",
        "0.00",
    ]
    assert client.delete(f"/api/expenses/{expense['id']}").status_code == 404
