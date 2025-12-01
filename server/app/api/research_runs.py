"""
API endpoints for listing all research pipeline runs.
"""

import logging

from fastapi import APIRouter, Query, Request

from app.middleware.auth import get_current_user
from app.models import ResearchRunListItem, ResearchRunListResponse
from app.services import get_database

router = APIRouter(prefix="/research-runs", tags=["research-runs"])
logger = logging.getLogger(__name__)


def _row_to_list_item(row: dict) -> ResearchRunListItem:
    """Convert a database row to a ResearchRunListItem."""
    return ResearchRunListItem(
        run_id=row["run_id"],
        status=row["status"],
        idea_title=row["idea_title"] or "Untitled",
        idea_hypothesis=row.get("idea_hypothesis"),
        current_stage=row.get("current_stage"),
        progress=row.get("progress"),
        gpu_type=row.get("gpu_type"),
        best_metric=row.get("best_metric"),
        created_by_name=row["created_by_name"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
        artifacts_count=row.get("artifacts_count", 0),
        error_message=row.get("error_message"),
        conversation_id=row["conversation_id"],
    )


@router.get("/", response_model=ResearchRunListResponse)
def list_research_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
) -> ResearchRunListResponse:
    """
    List all research pipeline runs with enriched data.

    Returns runs ordered by creation date (newest first) with:
    - Run metadata (status, GPU, timestamps)
    - Idea information (title, hypothesis)
    - Latest stage progress (stage, progress percentage, best metric)
    - Artifact count
    - Creator information
    """
    # Ensure user is authenticated
    get_current_user(request)

    db = get_database()
    rows, total = db.list_all_research_pipeline_runs(limit=limit, offset=offset)

    items = [_row_to_list_item(row) for row in rows]

    return ResearchRunListResponse(items=items, total=total)
