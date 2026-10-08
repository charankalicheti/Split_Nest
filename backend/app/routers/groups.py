
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.group import (
    GroupCreate,
    GroupJoin,
    GroupResponse,
    GroupDetailResponse,
)
from app.services.group_service import (
    create_group,
    join_group,
    get_user_groups,
    get_group_details,
    add_member,
)

# Change this import only if Charan used a different path/name
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)


# --------------------------------------------------
# Create Group
# POST /groups
# --------------------------------------------------

@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED
)
def create_new_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return create_group(
        db=db,
        group_data=group_data,
        user_id=current_user.id
    )


# --------------------------------------------------
# Join Group
# POST /groups/join
# --------------------------------------------------

@router.post(
    "/join",
    response_model=GroupResponse
)
def join_existing_group(
    group_data: GroupJoin,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return join_group(
        db=db,
        group_id=group_data.group_id,
        user_id=current_user.id
    )


# --------------------------------------------------
# Get My Groups
# GET /groups
# --------------------------------------------------

@router.get(
    "",
    response_model=list[GroupResponse]
)
def get_my_groups(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_user_groups(
        db=db,
        user_id=current_user.id
    )


# --------------------------------------------------
# Get Group Details
# GET /groups/{group_id}
# --------------------------------------------------

@router.get(
    "/{group_id}",
    response_model=GroupDetailResponse
)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_group_details(
        db=db,
        group_id=group_id,
        user_id=current_user.id
    )


# --------------------------------------------------
# Add Member
# POST /groups/{group_id}/members/{user_id}
# --------------------------------------------------

@router.post(
    "/{group_id}/members/{user_id}",
    response_model=GroupDetailResponse
)
def add_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return add_member(
        db=db,
        group_id=group_id,
        new_user_id=user_id,
        requesting_user_id=current_user.id
    )
