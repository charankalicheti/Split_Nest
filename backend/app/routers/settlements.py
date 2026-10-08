"""API endpoints for recording and listing group settlements."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.settlement import (
    SettlementCreate,
    SettlementResponse,
)
from app.services.settlement_service import (
    create_settlement,
    list_group_settlements,
)


router = APIRouter(
    prefix="/groups/{group_id}/settlements",
    tags=["Settlements"],
)


@router.post(
    "",
    response_model=SettlementResponse,
    summary="Record a completed repayment",
)
def record_settlement(
    group_id: Annotated[int, Path(gt=0)],
    payload: SettlementCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Record a payment made by the authenticated user.

    Reuse the same idempotency key when retrying the same submission.
    An identical retry returns the original settlement.
    """
    return create_settlement(
        db=db,
        group_id=group_id,
        payload=payload,
        current_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[SettlementResponse],
    summary="Get group settlement history",
)
def read_settlements(
    group_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Return recorded payments, newest first."""
    return list_group_settlements(
        db=db,
        group_id=group_id,
        current_user_id=current_user.id,
        offset=offset,
        limit=limit,
    )