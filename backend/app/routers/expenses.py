from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
)
from app.services.expense_service import (
    create_expense,
    get_expense,
    get_group_expenses,
)


router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"],
)


@router.post(
    "/groups/{group_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_expense(
    group_id: int,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_expense(
        db=db,
        group_id=group_id,
        current_user_id=current_user.id,
        expense_data=expense_data,
    )


@router.get(
    "/groups/{group_id}",
    response_model=list[ExpenseResponse],
)
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_group_expenses(
        db=db,
        group_id=group_id,
        current_user_id=current_user.id,
    )


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
)
def expense_details(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_expense(
        db=db,
        expense_id=expense_id,
        current_user_id=current_user.id,
    )