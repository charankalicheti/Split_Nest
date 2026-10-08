from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserRegister


def get_user_by_email(
    db: Session,
    email: str
) -> User | None:

    statement = select(User).where(
        User.email == email.lower()
    )

    return db.scalar(statement)


def get_user_by_id(
    db: Session,
    user_id: int
) -> User | None:

    return db.get(User, user_id)


def register_user(
    db: Session,
    user_data: UserRegister
) -> User:

    user_data.validate_passwords()

    email = user_data.email.lower()

    existing_user = get_user_by_email(
        db,
        email
    )

    if existing_user:
        raise ValueError(
            "A user with this email already exists"
        )

    user = User(
        name=user_data.name.strip(),
        email=email,
        password_hash=hash_password(
            user_data.password
        ),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str
) -> User | None:

    user = get_user_by_email(
        db,
        email.lower()
    )

    if not user:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user


def create_user_token(user: User) -> str:
    return create_access_token(user.id)