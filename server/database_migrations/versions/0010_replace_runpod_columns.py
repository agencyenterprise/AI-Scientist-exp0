"""Rename RunPod columns to AWS instance terminology and add timestamps.

Revision ID: 0010
Revises: 0009
Create Date: 2025-12-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("research_pipeline_runs", "pod_id", new_column_name="instance_id")
    op.alter_column("research_pipeline_runs", "pod_name", new_column_name="instance_name")
    op.alter_column("research_pipeline_runs", "gpu_type", new_column_name="instance_type")
    op.alter_column("research_pipeline_runs", "pod_host_id", new_column_name="availability_zone")
    op.add_column(
        "research_pipeline_runs",
        sa.Column("instance_launched_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "research_pipeline_runs",
        sa.Column("instance_terminated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE research_pipeline_run_events "
            "SET event_type = 'instance_info_updated' "
            "WHERE event_type = 'pod_info_updated'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE research_pipeline_run_events "
            "SET event_type = 'instance_billing_summary' "
            "WHERE event_type = 'pod_billing_summary'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE research_pipeline_run_events "
            "SET event_type = 'pod_info_updated' "
            "WHERE event_type = 'instance_info_updated'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE research_pipeline_run_events "
            "SET event_type = 'pod_billing_summary' "
            "WHERE event_type = 'instance_billing_summary'"
        )
    )
    op.drop_column("research_pipeline_runs", "instance_terminated_at")
    op.drop_column("research_pipeline_runs", "instance_launched_at")
    op.alter_column("research_pipeline_runs", "availability_zone", new_column_name="pod_host_id")
    op.alter_column("research_pipeline_runs", "instance_type", new_column_name="gpu_type")
    op.alter_column("research_pipeline_runs", "instance_name", new_column_name="pod_name")
    op.alter_column("research_pipeline_runs", "instance_id", new_column_name="pod_id")
