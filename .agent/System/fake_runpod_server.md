# Fake RunPod Server

## Related Documentation
- [README.md](../README.md) - Documentation index
- [Server Architecture](server_architecture.md) - FastAPI server details
- [Project Architecture](project_architecture.md) - Overall system architecture

---

## 1. Overview

The Fake RunPod Server is a local development tool that simulates RunPod's GPU cloud infrastructure APIs. It enables end-to-end testing of the research pipeline without incurring real cloud GPU costs or requiring actual GPU hardware.

**Location**: `server/app/services/research_pipeline/fake_runpod_server.py`

### Use Cases

- **Local development**: Test pipeline integration without GPU costs
- **CI/CD testing**: Validate event flow and API contracts
- **Frontend development**: Test real-time progress updates via SSE
- **Debugging**: Isolate issues in event persistence or webhook delivery

---

## 2. Architecture

The fake server consists of two main components:

### FastAPI Application

A FastAPI server that mimics RunPod's REST and GraphQL APIs:

```
┌─────────────────────────────────────────────────────────────┐
│                    Fake RunPod Server                       │
│                   (FastAPI @ localhost:9000)                │
├─────────────────────────────────────────────────────────────┤
│  /pods (POST)          → Create pod, spawn FakeRunner       │
│  /pods/{id} (GET)      → Return pod status                  │
│  /pods/{id} (DELETE)   → Remove pod from registry           │
│  /billing/pods (GET)   → Return mock billing (0.0)          │
│  /graphql (POST)       → Return fake podHostId              │
│  /telemetry/* (POST)   → Collect telemetry events           │
└─────────────────────────────────────────────────────────────┘
```

### FakeRunner Class

A background thread that simulates a complete research pipeline execution:

```
┌─────────────────────────────────────────────────────────────┐
│                       FakeRunner                            │
├─────────────────────────────────────────────────────────────┤
│  1. publish_run_started()                                   │
│  2. Start heartbeat thread (every 10s)                      │
│  3. Emit stage progress (4 stages × 3 iterations × 20s)     │
│  4. Publish fake artifact to S3                             │
│  5. publish_run_finished(success=True)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. API Endpoints

### Pod Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pods` | POST | Create a fake pod. Spawns FakeRunner thread. Returns pod ID. |
| `/pods/{pod_id}` | GET | Get pod status (PENDING → RUNNING after 1s) |
| `/pods/{pod_id}` | DELETE | Delete pod from in-memory registry |

### Billing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/billing/pods` | GET | Returns mock billing summary (always 0.0 USD) |

### GraphQL

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graphql` | POST | Returns fake `podHostId` for SSH access queries |

### Telemetry (for testing)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telemetry/run-started` | POST | Receives run started signal |
| `/telemetry/run-finished` | POST | Receives run finished signal |
| `/telemetry/heartbeat` | POST | Receives heartbeat |
| `/telemetry/stage-progress` | POST | Receives stage progress events (stages 1-4) |
| `/telemetry/substage-completed` | POST | Receives substage completion |
| `/telemetry/paper-generation-progress` | POST | Receives paper generation events (stage 5) |
| `/telemetry/gpu-shortage` | POST | Receives GPU shortage alerts |
| `/telemetry` | GET | List all received telemetry events |

---

## 4. FakeRunner Behavior

### Stage Simulation

The runner simulates 5 research pipeline stages:

**Stages 1-4 (Research Iteration):**

| Stage | Name | Iterations | Time per Iteration |
|-------|------|------------|-------------------|
| 1 | `1_initial_implementation_1_preliminary` | 3 of 10 | 20s |
| 2 | `2_baseline_tuning_1_first_attempt` | 3 of 5 | 20s |
| 3 | `3_creative_research_1_first_attempt` | 3 of 5 | 20s |
| 4 | `4_ablation_studies_1_first_attempt` | 3 of 5 | 20s |

**Stage 5 (Paper Generation):**

| Step | Substeps | Time per Substep |
|------|----------|------------------|
| `plot_aggregation` | collecting_figures, validating_plots, generating_captions | 5s |
| `citation_gathering` | searching_literature, filtering_relevant, formatting_citations | 5s |
| `paper_writeup` | writing_abstract, writing_introduction, writing_methodology, writing_results, writing_discussion, writing_conclusion | 5s |
| `paper_review` | review_1, review_2, review_3 | 5s |

**Total simulation time**: ~5 minutes
- Stages 1-4: 12 iterations × 20 seconds = ~4 minutes
- Stage 5: 15 substeps × 5 seconds = ~75 seconds

### Events Emitted

For each iteration:
```python
PersistableEvent(
    kind="run_stage_progress",
    data={
        "stage": stage_name,
        "iteration": iteration + 1,
        "max_iterations": max_iterations,
        "progress": progress,
        "total_nodes": 10 + iteration,
        "buggy_nodes": iteration,
        "good_nodes": 9 - iteration,
        "best_metric": f"metric-{progress:.2f}",
        "eta_s": estimated_time_remaining,
        "latest_iteration_time_s": 20,
    }
)
```

