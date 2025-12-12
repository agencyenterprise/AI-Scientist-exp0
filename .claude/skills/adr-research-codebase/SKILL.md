---
name: adr-research-codebase
description: Explore this codebase efficiently with structured search
allowed-tools: Read, Glob, Grep, Bash(grep:*), Bash(find:*), Bash(cat:*), Bash(head:*)
---

# ADR Research Codebase Skill

## When to Use
- Understanding existing code before changes
- Tracing data flows
- Finding where functionality lives
- Discovering patterns and conventions

## Search Areas

<!-- Customize these paths after /init -->

| Area | Path | Contains |
|------|------|----------|
| Components | `src/components/` | React components |
| Hooks | `src/hooks/` | Custom hooks |
| Stores | `src/stores/` | State management |
| API | `src/api/` | API routes/calls |
| Utils | `src/utils/` | Helper functions |
| Types | `src/types/` | TypeScript types |

## Process

### Step 1: Keyword Search
```bash
# Find topic in code
grep -rn "TOPIC" src/ --include="*.ts" --include="*.tsx" | head -30
```

### Step 2: File Discovery
```bash
# Find files by name
find . -type f -name "*TOPIC*" -not -path "*/node_modules/*" | head -10
```

### Step 3: Import Tracing
```bash
# Trace imports/exports
grep -rn "export.*TOPIC\|import.*TOPIC" src/ | head -20
```

### Step 4: Deep Dive
For each key file:
1. Read specific section (not whole file)
2. Note exact line numbers
3. Trace to integration points

## Output Requirements

Every finding must include:
- File path
- Line numbers
- Action classification (modify/reference)

See `patterns.md` for codebase-specific patterns.

## Anti-Patterns
- ❌ Reading entire files
- ❌ Prose descriptions without line refs
- ✅ File:line precision
- ✅ Dense, compressed output
