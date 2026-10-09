"""API endpoints for group balances and repayment suggestions."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.balance_service import (
    get_group_balances,
    get_settlement_suggestions,
)


router = APIRouter(
    prefix="/groups/{group_id}/balances",
    tags=["Balances"],
)


# Response schemas live here to stay within your six assigned files.
# They can later be moved into app/schemas/balance.py.

class MemberBalanceResponse(BaseModel):
    member_id: int
    name: str
    total_paid: Decimal
    total_share: Decimal
    total_settlements_sent: Decimal
    total_settlements_received: Decimal
    net_balance: Decimal
    position: Literal["receives", "owes", "settled"]


class GroupBalancesResponse(BaseModel):
    group_id: int
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    members: list[MemberBalanceResponse]


class RepaymentSuggestionResponse(BaseModel):
    payer_id: int
    payee_id: int
    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )


class SettlementSuggestionsResponse(BaseModel):
    group_id: int
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    suggestions: list[RepaymentSuggestionResponse]


@router.get(
    "",
    response_model=GroupBalancesResponse,
    summary="Get group member balances",
)
def read_group_balances(
    group_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Return each member's balance.

    Positive balance: member should receive money.
    Negative balance: member owes money.
    Zero balance: member is settled.
    """
    return get_group_balances(
        db=db,
        group_id=group_id,
    )


@router.get(
    "/suggestions",
    response_model=SettlementSuggestionsResponse,
    summary="Get suggested repayments",
)
def read_settlement_suggestions(
    group_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return suggested payments without creating settlement records."""
    return get_settlement_suggestions(
        db=db,
        group_id=group_id,
    )