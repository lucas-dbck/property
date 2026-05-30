"""enrich property listings

Revision ID: 20260530_0002
Revises: 20260528_0001
Create Date: 2026-05-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0002"
down_revision: str | None = "20260528_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("slug", sa.String(length=180), nullable=True))
    op.add_column(
        "properties",
        sa.Column(
            "listing_type",
            sa.Enum("sale", "rent", name="listingtype"),
            server_default="sale",
            nullable=False,
        ),
    )
    op.add_column("properties", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("properties", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("properties", sa.Column("amenities", sa.Text(), nullable=True))
    op.add_column("properties", sa.Column("available_from", sa.Date(), nullable=True))
    op.add_column("properties", sa.Column("energy_score", sa.String(length=40), nullable=True))
    op.add_column("properties", sa.Column("agent_name", sa.String(length=120), nullable=True))
    op.add_column("properties", sa.Column("agent_phone", sa.String(length=50), nullable=True))
    op.add_column("properties", sa.Column("agent_email", sa.String(length=255), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, title FROM properties")).fetchall()
    used_slugs: set[str] = set()
    for row in rows:
        base_slug = "".join(character.lower() if character.isalnum() else "-" for character in row.title)
        base_slug = "-".join(part for part in base_slug.split("-") if part) or f"property-{row.id}"
        next_slug = base_slug
        counter = 2
        while next_slug in used_slugs:
            next_slug = f"{base_slug}-{counter}"
            counter += 1
        used_slugs.add(next_slug)
        connection.execute(
            sa.text("UPDATE properties SET slug = :slug WHERE id = :id"),
            {"slug": next_slug, "id": row.id},
        )

    op.alter_column("properties", "slug", nullable=False)
    op.create_index(op.f("ix_properties_slug"), "properties", ["slug"], unique=True)
    op.create_index(op.f("ix_properties_listing_type"), "properties", ["listing_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_properties_listing_type"), table_name="properties")
    op.drop_index(op.f("ix_properties_slug"), table_name="properties")
    op.drop_column("properties", "agent_email")
    op.drop_column("properties", "agent_phone")
    op.drop_column("properties", "agent_name")
    op.drop_column("properties", "energy_score")
    op.drop_column("properties", "available_from")
    op.drop_column("properties", "amenities")
    op.drop_column("properties", "longitude")
    op.drop_column("properties", "latitude")
    op.drop_column("properties", "listing_type")
    op.drop_column("properties", "slug")
