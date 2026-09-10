"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

rate_type_enum = postgresql.ENUM("TEA", "TCEA", name="rate_type")
frequency_enum = postgresql.ENUM(
    "MENSUAL", "QUINCENAL", "BIMESTRAL", "TRIMESTRAL", "CUATRIMESTRAL", "SEMESTRAL", "ANUAL", name="frequency"
)
installment_status_enum = postgresql.ENUM("PENDING", "PAID", name="installment_status")


def upgrade() -> None:
    # The enum types are created implicitly by create_table below (each
    # postgresql.ENUM column emits its CREATE TYPE on first use); creating
    # them again explicitly here would raise DuplicateObject.
    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("principal", sa.Numeric(14, 2), nullable=False),
        sa.Column("annual_rate", sa.Numeric(9, 6), nullable=False),
        sa.Column("rate_type", rate_type_enum, nullable=False),
        sa.Column("frequency", frequency_enum, nullable=False),
        sa.Column("num_installments", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("initial_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("interest_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("amortization_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("final_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", installment_status_enum, nullable=False, server_default="PENDING"),
    )
    op.create_index("ix_installments_loan_id", "installments", ["loan_id"])
    op.create_unique_constraint("uq_installments_loan_number", "installments", ["loan_id", "number"])

    op.create_table(
        "amortizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "loan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_amortizations_loan_id", "amortizations", ["loan_id"])


def downgrade() -> None:
    op.drop_table("amortizations")
    op.drop_table("installments")
    op.drop_table("loans")
    installment_status_enum.drop(op.get_bind(), checkfirst=True)
    frequency_enum.drop(op.get_bind(), checkfirst=True)
    rate_type_enum.drop(op.get_bind(), checkfirst=True)
