---
description: 🚀 Initialize agent system for this codebase
model: opus
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

# Initialize Project Agent System

You are the **Init Agent**. Your job is to analyze this codebase and customize the agent system.

## Process

### Step 1: Scan Project Structure

```bash
# Discover structure
find . -type d -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' | head -50

# Find source directories  
ls -la src/ app/ lib/ server/ packages/ 2>/dev/null || echo "Non-standard structure"
```

### Step 2: Detect Tech Stack

Analyze `package.json`, `Cargo.toml`, `requirements.txt`, `go.mod`, etc.

Identify:
- **Framework**: Next.js, React, Vue, FastAPI, etc.
- **Language**: TypeScript, Python, Rust, Go
- **Database**: Prisma, Drizzle, SQLAlchemy
- **State**: Zustand, Redux, React Query
- **Testing**: Vitest, Jest, pytest
- **Styling**: Tailwind, CSS Modules

### Step 3: Identify Patterns

Sample existing code to discover:
- File organization patterns
- Component/module structure
- API patterns
- Testing patterns  
- Naming conventions

### Step 4: Update Configuration

Update these files with project-specific info:

1. **CLAUDE.md** — Add stack and structure to Project Info section
2. **`.claude/skills/adr-research-codebase/SKILL.md`** — Update folder paths
3. **`.claude/skills/adr-research-codebase/patterns.md`** — Document discovered patterns
4. **`adr/decisions/YYYYMMDD_HHMMSS-init-project.md`** — Create setup ADR

## Output Format

```markdown
## 🚀 Project Analysis Complete

### Stack Detected
- **Framework**: {framework}
- **Language**: {language}
- **Database**: {database}
- **State**: {state management}
- **Testing**: {test framework}

### Structure Discovered
| Folder | Purpose |
|--------|---------|
| `{path}` | {purpose} |

### Patterns Identified
- {pattern 1}
- {pattern 2}

### Files Updated
- ✅ CLAUDE.md — Added project info
- ✅ adr-research-codebase/SKILL.md — Configured paths
- ✅ patterns.md — Documented patterns
- ✅ Created setup ADR

### Next Steps
Run `/adr-research [topic]` to explore any area of the codebase.
```

## Error Handling

- No package.json? → Ask about project type
- Unusual structure? → Ask for clarification
- Multiple frameworks? → Ask which is primary
