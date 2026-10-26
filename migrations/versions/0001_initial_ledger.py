"""create ledger tables

Revision ID: 0001_initial_ledger
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_ledger"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("accounts",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("balance >= 0", name="ck_accounts_balance_nonnegative"), sa.PrimaryKeyConstraint("id"))
    op.create_table("transactions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(6), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False), sa.Column("reference_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"), sa.CheckConstraint("type IN ('credit', 'debit')", name="ck_transactions_type"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "reference_id", name="uq_transactions_account_reference"))
    op.create_index("ix_transactions_history", "transactions", ["account_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_history", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("accounts")
