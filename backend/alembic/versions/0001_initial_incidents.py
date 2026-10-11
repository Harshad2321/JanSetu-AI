"""0001_initial_incidents

Revision ID: 0001
Revises: 
Create Date: 2026-10-11 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "incidents" not in existing_tables:
        op.create_table(
            "incidents",
            sa.Column("incident_id", sa.String(length=64), primary_key=True),
            sa.Column("complaint", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False, server_default="uncertain_other"),
            sa.Column("location_data", sa.JSON(), nullable=True),
            sa.Column("has_photograph", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("photo_storage_path", sa.String(length=512), nullable=True),
            sa.Column("photo_mime_type", sa.String(length=64), nullable=True),
            sa.Column("operational_status", sa.String(length=64), nullable=False, server_default="NEW"),
            sa.Column("evidence_status", sa.String(length=64), nullable=False, server_default="NOT_PROVIDED"),
            sa.Column("extracted_facts", sa.JSON(), nullable=True),
            sa.Column("evidence_analysis", sa.JSON(), nullable=True),
            sa.Column("geo_context", sa.JSON(), nullable=True),
            sa.Column("priority", sa.JSON(), nullable=True),
            sa.Column("current_plan", sa.JSON(), nullable=True),
            sa.Column("validation", sa.JSON(), nullable=True),
            sa.Column("closure_evidence", sa.JSON(), nullable=True),
            sa.Column("simulation_result", sa.String(length=64), nullable=True),
            sa.Column("failure_reason", sa.String(length=512), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("agent_traces", sa.JSON(), nullable=False),
            sa.Column("audit_timeline", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_incidents_incident_id", "incidents", ["incident_id"], unique=False)
        op.create_index("ix_incidents_category", "incidents", ["category"], unique=False)
        op.create_index("ix_incidents_operational_status", "incidents", ["operational_status"], unique=False)
        op.create_index("ix_incidents_evidence_status", "incidents", ["evidence_status"], unique=False)


def downgrade() -> None:
    # Safe non-destructive policy: do not drop table in production unless explicitly commanded
    op.drop_table("incidents")
