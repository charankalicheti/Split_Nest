"""Replace registered users with named, group-scoped participants.

Revision ID: 0002_named_group_participants
Revises: 0001_initial_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_named_group_participants"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAMING = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def _drop_foreign_keys(table: str, columns: set[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys(table)
        if set(foreign_key["constrained_columns"]) & columns
    ]
    if not foreign_keys:
        return

    with op.batch_alter_table(table, naming_convention=FK_NAMING) as batch:
        for foreign_key in foreign_keys:
            name = foreign_key["name"]
            if name is None:
                column = foreign_key["constrained_columns"][0]
                target = foreign_key["referred_table"]
                name = f"fk_{table}_{column}_{target}"
            batch.drop_constraint(name, type_="foreignkey")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return
    recreate_mode = "always" if bind.dialect.name == "sqlite" else "auto"

    op.create_table(
        "_participant_migration_map",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("legacy_user_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
    )
    op.execute(
        sa.text(
            "INSERT INTO _participant_migration_map "
            "(group_id, legacy_user_id, member_id) "
            "SELECT group_id, user_id, id FROM group_members"
        )
    )

    _drop_foreign_keys("groups", {"created_by"})
    _drop_foreign_keys("group_members", {"user_id"})
    _drop_foreign_keys("expenses", {"paid_by"})
    _drop_foreign_keys("expense_splits", {"user_id"})
    _drop_foreign_keys("settlements", {"payer_id", "payee_id", "created_by"})

    op.drop_index("ix_groups_created_by", table_name="groups")
    with op.batch_alter_table("groups") as batch:
        batch.drop_column("created_by")

    op.drop_index("ix_group_members_user_id", table_name="group_members")
    with op.batch_alter_table("group_members") as batch:
        batch.add_column(sa.Column("name", sa.String(length=100), nullable=True))
    op.execute(
        sa.text(
            "UPDATE group_members SET name = "
            "(SELECT users.name FROM users "
            "JOIN _participant_migration_map AS participant_map "
            "ON participant_map.legacy_user_id = users.id "
            "WHERE participant_map.member_id = group_members.id)"
        )
    )
    with op.batch_alter_table("group_members") as batch:
        batch.drop_constraint("uq_group_member", type_="unique")
        batch.drop_column("user_id")
        batch.alter_column("name", existing_type=sa.String(length=100), nullable=False)
    op.create_index(
        "ix_group_members_group_id",
        "group_members",
        ["group_id"],
    )

    op.execute(
        sa.text(
            "UPDATE expenses SET paid_by = "
            "(SELECT member_id FROM _participant_migration_map "
            "WHERE group_id = expenses.group_id "
            "AND legacy_user_id = expenses.paid_by)"
        )
    )
    with op.batch_alter_table("expenses", recreate=recreate_mode) as batch:
        batch.create_foreign_key(
            "fk_expenses_paid_by_group_members",
            "group_members",
            ["paid_by"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.drop_index("ix_expense_splits_user_id", table_name="expense_splits")
    op.execute(
        sa.text(
            "UPDATE expense_splits SET user_id = "
            "(SELECT participant_map.member_id "
            "FROM _participant_migration_map AS participant_map "
            "JOIN expenses ON expenses.group_id = participant_map.group_id "
            "WHERE expenses.id = expense_splits.expense_id "
            "AND participant_map.legacy_user_id = expense_splits.user_id)"
        )
    )
    with op.batch_alter_table("expense_splits", recreate=recreate_mode) as batch:
        batch.drop_constraint("uq_expense_split_member", type_="unique")
        batch.alter_column(
            "user_id",
            new_column_name="member_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
    with op.batch_alter_table("expense_splits", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_expense_splits_member_id_group_members",
            "group_members",
            ["member_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_expense_split_member",
            ["expense_id", "member_id"],
        )
    op.create_index(
        "ix_expense_splits_member_id",
        "expense_splits",
        ["member_id"],
    )

    for column in ("payer_id", "payee_id", "created_by"):
        op.execute(
            sa.text(
                f"UPDATE settlements SET {column} = "
                "(SELECT member_id FROM _participant_migration_map "
                "WHERE group_id = settlements.group_id "
                f"AND legacy_user_id = settlements.{column})"
            )
        )
    with op.batch_alter_table("settlements", recreate=recreate_mode) as batch:
        for column in ("payer_id", "payee_id", "created_by"):
            batch.create_foreign_key(
                f"fk_settlements_{column}_group_members",
                "group_members",
                [column],
                ["id"],
                ondelete="RESTRICT",
            )

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("_participant_migration_map")
    op.drop_table("users")


def downgrade() -> None:
    bind = op.get_bind()
    if "users" in sa.inspect(bind).get_table_names():
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO users (id, name, email, password_hash) "
            "SELECT id, name, "
            "'participant-' || CAST(id AS VARCHAR) || '@invalid.local', "
            "'disabled' FROM group_members"
        )
    )

    op.drop_index("ix_group_members_group_id", table_name="group_members")
    with op.batch_alter_table("group_members") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE group_members SET user_id = id"))
    with op.batch_alter_table("group_members") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("name")
        batch.create_foreign_key(
            "fk_group_members_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint(
            "uq_group_member",
            ["group_id", "user_id"],
        )
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    with op.batch_alter_table("groups") as batch:
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE groups SET created_by = "
            "(SELECT id FROM group_members "
            "WHERE group_members.group_id = groups.id ORDER BY id LIMIT 1)"
        )
    )
    with op.batch_alter_table("groups") as batch:
        batch.alter_column("created_by", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_groups_created_by_users",
            "users",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_groups_created_by", "groups", ["created_by"])

    with op.batch_alter_table("expenses") as batch:
        batch.drop_constraint("fk_expenses_paid_by_group_members", type_="foreignkey")
        batch.create_foreign_key(
            "fk_expenses_paid_by_users",
            "users",
            ["paid_by"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.drop_index("ix_expense_splits_member_id", table_name="expense_splits")
    with op.batch_alter_table("expense_splits") as batch:
        batch.drop_constraint(
            "uq_expense_split_member",
            type_="unique",
        )
        batch.drop_constraint(
            "fk_expense_splits_member_id_group_members",
            type_="foreignkey",
        )
        batch.alter_column(
            "member_id",
            new_column_name="user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch.create_foreign_key(
            "fk_expense_splits_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_expense_split_member",
            ["expense_id", "user_id"],
        )
    op.create_index("ix_expense_splits_user_id", "expense_splits", ["user_id"])

    with op.batch_alter_table("settlements") as batch:
        for column in ("payer_id", "payee_id", "created_by"):
            batch.drop_constraint(
                f"fk_settlements_{column}_group_members",
                type_="foreignkey",
            )
            batch.create_foreign_key(
                f"fk_settlements_{column}_users",
                "users",
                [column],
                ["id"],
                ondelete="RESTRICT",
            )
