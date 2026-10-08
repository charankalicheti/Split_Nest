"""Calculate group balances and suggest repayments."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.expense_split import ExpenseSplit
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.settlement import Settlement


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _as_money(value: Decimal | None) -> Decimal:
    """Require exact two-decimal money values."""
    if value is None:
        return ZERO

    if not isinstance(value, Decimal):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Money fields must use decimal database types.",
        )

    if not value.is_finite() or value != value.quantize(CENT):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored amounts contain invalid currency precision.",
        )

    return value.quantize(CENT)


def _get_authorized_group(
    db: Session,
    group_id: int,
    current_user_id: int,
) -> Group:
    """Only members can access a group's financial information."""
    group = db.get(Group, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )

    membership = db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user_id,
        )
    ).first()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to this group to view its balances.",
        )

    return group


def get_group_balances(
    db: Session,
    group_id: int,
    current_user_id: int,
) -> dict:
    """
    Return each member's financial position.

    Positive net balance: member should receive money.
    Negative net balance: member owes money.

    net = expenses paid - personal shares
          + settlements sent - settlements received
    """
    group = _get_authorized_group(db, group_id, current_user_id)

    member_ids = db.scalars(
        select(GroupMember.user_id)
        .where(GroupMember.group_id == group_id)
        .distinct()
        .order_by(GroupMember.user_id)
    ).all()

    balances = {
        user_id: {
            "user_id": user_id,
            "total_paid": ZERO,
            "total_share": ZERO,
            "total_settlements_sent": ZERO,
            "total_settlements_received": ZERO,
        }
        for user_id in member_ids
    }

    # Sum expenses paid by each member.
    expense_totals = db.execute(
        select(
            Expense.paid_by,
            func.sum(Expense.amount),
        )
        .where(Expense.group_id == group_id)
        .group_by(Expense.paid_by)
    ).all()

    # Join through Expense because each split belongs to an expense.
    share_totals = db.execute(
        select(
            ExpenseSplit.user_id,
            func.sum(ExpenseSplit.amount),
        )
        .join(
            Expense,
            Expense.id == ExpenseSplit.expense_id,
        )
        .where(Expense.group_id == group_id)
        .group_by(ExpenseSplit.user_id)
    ).all()

    sent_totals = db.execute(
        select(
            Settlement.payer_id,
            func.sum(Settlement.amount),
        )
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.payer_id)
    ).all()

    received_totals = db.execute(
        select(
            Settlement.payee_id,
            func.sum(Settlement.amount),
        )
        .where(Settlement.group_id == group_id)
        .group_by(Settlement.payee_id)
    ).all()

    def assign_totals(rows, field: str) -> None:
        for user_id, amount in rows:
            if user_id not in balances:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "Financial records reference a user "
                        "outside the group membership records."
                    ),
                )

            balances[user_id][field] = _as_money(amount)

    assign_totals(expense_totals, "total_paid")
    assign_totals(share_totals, "total_share")
    assign_totals(sent_totals, "total_settlements_sent")
    assign_totals(received_totals, "total_settlements_received")

    members = []

    for member in balances.values():
        net_balance = (
            member["total_paid"]
            - member["total_share"]
            + member["total_settlements_sent"]
            - member["total_settlements_received"]
        )

        member["net_balance"] = _as_money(net_balance)

        if net_balance > ZERO:
            member["position"] = "receives"
        elif net_balance < ZERO:
            member["position"] = "owes"
        else:
            member["position"] = "settled"

        members.append(member)

    # Expense shares must account for the entire expense amount.
    total_paid = sum(
        (member["total_paid"] for member in members),
        ZERO,
    )

    total_share = sum(
        (member["total_share"] for member in members),
        ZERO,
    )

    if total_paid != total_share:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Expense totals and allocated shares do not match.",
        )

    net_total = sum(
        (member["net_balance"] for member in members),
        ZERO,
    )

    if net_total != ZERO:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Group balances are inconsistent.",
        )

    return {
        "group_id": group.id,
        "currency": group.currency,
        "members": members,
    }


def get_settlement_suggestions(
    db: Session,
    group_id: int,
    current_user_id: int,
) -> dict:
    """
    Match members who owe money with members who should receive it.

    Suggestions are calculated only; no settlement records are created.
    This greedy method produces valid repayments but does not guarantee
    the smallest possible number of payments.
    """
    balance_result = get_group_balances(
        db=db,
        group_id=group_id,
        current_user_id=current_user_id,
    )

    debtors = []
    creditors = []

    for member in balance_result["members"]:
        net_balance = member["net_balance"]

        if net_balance < ZERO:
            debtors.append(
                {
                    "user_id": member["user_id"],
                    "remaining": -net_balance,
                }
            )
        elif net_balance > ZERO:
            creditors.append(
                {
                    "user_id": member["user_id"],
                    "remaining": net_balance,
                }
            )

    # Largest amounts first, with user ID as a stable tie-breaker.
    debtors.sort(key=lambda item: (-item["remaining"], item["user_id"]))
    creditors.sort(key=lambda item: (-item["remaining"], item["user_id"]))

    suggestions = []
    debtor_index = 0
    creditor_index = 0

    while (
        debtor_index < len(debtors)
        and creditor_index < len(creditors)
    ):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]

        amount = min(
            debtor["remaining"],
            creditor["remaining"],
        )

        suggestions.append(
            {
                "payer_id": debtor["user_id"],
                "payee_id": creditor["user_id"],
                "amount": _as_money(amount),
            }
        )

        debtor["remaining"] -= amount
        creditor["remaining"] -= amount

        if debtor["remaining"] == ZERO:
            debtor_index += 1

        if creditor["remaining"] == ZERO:
            creditor_index += 1

    return {
        "group_id": balance_result["group_id"],
        "currency": balance_result["currency"],
        "suggestions": suggestions,
    }