# Skill: Taskwarrior Project Tracker Setup

Set up Taskwarrior for local, gitignored task tracking as an alternative to GitHub Issues or Jira.

## When to Load This Skill

**Activate when** any of the following occur:
- User wants to set up task tracking for a project
- User mentions "todo", "task management", "backlog", or "tracking tasks"
- User wants gitignored task tracking (no commits for task changes)
- User is switching from GitHub Issues to local tracking
- User mentions "how do I track tasks", "taskwarrior", or "todo.txt"
- User wants per-project task databases

**Do not activate for:**
- GitHub/Jira/Azure DevOps integration (use those specific skills)
- Simple one-off reminders (use system tools)

## Workflow

### 1. Installation

```bash
brew install task
```

### 2. Project-Local Configuration

Create in project root:

```bash
mkdir -p .task
```

Create `.taskrc`:

```
# Local Taskwarrior config for <project-name>
data.location=/absolute/path/to/project/.task
```

### 3. Usage Patterns

**Basic commands:**
```bash
# From project root:
task rc:.taskrc list              # all pending tasks
task rc:.taskrc next             # most urgent
task rc:.taskrc add project:backlog.p1 priority:H "Task description +TAG #id"
task rc:.taskrc <id> done         # mark complete
task rc:.taskrc summary          # project overview
```

**Shell alias (recommended):**
```bash
# Add to .zshrc:
alias t='task rc:.taskrc'
```

### 4. Conventions

**Projects:**
- `backlog.p1` — Quality/risk tasks
- `backlog.silver` — Data cleaning/normalization
- `backlog.p2` — Polish/refactoring
- `backlog.wontfix` — Explicitly decided against
- `backlog.done` — Completed tasks

**Priorities:**
- `H` — High (blocking or critical)
- `M` — Medium (important, not urgent)
- `L` — Low (nice to have)

**Tags:**
- `@silver`, `@testing`, `@sharepoint`, `@fabric`, `@build`, etc.
- Use for filtering and cross-cutting concerns

**Task IDs:**
- Include `+BACKLOG #<number>` for cross-reference to other tracking systems
- Include `@context` for filtering

### 5. Bulk Import from Markdown

If converting an existing markdown backlog:

```bash
# For each open task:
task rc:.taskrc add project:backlog.p1 priority:M "Description +BACKLOG #15 @context"

# Mark done tasks:
task rc:.taskrc <id> done
```

### 6. Git Integration

Add to `.gitignore`:
```gitignore
# Taskwarrior local database
.task/
.taskrc
```

The database is purely local — no commits, no push, no merge conflicts.

## Key Principles

- **Local only**: Database lives in `.task/`, never committed
- **One task at a time**: Check `task next` before starting work
- **Immediate updates**: Mark done as soon as task completes
- **Discovered work**: Add subtasks immediately when found
- **No ad-hoc work**: Every code change needs a tracked task

## Comparison with Other Tools

| Tool | When to Use | Drawbacks |
|------|-------------|-----------|
| Taskwarrior | Local, fast, gitignored | No web UI, no team sharing |
| GitHub Issues | Team collaboration, web UI | Network required, commits noisy |
| Jira | Enterprise, complex workflows | Heavy, expensive, slow |
| todo.txt | Simple text files | No built-in prioritization/reports |
