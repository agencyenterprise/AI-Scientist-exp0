import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services import get_database
from app.services.database import DatabaseManager
from app.services.database.research_pipeline_runs import ResearchPipelineRun
from app.services.research_pipeline import (
    AWSEC2Error,
    fetch_instance_billing_summary,
    terminate_instance,
    upload_worker_log_via_ssh,
)
from app.services.research_pipeline.aws_ec2_manager import AWSEC2Manager

logger = logging.getLogger(__name__)


class PipelineMonitorError(Exception):
    """Raised when the pipeline monitor encounters an unexpected error."""


class ResearchPipelineMonitor:
    def __init__(
        self,
        *,
        poll_interval_seconds: int,
        heartbeat_timeout_seconds: int,
        max_missed_heartbeats: int,
        startup_grace_seconds: int,
    ) -> None:
        self._poll_interval = poll_interval_seconds
        self._heartbeat_timeout = timedelta(seconds=heartbeat_timeout_seconds)
        self._max_missed_heartbeats = max_missed_heartbeats
        self._startup_grace = timedelta(seconds=startup_grace_seconds)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        region = os.environ.get("AWS_REGION")
        if not region:
            raise RuntimeError("AWS_REGION environment variable is required.")
        self._ec2_manager = AWSEC2Manager(region=region)

    async def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="PipelineMonitor", daemon=True)
        self._thread.start()
        logger.info("Research pipeline monitor started.")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 1)
            self._thread = None
        logger.info("Research pipeline monitor stopped.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_runs()
            except PipelineMonitorError:
                logger.exception("Pipeline monitor encountered an error.")
            self._stop_event.wait(timeout=self._poll_interval)

    def _check_runs(self) -> None:
        try:
            db = get_database()
            runs = db.list_active_research_pipeline_runs()
            if not runs:
                logger.debug("Pipeline monitor heartbeat: no active runs.")
                return
            logger.info(
                "Pipeline monitor inspecting %s active runs: %s",
                len(runs),
                [f"{run.run_id}:{run.status}" for run in runs],
            )
            now = datetime.now(timezone.utc)
            for run in runs:
                if run.status == "pending":
                    self._handle_pending_run(db, run, now)
                elif run.status == "running":
                    self._handle_running_run(db, run, now)
        except Exception as exc:  # noqa: BLE001
            raise PipelineMonitorError from exc

    def _handle_pending_run(
        self, db: "DatabaseManager", run: ResearchPipelineRun, now: datetime
    ) -> None:
        deadline = run.start_deadline_at
        if deadline is None:
            logger.info(
                "Run %s pending; launch has not scheduled a deadline yet.",
                run.run_id,
            )
            return
        if deadline:
            remaining = (deadline - now).total_seconds()
            if remaining > 0:
                logger.info(
                    "Run %s pending; waiting for instance start (%.0fs remaining).",
                    run.run_id,
                    remaining,
                )
        if deadline and now > deadline:
            self._fail_run(db, run, "Pipeline did not start within the grace period.")

    def _handle_running_run(
        self, db: "DatabaseManager", run: ResearchPipelineRun, now: datetime
    ) -> None:
        if run.last_heartbeat_at is None:
            deadline = run.start_deadline_at
            if deadline is None:
                logger.info(
                    "Run %s awaiting instance start; deadline not scheduled yet.",
                    run.run_id,
                )
                return
            if deadline:
                remaining = (deadline - now).total_seconds()
                logger.info(
                    "Run %s awaiting first heartbeat (%.0fs remaining).",
                    run.run_id,
                    max(0, remaining),
                )
            if deadline and now > deadline:
                self._fail_run(db, run, "Pipeline failed to send an initial heartbeat.")
            return

        delta = now - run.last_heartbeat_at
        if delta > self._heartbeat_timeout:
            failures = run.heartbeat_failures + 1
            db.update_research_pipeline_run(run_id=run.run_id, heartbeat_failures=failures)
            logger.warning(
                "Run %s missed heartbeat (delta %.0fs). Failure count %s/%s.",
                run.run_id,
                delta.total_seconds(),
                failures,
                self._max_missed_heartbeats,
            )
            if failures >= self._max_missed_heartbeats:
                self._fail_run(db, run, "Pipeline heartbeats exceeded failure threshold.")
            return

        if run.heartbeat_failures > 0:
            db.update_research_pipeline_run(run_id=run.run_id, heartbeat_failures=0)

        if run.instance_id:
            try:
                instance = self._ec2_manager.describe_instance(instance_id=run.instance_id)
            except AWSEC2Error as exc:
                logger.warning("Failed to poll instance %s: %s", run.instance_id, exc)
            else:
                state = instance.get("State", {}).get("Name")
                if state == "pending":
                    logger.info(
                        "Run %s instance %s still pending startup; waiting for readiness.",
                        run.run_id,
                        run.instance_id,
                    )
                elif state not in ("running", "pending"):
                    logger.warning(
                        "Run %s instance %s returned unexpected state '%s'; failing run.",
                        run.run_id,
                        run.instance_id,
                        state,
                    )
                    self._fail_run(db, run, f"Instance state is {state}; terminating run.")

    def _fail_run(self, db: "DatabaseManager", run: ResearchPipelineRun, message: str) -> None:
        logger.warning("Marking run %s as failed: %s", run.run_id, message)
        db.update_research_pipeline_run(
            run_id=run.run_id,
            status="failed",
            error_message=message,
        )
        db.insert_research_pipeline_run_event(
            run_id=run.run_id,
            event_type="status_changed",
            metadata={
                "from_status": run.status,
                "to_status": "failed",
                "reason": "pipeline_monitor",
                "error_message": message,
            },
            occurred_at=datetime.now(timezone.utc),
        )
        if run.instance_id:
            self._upload_worker_log(run)
            try:
                terminate_instance(instance_id=run.instance_id)
            except RuntimeError as exc:
                logger.warning("Failed to terminate instance %s: %s", run.instance_id, exc)
            else:
                db.update_research_pipeline_run(
                    run_id=run.run_id,
                    instance_info={"instance_terminated_at": datetime.now(timezone.utc)},
                )
            self._record_instance_billing_event(
                db=db,
                run_id=run.run_id,
                instance_id=run.instance_id,
                context="pipeline_monitor_failure",
            )

    def _record_instance_billing_event(
        self,
        db: "DatabaseManager",
        *,
        run_id: str,
        instance_id: str,
        context: str,
    ) -> None:
        try:
            summary = fetch_instance_billing_summary(instance_id=instance_id)
        except AWSEC2Error as exc:
            logger.warning("Failed to fetch billing summary for instance %s: %s", instance_id, exc)
            return
        if summary is None:
            return
        metadata = dict(summary)
        metadata["context"] = context
        db.insert_research_pipeline_run_event(
            run_id=run_id,
            event_type="instance_billing_summary",
            metadata=metadata,
            occurred_at=datetime.now(timezone.utc),
        )

    def _upload_worker_log(self, run: ResearchPipelineRun) -> None:
        if not run.public_ip or not run.ssh_port:
            logger.info("Run %s missing SSH info; skipping log upload.", run.run_id)
            return
        try:
            upload_worker_log_via_ssh(
                host=run.public_ip,
                port=run.ssh_port,
                run_id=run.run_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to upload worker log via SSH for run %s: %s", run.run_id, exc)


def _require_int(name: str) -> int:
    value = os.environ.get(name)
    if value is None:
        raise RuntimeError(f"Environment variable {name} is required for pipeline monitoring.")
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer.") from exc


DEFAULT_POLL_INTERVAL_SECONDS = _require_int("PIPELINE_MONITOR_POLL_INTERVAL_SECONDS")
DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = _require_int("PIPELINE_MONITOR_HEARTBEAT_TIMEOUT_SECONDS")
DEFAULT_MAX_MISSED_HEARTBEATS = _require_int("PIPELINE_MONITOR_MAX_MISSED_HEARTBEATS")
DEFAULT_STARTUP_GRACE_SECONDS = _require_int("PIPELINE_MONITOR_STARTUP_GRACE_SECONDS")

pipeline_monitor = ResearchPipelineMonitor(
    poll_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
    heartbeat_timeout_seconds=DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    max_missed_heartbeats=DEFAULT_MAX_MISSED_HEARTBEATS,
    startup_grace_seconds=DEFAULT_STARTUP_GRACE_SECONDS,
)
