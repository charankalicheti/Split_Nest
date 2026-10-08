"""Business logic for recording and listing group settlements."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.settlement import Settlement
from app.schemas.settlement import SettlementCreate


def _require_group_member(
    db: Session,
    group_id: int,
    user_id: int,
) -> Group:
    """Check that the group exists and the user belongs to it."""
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )

    membership = db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    ).first()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to this group.",
        )

    return group


def _find_existing_settlement(
    db: Session,
    group_id: int,
    created_by: int,
    idempotency_key: str,
) -> Settlement | None:
    """Find a previously saved submission."""
    return db.scalars(
        select(Settlement).where(
            Settlement.group_id == group_id,
            Settlement.created_by == created_by,
            Settlement.idempotency_key == idempotency_key,
        )
    ).one_or_none()


def _validate_retry(
    existing: Settlement,
    payload: SettlementCreate,
) -> Settlement:
    """Return the original payment only when retry details match."""
    same_payment = (
        existing.payer_id == payload.payer_id
        and existing.payee_id == payload.payee_id
        and existing.amount == payload.amount
        and existing.note == payload.note
    )

    if not same_payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This idempotency key was already used "
                "for a different payment."
            ),
        )

    return existing


def create_settlement(
    db: Session,
    group_id: int,
    payload: SettlementCreate,
    current_user_id: int,
) -> Settlement:
    """
    Record a completed repayment.

    This function commits its database transaction.
    Use a request-scoped session without unrelated pending changes.
    """
    group = _require_group_member(
        db=db,
        group_id=group_id,
        user_id=current_user_id,
    )

    if payload.payer_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only record payments that you made.",
        )

    # The schema already validates these conditions.
    # Check again here to protect the business logic.
    if payload.payer_id == payload.payee_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payer and payee must be different members.",
        )

    amount = payload.amount

    if (
        not isinstance(amount, Decimal)
        or not amount.is_finite()
        or amount <= Decimal("0")
        or amount != amount.quantize(Decimal("0.01"))
        or amount >= Decimal("1000000000000")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount must be positive and fit a two-decimal currency.",
        )

    submission_key = str(payload.idempotency_key)

    existing = _find_existing_settlement(
        db=db,
        group_id=group_id,
        created_by=current_user_id,
        idempotency_key=submission_key,
    )

    if existing is not None:
        return _validate_retry(existing, payload)

    participant_ids = set(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id.in_(
                    [payload.payer_id, payload.payee_id]
                ),
            )
        ).all()
    )

    if participant_ids != {payload.payer_id, payload.payee_id}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both payment participants must belong to this group.",
        )

    currency = group.currency

    # This version supports the two-decimal currencies discussed earlier.
    if currency not in {"INR", "USD"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Settlement currency must be INR or USD.",
        )

    settlement = Settlement(
        group_id=group_id,
        payer_id=payload.payer_id,
        payee_id=payload.payee_id,
        amount=amount,
        currency=currency,
        note=payload.note,
        created_by=current_user_id,
        idempotency_key=submission_key,
    )

    try:
        db.add(settlement)
        db.commit()

    except IntegrityError as exc:
        # Two simultaneous retries can both pass the earlier lookup.
        # The database unique constraint permits only one saved record.
        db.rollback()

        existing = _find_existing_settlement(
            db=db,
            group_id=group_id,
            created_by=current_user_id,
            idempotency_key=submission_key,
        )

        if existing is not None:
            return _validate_retry(existing, payload)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The payment could not be saved because its "
                "related records changed or violated a database constraint."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise

    db.refresh(settlement)
    return settlement


def list_group_settlements(
    db: Session,
    group_id: int,
    current_user_id: int,
    offset: int = 0,
    limit: int = 50,
) -> list[Settlement]:
    """Return settlement history, newest first."""
    _require_group_member(
        db=db,
        group_id=group_id,
        user_id=current_user_id,
    )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offset cannot be negative.",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limit must be between 1 and 100.",
        )

    return list(
        db.scalars(
            select(Settlement)
            .where(Settlement.group_id == group_id)
            .order_by(
                Settlement.created_at.desc(),
                Settlement.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )