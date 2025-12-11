## 🔍 Feature Area: Mypy Error - Missing PaperGenerationProgressEvent

## Summary

Commit `8af0a23` (Dec 10, 2025) added real-time paper generation progress tracking but **forgot to define the `PaperGenerationProgressEvent` class** in `events.py`. The commit added the event type to `EventKind` literal and added imports in 4 files, but never implemented the actual event class. This causes mypy type checking to fail.

## Root Cause

| File                                                       | Lines | Issue                                                                            |
| ---------------------------------------------------------- | ----- | -------------------------------------------------------------------------------- |
| `research_pipeline/ai_scientist/treesearch/events.py`      | 4-9   | Added `"paper_generation_progress"` to EventKind literal but no class definition |
| `research_pipeline/ai_scientist/perform_llm_review.py`     | 15    | Imports non-existent `PaperGenerationProgressEvent`                              |
| `research_pipeline/ai_scientist/perform_writeup.py`        | 28    | Imports non-existent `PaperGenerationProgressEvent`                              |
| `research_pipeline/ai_scientist/perform_icbinb_writeup.py` | 28    | Imports non-existent `PaperGenerationProgressEvent`                              |
| `research_pipeline/ai_scientist/perform_plotting.py`       | 22    | Imports non-existent `PaperGenerationProgressEvent`                              |

## Event Usage Patterns Found

All 4 files instantiate `PaperGenerationProgressEvent` with consistent parameters:

**perform_llm_review.py:**

- Line 252-258: Paper review starting (progress=0.80, step_progress=0.0)
- Line 288-294: Review ensemble progress (progress=0.80-1.0, step_progress tracking)

**perform_writeup.py:**

- Line 839-845: Paper writeup starting (progress=0.30, step_progress=0.0)
- Line 994+: Writeup revision progress tracking

**perform_plotting.py:**

- Line 257+: Plot aggregation progress tracking
- Line 285+: Figure generation progress

**perform_icbinb_writeup.py:**

- Line 830+: ICBINB-specific writeup progress
- Line 849+: Citation gathering progress
- Line 916+: Final writeup compilation

**Common constructor signature:**

```python
PaperGenerationProgressEvent(
    run_id=str,
    step=str,          # "plot_aggregation" | "citation_gathering" | "paper_writeup" | "paper_review"
    substep=str,       # Optional descriptive text
    progress=float,    # 0.0-1.0 overall progress
    step_progress=float # 0.0-1.0 within current step
)
```

## Backend Infrastructure (Already Exists)

| File                                                                     | Lines   | Purpose                                             | Status    |
| ------------------------------------------------------------------------ | ------- | --------------------------------------------------- | --------- |
| `server/database_migrations/versions/0019_rp_paper_generation_events.py` | 23-43   | Creates `rp_paper_generation_events` table          | ✅ Exists |
| `server/app/models/research_pipeline.py`                                 | 100-116 | Pydantic model `ResearchRunPaperGenerationProgress` | ✅ Exists |
| `research_pipeline/ai_scientist/telemetry/event_persistence.py`          | ~258    | Handles `"paper_generation_progress"` persistence   | ✅ Exists |

**Database Schema (from migration):**

- `run_id` (Text)
- `step` (Text)
- `substep` (Text, nullable)
- `progress` (Float)
- `step_progress` (Float)
- `details` (JSONB, nullable)
- `created_at` (Timestamp)

## Expected Event Class Structure

Based on existing event patterns in `events.py` (lines 30-150):

```python
@dataclass(frozen=True)
class PaperGenerationProgressEvent(BaseEvent):
    run_id: str
    step: str
    substep: Optional[str] = None
    progress: float
    step_progress: float
    details: Optional[Dict[str, Any]] = None

    def type(self) -> str:
        return "ai.run.paper_generation_progress"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step": self.step,
            "substep": self.substep,
            "progress": self.progress,
            "step_progress": self.step_progress,
            "details": self.details,
        }

    def persistence_record(self) -> PersistenceRecord:
        return (
            "paper_generation_progress",
            {
                "run_id": self.run_id,
                "step": self.step,
                "substep": self.substep,
                "progress": self.progress,
                "step_progress": self.step_progress,
                "details": self.details,
            },
        )
```

## Solution

**Action:** Add `PaperGenerationProgressEvent` class to `events.py` after line 150 (after `GpuShortageEvent`).

**Pattern:** Follow existing event pattern:

1. Dataclass with `@dataclass(frozen=True)` decorator
2. Inherit from `BaseEvent`
3. Implement `type()` returning event type string
4. Implement `to_dict()` for serialization
5. Implement `persistence_record()` returning `(EventKind, Dict)` tuple

## Constraints Discovered

- Event class must be frozen dataclass (immutable)
- Must inherit from `BaseEvent`
- Must implement 3 methods: `type()`, `to_dict()`, `persistence_record()`
- EventKind literal already includes `"paper_generation_progress"` (line 8)
- Persistence layer expects exact field names matching DB schema

## Integration Points

- ✅ EventPersistenceManager → `_insert_paper_generation_progress()` (already handles the event)
- ✅ Database schema → `rp_paper_generation_events` table (already exists)
- ✅ API models → `ResearchRunPaperGenerationProgress` (already defined)
- ❌ Event class → **MISSING** (needs to be added)

## Why Tests Pass But Mypy Fails

- Python is dynamically typed - runtime doesn't check imports until used
- Mypy performs static analysis and detects the missing class at import time
- The `PaperGenerationProgressEvent` is imported but never defined, causing attr-defined errors
