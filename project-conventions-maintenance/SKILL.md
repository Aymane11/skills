# Skill: Project Conventions Maintenance

Keep agent instruction files (AGENTS.md, CLAUDE.md, .gitignore) in sync with actual codebase changes.

## When to Load This Skill

**Activate when** any of the following occur:
- User mentions `AGENTS.md` is out of date
- User changed project structure, dependencies, or conventions and wants docs updated
- User asks to "update conventions", "sync agents.md", or "update project docs"
- New directories, modules, or files are added that should be in repo structure docs
- Version bumps, dependency changes, or build process changes occur
- New rules or workflows are established (e.g., "always use uv run", "never write Excel")
- User creates or modifies `.gitignore` entries
- User says things like "agents.md needs updating", "conventions changed", "document this rule"
- **Starting a new project or setting up conventions for the first time** — this skill handles the critical Step 0: establishing task tracking

**Do not activate for:**
- Code changes that don't affect conventions (bug fixes, features within existing patterns)
- Documentation unrelated to agent instructions (user docs, API docs)
- README updates (unless they affect agent behavior)

## Workflow

### 0. Establish Task Tracking (Critical — Do Not Skip)

**At the start of any project or when setting up conventions, ask the user:**

> "How do you want to track tasks for this project? Options:
> - **Local**: Taskwarrior (gitignored, fast, local-only) — see `taskwarrior-project-tracker` skill
> - **Azure DevOps**: Boards integration — see `azure-devops-sprint-manager` skill
> - **GitHub**: Issues and Projects
> - **Other**: Jira, Notion, Linear, etc.
>
> The essential rule is: **all work must be tracked somewhere**. No ad-hoc coding without a corresponding task."

**If user chooses local (Taskwarrior):**
- Set up `.taskrc` and `.task/` directory
- Document commands in AGENTS.md under "Task Tracking"
- Add `.task/` and `.taskrc` to `.gitignore`

**If user chooses Azure DevOps:**
- Reference `azure-devops-sprint-manager` skill for sprint/board setup
- Document work item creation process in AGENTS.md
- Ensure ADO project/board exists before work begins

**If user chooses GitHub Issues:**
- Document issue templates and labeling conventions
- Ensure repo has Issues enabled

**Default fallback:** If user has no preference or is unsure, recommend **Taskwarrior** (local, fast, zero setup overhead) and offer to migrate later.

**This decision must be documented in AGENTS.md under "Task Tracking" before any work begins.**

---

### 1. Read Current AGENTS.md

Always start by reading the current file to understand existing conventions:

```bash
cat AGENTS.md
```

### 2. Detect Drift

Compare AGENTS.md claims against actual code:

| AGENTS.md Claims | Check Against |
|-----------------|---------------|
| Repo structure diagram | `tree` or `ls -la` of actual directories |
| Version number | `pyproject.toml`, `__init__.py` |
| Build commands | Check if tools mentioned are installed (uv, pytest) |
| Dependencies listed | `pyproject.toml` dependencies |
| Module names | Actual file names in `src/` |
| Test locations | `find . -name "test_*.py"` |
| Gitignored files | `.gitignore` contents |

### 3. Update Rules

**When adding new conventions:**
- Add to "Key conventions" or create new section
- Include rationale (why this rule exists)
- Include example (what compliant code looks like)
- Include violation (what non-compliant code looks like)

**Example convention entry:**
```markdown
- **Prioritize source fixes over code fixes** — when Excel files have data quality issues 
  (e.g., numbers stored as text, formula errors `#VALUE!`, malformed dates), ask the business 
  team (owners of the source data) to fix/enforce proper formatting in Excel before writing 
  code to handle it. Only add data cleaning code when the fix is impractical at the source.
```

### 4. Update Structure

When directories or files move:

```markdown
## Repo structure

```
project/
├── new_directory/          # Added: <reason>
│   └── new_file.py
├── existing/               # Unchanged
└── moved_file.py           # Was in old/path/, moved because <reason>
```
```

### 5. Update Gitignore

When new artifacts are created that shouldn't be committed:

```gitignore
# New tool: Taskwarrior
.task/
.taskrc

# New dev tool
.mypy_cache/
```

### 6. Create CLAUDE.md Pointer

If `CLAUDE.md` doesn't exist, create it as a brief pointer:

```markdown
# CLAUDE.md

Project conventions in `AGENTS.md`.

Start there for:
- Working style (no over-engineering, ask before assuming)
- Coding style (minimalist, explicit, source-first)
- Task tracking (Taskwarrior workflow)
- Build/test commands

See `AGENTS.md` for full details.
```

### 7. Verify After Changes

After updating AGENTS.md:
- Run build commands to confirm they still work
- Check that new rules are actually followed in existing code
- Ensure `.gitignore` covers all generated artifacts

## Key Principles

- **AGENTS.md is the source of truth**: If code and docs disagree, docs are usually right (but fix the code too)
- **Update immediately**: When conventions change, update docs in the same session
- **Be explicit**: "No classes for simple data" is better than "use appropriate data structures"
- **Working style first**: Rules about *how* to work are more important than *what* to build
- **Gitignore tracks artifacts**: Every tool/generator should have its output ignored
- **Task tracking is non-negotiable**: All work must be tracked somewhere (Taskwarrior, ADO Boards, GitHub Issues, etc.) before coding begins

## Common Convention Categories

1. **Working Style** — how to approach problems
2. **Coding Style** — how to write code
3. **Task Tracking** — how to manage work
4. **Repo Structure** — where things live
5. **Build & Test** — how to verify changes
6. **Key Conventions** — specific rules (dependencies, secrets, modules)
7. **Deployment** — how to release
