from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
)
from app.services.expense_service import (
    create_expense,
    delete_expense,
    get_expense,
    get_group_expenses,
    update_expense,
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
):
    return create_expense(
        db=db,
        group_id=group_id,
        paid_by_member_id=expense_data.paid_by,
        expense_data=expense_data,
    )


@router.get(
    "/groups/{group_id}",
    response_model=list[ExpenseResponse],
)
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
):
    return get_group_expenses(
        db=db,
        group_id=group_id,
    )


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
)
def expense_details(
    expense_id: int,
    db: Session = Depends(get_db),
):
    return get_expense(
        db=db,
        expense_id=expense_id,
    )


@router.put(
    "/{expense_id}",
    response_model=ExpenseResponse,
)
def edit_expense(
    expense_id: int,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
):
    return update_expense(
        db=db,
        expense_id=expense_id,
        expense_data=expense_data,
    )


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_expense(
    expense_id: int,
    db: Session = Depends(get_db),
):
    delete_expense(db=db, expense_id=expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)