---
description: ⚡ Full workflow - Context → Research → Plan → Execute → Review
argument-hint: [feature description]
model: opus
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task
---

# Feature Implementation Workflow

Execute the full Context → Research → Plan → Execute → Review workflow.

## Feature Request
$ARGUMENTS

## Workflow

### Phase 0: Decision Context

**Gather historical context before starting:**

First, create task folder:
```bash
mkdir -p adr/tasks/$(date +%Y%m%d_%H%M%S)-{feature-slug}/
```

Then gather decision context:
```
Use the adr-decision-support-agent to gather context for: "$ARGUMENTS"
```

Output: `decision-brief.md` in task folder

**Review surfaced context:**
- Are there ADRs that constrain this work?
- Are there skills to apply?
- Is there similar past work to reference?

This context will guide research and planning.

---

### Phase 1: Research 🟣

**Delegate to adr-research-agent subagent:**

```
Use the adr-research-agent to explore: "$ARGUMENTS"
Context: Reference decision-brief.md for constraints and relevant ADRs
```

Wait for research.md output.

**Human checkpoint**: "Does this correctly understand the system?"
- ✅ Approved → Continue to Phase 2
- ❌ Adjust → Re-run research with corrections

---

### Phase 2: Planning 🔵

**Delegate to adr-planner-agent subagent:**

```
Use the adr-planner-agent to create implementation plan based on research.md
```

Wait for plan.md output.

**Human checkpoint** ⭐ **HIGHEST LEVERAGE**:
- Are file:line references correct?
- Do before/after snippets make sense?
- Is implementation order logical?
- Are edge cases handled?

- ✅ Approved → Continue to Phase 3
- ❌ Adjust → Re-run planning with corrections

---

### Phase 3: Execution 🟢

**Critical: Fresh context with plan only**

**Delegate to adr-executor-agent subagent:**

```
Use the adr-executor-agent to implement plan.md
```

The executor receives ONLY plan.md — no conversation history.
This ensures:
- No poisoned trajectory
- Plan is the contract
- Maximum context for implementation

---

### Phase 4: Review 🔍

**Validate changes against constraints:**

```
Use the adr-review-agent to check changes against decision-brief.md
```

The review agent:
- Reads git diff of changes made
- Checks against constraints from decision-brief.md
- Reports violations or passes

**Review output:**
- **PASS** → Continue to completion
- **WARNINGS** → Consider fixes, then continue
- **VIOLATIONS** → Must fix before completing

---

## Output Summary

After all phases:

```markdown
## ⚡ Feature Complete: {name}

### Phases
- 🧠 Context: ✅ Gathered
- 🟣 Research: ✅ Approved
- 🔵 Plan: ✅ Approved
- 🟢 Execute: ✅ Complete
- 🔍 Review: ✅ Passed

### Files Changed
- `{file}` — {change summary}

### Constraints Verified
- {constraint from decision-brief.md}

### Tests
- ✅ All tests passing

### Ready for PR
```

## Context Management

If context approaches 40% during any phase:
1. Complete current phase
2. Use `/adr-compact` to compress state
3. Resume with fresh context

## Novel Pattern?

If implementation reveals a reusable pattern:
```
/adr-save-skill {pattern-name}
```
