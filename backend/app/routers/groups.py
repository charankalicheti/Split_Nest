from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.group import (
    GroupCreate,
    GroupDetailResponse,
    GroupMemberCreate,
    GroupResponse,
)
from app.services.group_service import (
    add_member,
    create_group,
    delete_group,
    get_group_details,
    get_groups,
)


router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "",
    response_model=GroupDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
):
    return create_group(db=db, group_data=group_data)


@router.get("", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    return get_groups(db=db)


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
):
    return get_group_details(db=db, group_id=group_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_group(
    group_id: int,
    db: Session = Depends(get_db),
):
    delete_group(db=db, group_id=group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{group_id}/members",
    response_model=GroupDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_group_member(
    group_id: int,
    member_data: GroupMemberCreate,
    db: Session = Depends(get_db),
):
    return add_member(
        db=db,
        group_id=group_id,
        name=member_data.name,
    )
