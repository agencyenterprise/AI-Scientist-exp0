---
description: 📋 Document a code pattern as an ADR
argument-hint: [pattern description]
model: sonnet
allowed-tools: Read, Glob, Grep, Bash(grep:*), Bash(find:*), Write
---

# Document Pattern as ADR

Analyze a code pattern in the codebase, ask clarifying questions about the "why", and generate an ADR documenting the decision.

## Pattern to Document
$ARGUMENTS

## Why This Command?

Code shows **what** a pattern does, but not **why** it exists:
- `/adr-research` finds patterns but doesn't create ADRs
- `/adr-from-commits` only works if decision is in commit history
- This command bridges the gap: research + user input → ADR

---

## Process

### Step 1: Check for Existing Documentation

```bash
# Check if this pattern is already documented
grep -rli "$ARGUMENTS" adr/decisions/ 2>/dev/null
grep -rli "$ARGUMENTS" .claude/skills/*/SKILL.md 2>/dev/null
```

**If found:**
```
Existing documentation found:
- adr/decisions/20251201-similar-pattern.md

Options:
1. View existing documentation
2. Create new ADR anyway (different aspect)
3. Cancel

Enter [1/2/3]:
```

---

### Step 2: Research the Pattern

**Search for pattern instances:**

```bash
# Find files containing pattern keywords
grep -rn "PATTERN_KEYWORDS" . --include="*.ts" --include="*.tsx" --include="*.js" --include="*.py" | head -30

# Find related files by name
find . -type f -name "*PATTERN*" 2>/dev/null | head -10

# Trace usage patterns
grep -rn "import.*PATTERN\|from.*PATTERN" . --include="*.ts" | head -20
```

**For each instance found:**
- Read the specific function/block (not entire file)
- Note exact line numbers
- Identify what the pattern accomplishes
- Look for variations or inconsistencies

---

### Step 3: Present Findings

```markdown
## Pattern Analysis: {pattern name}

### Instances Found

| File | Lines | Usage | Consistent? |
|------|-------|-------|-------------|
| `src/api/route.ts` | 45-60 | {what it does} | ✅ |
| `src/api/other.ts` | 23-38 | {what it does} | ✅ |
| `src/legacy/old.ts` | 12-20 | {variation} | ⚠️ different |

### Pattern Description
{What the pattern does, based on code analysis}

### Variations Found
- {Any inconsistencies or alternative implementations}
- {Legacy code that doesn't follow the pattern}

### Integration Points
- Connects to: {other systems/modules}
- Called by: {callers}
- Depends on: {dependencies}
```

---

### Step 4: Ask Clarifying Questions

**Present questions to user:**

```markdown
To document this pattern properly, I need to understand the reasoning:

### 1. Why this approach?
What problem does this pattern solve? Why was it chosen over alternatives?

### 2. Alternatives considered?
Were other approaches tried or rejected? What were they?

### 3. Trade-offs?
What are the downsides or constraints of this pattern?

### 4. Exceptions?
Are there cases where this pattern should NOT be used?

### 5. Historical context?
When was this introduced? Was there a specific incident or requirement?

Please answer these questions so I can create a complete ADR.
```

**Wait for user response before proceeding.**

---

### Step 5: Generate ADR

Based on research findings + user answers, create:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TITLE=$(echo "$PATTERN_NAME" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')
```

Write to `adr/decisions/${TIMESTAMP}-${TITLE}.md`:

```markdown
# {YYYYMMDD_HHMMSS}-{pattern-name}

## Status
Accepted

## Context
{From research: what the pattern does and where it's used}

{From user: the problem it was solving, historical context}

## Decision
{Pattern description synthesized from research}

{From user: why this approach was chosen over alternatives}

### Implementation
The pattern is implemented in:
- `{file}:{lines}` — {description}
- `{file}:{lines}` — {description}

### Example
```{lang}
{Representative code example from research}
```

## Consequences

### Positive
{Benefits from user input}

### Negative
{Trade-offs from user input}

### Constraints
- {When to use this pattern}
- {When NOT to use this pattern}
- {Any hard rules: "never...", "always..."}

## Exceptions
{Cases where this pattern doesn't apply, from user input}

## Related
- {Related ADRs if any}
- {Related skills if any}
```

---

### Step 6: Confirm and Save

**Show preview to user:**

```markdown
## Preview: ADR to be created

**File:** `adr/decisions/{timestamp}-{title}.md`

{Show full ADR content}

---

**Actions:**
- `save` — Create the ADR
- `edit` — Modify before saving
- `cancel` — Discard

Enter action:
```

---

## Output Summary

```markdown
## 📋 Pattern Documented: {name}

### ADR Created
`adr/decisions/20251212_150000-{pattern-name}.md`

### Pattern Instances
Found in {n} files:
- `src/api/route.ts:45-60`
- `src/api/other.ts:23-38`

### Variations Noted
{Any inconsistencies flagged for attention}

### Next Steps
- Review ADR for accuracy
- Run `/adr-review` to check code against new constraints
- Consider `/adr-save-skill` if this is a repeatable procedure
- Fix any inconsistent implementations found
```

---

## Quality Checklist

Before completing:
- [ ] All pattern instances found and documented
- [ ] User answered clarifying questions
- [ ] ADR follows standard format
- [ ] Code examples are accurate with file:line refs
- [ ] Constraints are clearly stated
- [ ] Exceptions are documented

---

## Token Budget

| Phase | Target |
|-------|--------|
| Research | 300 tokens |
| Findings display | 200 tokens |
| Questions | 100 tokens |
| ADR generation | 400 tokens |
| **Total** | **~1000 tokens** |
