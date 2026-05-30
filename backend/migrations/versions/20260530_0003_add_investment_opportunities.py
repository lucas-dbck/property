"""add investment opportunities

Revision ID: 20260530_0003
Revises: 20260530_0002
Create Date: 2026-05-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0003"
down_revision: str | None = "20260530_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investment_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("manual", "immoweb", "other", name="importsource"), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("imported_data", sa.Text(), nullable=False),
        sa.Column("user_overrides", sa.Text(), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investment_opportunities_id"), "investment_opportunities", ["id"], unique=False)
    op.create_index(op.f("ix_investment_opportunities_owner_id"), "investment_opportunities", ["owner_id"], unique=False)
    op.create_index(op.f("ix_investment_opportunities_source"), "investment_opportunities", ["source"], unique=False)
    op.create_index(op.f("ix_investment_opportunities_source_url"), "investment_opportunities", ["source_url"], unique=False)
    op.create_index(op.f("ix_investment_opportunities_title"), "investment_opportunities", ["title"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_investment_opportunities_title"), table_name="investment_opportunities")
    op.drop_index(op.f("ix_investment_opportunities_source_url"), table_name="investment_opportunities")
    op.drop_index(op.f("ix_investment_opportunities_source"), table_name="investment_opportunities")
    op.drop_index(op.f("ix_investment_opportunities_owner_id"), table_name="investment_opportunities")
    op.drop_index(op.f("ix_investment_opportunities_id"), table_name="investment_opportunities")
    op.drop_table("investment_opportunities")