After each stage:
```python
PersistableEvent(
    kind="substage_completed",
    data={
        "stage": stage_name,
        "main_stage_number": stage_index + 1,
        "substage_number": 1,
        "substage_name": "fake-substage",
        "reason": "completed",
        "summary": {...}
    }
)
```

**Stage 5 Paper Generation Events:**

For each paper generation substep:
```python
PersistableEvent(
    kind="paper_generation_progress",
    data={
        "step": step_name,           # e.g., "plot_aggregation"
        "substep": substep_name,     # e.g., "collecting_figures"
        "progress": overall_progress, # 0-1, across all steps
        "step_progress": step_progress, # 0-1, within current step
        "details": {
            # Step-specific metadata
            "figures_collected": 8,   # for plot_aggregation
            "citations_found": 15,    # for citation_gathering
            "word_count": 4500,       # for paper_writeup
            "avg_score": 7.2,         # for paper_review
        }
    }
)
```

### Artifact Publication

Creates a fake artifact file and uploads to S3:
```python
artifact_path.write_text("fake run output\n")
ArtifactPublisher(...).publish(
    spec=ArtifactSpec(
        artifact_type="fake_result",
        path=artifact_path,
        packaging="file",
    )
)
```

**Note**: This requires real AWS credentials - artifacts are uploaded to the actual S3 bucket.

---

## 5. Event Flow

```
┌──────────────┐    ┌─────────────────────┐    ┌──────────────┐
│  FakeRunner  │───▶│ EventPersistenceManager │───▶│  PostgreSQL  │
│              │    │                     │    │  (rp_* tables)│
└──────────────┘    └─────────────────────┘    └──────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   WebhookClient     │
                    │ (HTTP POST to server)│
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Server Webhooks    │
                    │ /api/research-pipeline/events │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │     SSE Stream      │
                    │   (to Frontend)     │
                    └─────────────────────┘
```

### Database Tables

Events are persisted to:
- `rp_run_stage_progress_events` - Stage progress
- `rp_run_log_events` - Log messages
- `rp_substage_completed_events` - Substage completions
- `rp_paper_generation_progress_events` - Paper generation progress

---

## 6. Environment Variables

### Required for Fake Server

```bash
# Fake server port
FAKE_RUNPOD_PORT="9000"

# Database for event persistence
DATABASE_PUBLIC_URL="postgresql://user:pass@host:5432/db"

# Webhook endpoint (your local server)
TELEMETRY_WEBHOOK_URL="http://localhost:8000/api/research-pipeline/events"
TELEMETRY_WEBHOOK_TOKEN="your-webhook-token"

# AWS credentials (for real artifact uploads)
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
AWS_REGION="us-east-1"
AWS_S3_BUCKET_NAME="your-bucket"
```

### Required for RunPodManager Redirection

```bash
# Point RunPodManager at fake server
FAKE_RUNPOD_BASE_URL="http://127.0.0.1:9000"
FAKE_RUNPOD_GRAPHQL_URL="http://127.0.0.1:9000/graphql"
```

---

## 7. Usage Guide

### Starting the Fake Server

From the `server/` directory:

```bash
make fake-runpod
```

Or manually:
```bash
VIRTUAL_ENV= PYTHONPATH=../research_pipeline:..:$(PYTHONPATH) \
  uv run python -m app.services.research_pipeline.fake_runpod_server
```

### Running with Fake Server

1. **Terminal 1**: Start the fake RunPod server
   ```bash
   cd server && make fake-runpod
   ```

2. **Terminal 2**: Start the main server with fake endpoints
   ```bash
   export FAKE_RUNPOD_BASE_URL="http://127.0.0.1:9000"
   export FAKE_RUNPOD_GRAPHQL_URL="http://127.0.0.1:9000/graphql"
   cd server && make dev
   ```

3. **Terminal 3**: Start the frontend
   ```bash
   cd frontend && npm run dev
   ```

4. **Create a research run** via the frontend - it will use the fake server

### Expected Output

When a pod is created, you'll see:
```
INFO:     127.0.0.1:xxxxx - "POST /pods HTTP/1.1" 200
INFO:     FakeRunner starting for run_id=xxx
INFO:     1_initial_implementation_1_preliminary iteration 1 complete
INFO:     1_initial_implementation_1_preliminary iteration 2 complete
...
INFO:     FakeRunner completed for run_id=xxx
```

---

## 8. Code Reference

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `FakeRunner` | `fake_runpod_server.py:304` | Simulates pipeline execution |
| `PodRecord` | `fake_runpod_server.py:27` | Pod state storage |
| `LocalPersistence` | `fake_runpod_server.py:292` | Fallback when DB unavailable |

### Integration Points

| File | Purpose |
|------|---------|
| `runpod_manager.py:32-35` | Checks for `FAKE_RUNPOD_BASE_URL` override |
| `event_persistence.py` | Shared event persistence infrastructure |
| `artifact_manager.py` | S3 artifact upload (used by fake runner) |

---

## 9. Limitations

1. **AWS Credentials Required**: Artifact uploads go to real S3
2. **Fixed Timing**: Stage iterations are always 20 seconds
3. **No GPU Simulation**: No actual ML workload execution
4. **Single-threaded**: One runner per pod creation
5. **In-memory State**: Pod registry is lost on restart
