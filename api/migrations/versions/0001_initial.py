"""create segments and comics

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "segments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "comics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column(
            "status",
            sa.Enum("in_progress", "failed", "succeeded", name="comicstatus", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("segment_id", sa.Uuid(), sa.ForeignKey("segments.id"), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("comics")
    op.drop_table("segments")
