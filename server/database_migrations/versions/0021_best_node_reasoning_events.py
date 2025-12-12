"""Add table for best-node reasoning and enforce RP run foreign keys."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create reasoning table and add missing run_id foreign keys."""
    op.create_table(
        "rp_best_node_reasoning_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "run_id",
            sa.Text(),
            sa.ForeignKey("research_pipeline_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="rp_best_node_reasoning_events_pkey"),
    )
    op.create_index(
        "idx_rp_best_node_reasoning_events_run",
        "rp_best_node_reasoning_events",
        ["run_id"],
    )
    op.create_index(
        "idx_rp_best_node_reasoning_events_stage",
        "rp_best_node_reasoning_events",
        ["stage"],
    )

    # Backfill missing run_id foreign keys on existing rp_* tables.
    op.create_foreign_key(
        "fk_rp_run_stage_progress_events_run",
        "rp_run_stage_progress_events",
        "research_pipeline_runs",
        ["run_id"],
        ["run_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_rp_run_log_events_run",
        "rp_run_log_events",
        "research_pipeline_runs",
        ["run_id"],
        ["run_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_rp_substage_completed_events_run",
        "rp_substage_completed_events",
        "research_pipeline_runs",
        ["run_id"],
        ["run_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_rp_paper_generation_events_run",
        "rp_paper_generation_events",
        "research_pipeline_runs",
        ["run_id"],
        ["run_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_rp_tree_viz_run",
        "rp_tree_viz",
        "research_pipeline_runs",
        ["run_id"],
        ["run_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Drop reasoning table and remove added foreign keys."""
    op.drop_constraint(
        "fk_rp_tree_viz_run",
        table_name="rp_tree_viz",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_rp_paper_generation_events_run",
        table_name="rp_paper_generation_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_rp_substage_completed_events_run",
        table_name="rp_substage_completed_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_rp_run_log_events_run",
        table_name="rp_run_log_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_rp_run_stage_progress_events_run",
        table_name="rp_run_stage_progress_events",
        type_="foreignkey",
    )

    op.drop_index(
        "idx_rp_best_node_reasoning_events_stage",
        table_name="rp_best_node_reasoning_events",
    )
    op.drop_index(
        "idx_rp_best_node_reasoning_events_run",
        table_name="rp_best_node_reasoning_events",
    )
    op.drop_table("rp_best_node_reasoning_events")
