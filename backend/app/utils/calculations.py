from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


TWO_PLACES = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    return amount.quantize(
        TWO_PLACES,
        rounding=ROUND_HALF_UP
    )


def calculate_equal_split(
    total_amount: Decimal,
    member_ids: list[int],
) -> dict[int, Decimal]:

    if total_amount <= 0:
        raise ValueError("Total amount must be greater than zero.")

    if not member_ids:
        raise ValueError("At least one participant is required.")

    number_of_members = len(member_ids)

    base_share = (
        total_amount / Decimal(number_of_members)
    ).quantize(
        TWO_PLACES,
        rounding=ROUND_DOWN
    )

    remaining = round_money(
        total_amount - (
            base_share * number_of_members
        )
    )

    splits: dict[int, Decimal] = {}

    for member_id in member_ids:
        share = base_share

        if remaining >= TWO_PLACES:
            share += TWO_PLACES
            remaining -= TWO_PLACES

        splits[member_id] = share

    return splits


def validate_custom_split(
    total_amount: Decimal,
    splits: dict[int, Decimal],
) -> bool:

    if total_amount <= 0:
        raise ValueError("Total amount must be greater than zero.")

    if not splits:
        raise ValueError("At least one split is required.")

    for member_id, amount in splits.items():

        if amount < 0:
            raise ValueError(
                f"Split amount for participant {member_id} "
                "cannot be negative."
            )

    split_total = sum(
        splits.values(),
        Decimal("0.00")
    )

    if round_money(split_total) != round_money(total_amount):
        raise ValueError(
            f"Split total {round_money(split_total)} "
            f"does not match expense total "
            f"{round_money(total_amount)}."
        )

    return True