---
description: 📝 Extract ADRs from commit history
argument-hint: [n|since-adr|interactive]
model: haiku
allowed-tools: Read, Glob, Grep, Bash(git:*), Write, Task
---

# Extract ADRs from Commits

Extract architecture decisions from git commit history and create ADR files.

## Arguments
$ARGUMENTS

## Mode Selection

**Parse argument:**
- Number (e.g., `5`) → Analyze last N commits
- `since-adr` → Since last ADR was created
- `interactive` → Pick from recent commits
- Empty → Ask user which mode

**If no argument provided, ask:**
```
Which mode for commit selection?
1. [n] - Analyze last N commits
2. [since-adr] - Since last ADR was created
3. [interactive] - Pick from recent commits

Enter [1/2/3]:
```

---

## Process

### Step 1: Gather Commits

**Mode: N commits**
```bash
git log -n $N --format="%H|%s|%b" --no-merges
```

**Mode: since-adr**
```bash
# Get last ADR creation time
LAST_ADR=$(ls -t adr/decisions/*.md 2>/dev/null | head -1)
# Get commits since that file was created
git log --since="$(stat -f "%Sm" -t "%Y-%m-%d" "$LAST_ADR" 2>/dev/null || echo "1 week ago")" --format="%H|%s|%b" --no-merges
```

**Mode: interactive**
```bash
# Show recent 20 commits for selection
git log -20 --oneline --no-merges
```
Then ask: "Enter commit hashes (space-separated) or range (abc..def):"

### Step 2: Count and Route

```bash
# Count commits gathered
COMMIT_COUNT=$(echo "$COMMITS" | wc -l)
```

**Routing decision:**
- `commits <= 10` → Single agent mode (Step 3a)
- `commits > 10` → Subagent mode (Step 3b)

---

### Step 3a: Single Agent Mode (<=10 commits)

Analyze all commits directly:

**For each commit, extract:**
1. **Decision signals** in message:
   - "decided to...", "chose...", "went with..."
   - "instead of...", "rather than..."
   - "because...", "due to..."
2. **Constraints**:
   - "never...", "always...", "must..."
3. **Problem/solution pairs**:
   - What was broken → How it was fixed

**In diffs, look for:**
- New configuration files (architectural choices)
- New patterns (file structure, naming conventions)
- Dependency changes with rationale
- API contract changes

**Skip commits that are:**
- Pure bug fixes with no architectural insight
- Documentation-only changes
- Dependency bumps without rationale
- Formatting/lint changes

**Cluster by topic:**
- Same domain area (auth, API, database, etc.)
- Related problem/solution
- Sequential commits addressing same issue

→ Continue to Step 4

---

### Step 3b: Subagent Mode (>10 commits)

**Batch commits (10 per batch):**
```bash
# Split commits into batches
echo "$COMMITS" | split -l 10
```

**Launch analyzer agents in parallel:**
```
For each batch:
  Use adr-commit-analyzer-agent with batch of commit hashes
```

**Collect compressed findings from all analyzers.**

**Launch clusterer agent:**
```
Use adr-commit-clusterer-agent with all compressed findings
```

→ Continue to Step 4

---

### Step 4: Present Groupings for Approval

**Display proposed ADRs:**

```markdown
## Proposed ADR Groupings

| # | Commits | Proposed ADR Title | Signal |
|---|---------|-------------------|--------|
| 1 | abc123, def456 | API error handling strategy | rationale |
| 2 | ghi789 | Database connection pooling | constraint |

### Excluded (no decision signal)
- jkl012: "Fix typo in README"
- mno345: "Update deps"

---

**Actions:**
- `approve` - Create ADRs as shown
- `merge 1,2` - Combine groups into single ADR
- `split 1` - Break a group apart
- `drop 2` - Exclude group from ADR creation
- `rename 1 "New title"` - Change proposed title
- `cancel` - Abort without creating ADRs

Enter action:
```

**Process user action and loop until `approve` or `cancel`.**

---

### Step 5: Deduplication Check

Before creating, check for overlap:
```bash
grep -rli "KEYWORDS" adr/decisions/ 2>/dev/null
```

**If overlap found:**
```
Warning: Potential overlap with existing ADR:
- adr/decisions/20251201-similar-topic.md

Options:
1. Create anyway (new perspective)
2. Skip this group
3. View existing ADR

Enter [1/2/3]:
```

---

### Step 6: Create ADR Files

For each approved group:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TITLE=$(echo "$PROPOSED_TITLE" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')
```

Write to `adr/decisions/${TIMESTAMP}-${TITLE}.md`:

```markdown
# {YYYYMMDD_HHMMSS}-{short-title}

## Status
Accepted

## Context
{Problem extracted from commits}

**Source commits:**
- {hash}: {subject}

## Decision
{What was chosen and why — extracted from commit messages}

## Consequences

### Positive
{Benefits mentioned or implied}

### Negative
{Trade-offs mentioned or implied}

### Constraints
{Any "never/always/must" statements discovered}
```

---

## Output Summary

```markdown
## 📝 ADRs Created from Commits

**Mode:** {n|since-adr|interactive}
**Commits analyzed:** {count}
**Groups found:** {n}
**ADRs created:** {n}

### Created ADRs

| File | Title | Source Commits |
|------|-------|----------------|
| `20251212_143000-{title}.md` | {Title} | abc1234, def5678 |

### Skipped
- {n} commits had no decision signal
- Group {n} dropped by user

### Next Steps
- Review created ADRs for accuracy
- Run `/adr-review` to check current code against new constraints
```

---

## Error Handling

**No commits found:**
```
No commits found for the specified range.
- If using `n`: try a larger number
- If using `since-adr`: no ADRs exist yet, use `n` mode
- If using `interactive`: ensure branch has commits
```

**No decision signals:**
```
Analyzed {n} commits but found no architectural decisions.

Commits appear to be routine changes:
- Bug fixes without rationale
- Documentation updates
- Dependency bumps

Options:
1. Force analysis (may create low-value ADRs)
2. Select different commits
3. Cancel

Enter [1/2/3]:
```

---

## Token Budget

| Phase | Target |
|-------|--------|
| Mode selection | 50 tokens |
| Commit gathering | 100 tokens |
| Analysis display | 400 tokens |
| User interaction | 100 tokens |
| **Total per cycle** | **~650 tokens** |
