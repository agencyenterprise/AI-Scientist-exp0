## 🔍 Merge Conflict Resolution: fake_runpod_server.py

## Summary

During merge commit `ab4e2d1`, a code block for `_store_tree_viz()` was incorrectly placed at the end of `_emit_paper_generation_flow()` where the required variables (`stage_index`, `stage_name`) are out of scope. This block should be inside the main loop in `_emit_fake_events()`.

## Code Paths Found

| File                                                          | Lines   | Purpose                                                           | Action                  |
| ------------------------------------------------------------- | ------- | ----------------------------------------------------------------- | ----------------------- |
| `server/app/services/research_pipeline/fake_runpod_server.py` | 608-611 | Misplaced `_store_tree_viz` call with wrong indentation and scope | remove                  |
| `server/app/services/research_pipeline/fake_runpod_server.py` | 416-506 | Main loop in `_emit_fake_events()` where variables are in scope   | verify has correct code |

## Root Cause

**Our branch (9e9e87e)**:

- Had `_emit_paper_generation_flow()` method (lines 480-575)
- Did NOT have any `_store_tree_viz()` calls

**Main branch (a51364b)**:

- Did NOT have `_emit_paper_generation_flow()` method
- Had `_store_tree_viz()` call at line 470-473 INSIDE the for loop in `_emit_fake_events()` where `stage_index` and `stage_name` are in scope

**Merge result (ab4e2d1)**:

- Git incorrectly placed the `_store_tree_viz()` block from main at the END of `_emit_paper_generation_flow()` (lines 608-611)
- Block has wrong indentation (extra indent level)
- Variables `stage_index` and `stage_name` are not in scope at this location

## Solution

Remove lines 608-611 entirely. They don't belong in `_emit_paper_generation_flow()`. The `_store_tree_viz()` call from main branch should already be correctly placed in the for loop of `_emit_fake_events()`.

## Integration Points

- `_emit_fake_events()` → calls `_emit_paper_generation_flow()` at line 510
- `_store_tree_viz()` → should be called within the main loop where `stage_index` and `stage_name` are defined (line 416)

## Constraints Discovered

- Variables must be in scope when used
- `_store_tree_viz()` requires `stage_index` parameter
- Python indentation must be consistent (no mixed tabs/spaces)
