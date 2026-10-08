
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_member import GroupMember
from app.schemas.group import GroupCreate


# --------------------------------------------------
# Create Group
# --------------------------------------------------

def create_group(
    db: Session,
    group_data: GroupCreate,
    user_id: int
):
    # Create the group
    new_group = Group(
        name=group_data.name,
        description=group_data.description,
        created_by=user_id
    )

    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    # Automatically add the creator as a group member
    creator_member = GroupMember(
        group_id=new_group.id,
        user_id=user_id
    )

    db.add(creator_member)
    db.commit()

    return new_group


# --------------------------------------------------
# Join Group
# --------------------------------------------------

def join_group(
    db: Session,
    group_id: int,
    user_id: int
):
    # Check whether group exists
    group = (
        db.query(Group)
        .filter(Group.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check whether user is already a member
    existing_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )

    # Add user to group
    new_member = GroupMember(
        group_id=group_id,
        user_id=user_id
    )

    db.add(new_member)
    db.commit()

    return group


# --------------------------------------------------
# Get Groups of Logged-in User
# --------------------------------------------------

def get_user_groups(
    db: Session,
    user_id: int
):
    groups = (
        db.query(Group)
        .join(
            GroupMember,
            Group.id == GroupMember.group_id
        )
        .filter(
            GroupMember.user_id == user_id
        )
        .order_by(Group.created_at.desc())
        .all()
    )

    return groups


# --------------------------------------------------
# Get Group Details
# --------------------------------------------------

def get_group_details(
    db: Session,
    group_id: int,
    user_id: int
):
    # Check group exists
    group = (
        db.query(Group)
        .filter(Group.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check whether requesting user is a member
    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )

    return group


# --------------------------------------------------
# Add Member
# --------------------------------------------------

def add_member(
    db: Session,
    group_id: int,
    new_user_id: int,
    requesting_user_id: int
):
    # Check group exists
    group = (
        db.query(Group)
        .filter(Group.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check whether requesting user belongs to group
    requesting_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == requesting_user_id
        )
        .first()
    )

    if not requesting_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )

    # Check whether new user is already a member
    existing_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == new_user_id
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )

    # Add new member
    new_member = GroupMember(
        group_id=group_id,
        user_id=new_user_id
    )

    db.add(new_member)
    db.commit()

    # Return updated group
    db.refresh(group)

    return group
