---
name: track-pipeline
description: >
  Use this skill to monitor and investigate Microsoft Fabric pipeline runs.
  Triggers include: checking pipeline status, investigating a failed run, listing
  recent runs, watching a live run, or exporting run details. Use when the user
  mentions a pipeline run, a run ID, or asks why a pipeline failed.
  NOT for: managing workspaces, deploying items, or Power BI-specific operations.
---

# Track Pipeline Skill

Monitor Microsoft Fabric pipeline runs from the CLI using `track_pipeline.py`,
located at `~/.agents/skills/track-pipeline/track_pipeline.py`.

## Prerequisites

- Python 3.12+
- `rich` library: `pip install rich`
- `fab` CLI authenticated: `fab auth status`
- Azure CLI authenticated: `az account show`

Assume all libraries are present, and authenticated, run the command, and when it fails then do the neccessary checks
---

## Basic Usage

```bash
python ~/.agents/skills/track-pipeline/track_pipeline.py "<Workspace>" "<Pipeline>"
```

This shows the **latest run** by default.

### Examples

```bash
# Latest run of Master_Orchestration in Tourba - Production
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration"

# Latest run, compact output (errors only — no params/lookups)
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" --compact

# Second most recent run
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" --run-selector 2

# Specific run by UUID
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --run-selector 80452338-7fab-4644-ab92-990e507cc5ef

# Live polling every 30 seconds
watch -n 30 python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" --compact

# Export run details to JSON
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --export /tmp/run.json

# Debug InvokePipeline activity inputs/outputs
python ~/.agents/skills/track-pipeline/track_pipeline.py "Tourba - Production" "Master_Orchestration" --debug

# Clear metadata cache (workspaces/items are cached for 1 hour)
python ~/.agents/skills/track-pipeline/track_pipeline.py --clear-cache
```

---

## Arguments Reference

| Argument | Description |
|---|---|
| `workspace` | Fabric workspace display name (required unless `--clear-cache`) |
| `pipeline` | Data pipeline name (required unless `--clear-cache`) |
| `--run-selector N\|UUID` | `1` = latest (default), `2` = second most recent, or a run UUID |
| `--compact` | Hide params, lookups, SetVariable details — errors always shown |
| `--export FILE.json` | Export run to JSON; suppresses terminal output |
| `--debug` | Dump raw input/output JSON for all InvokePipeline activities |
| `--clear-cache` | Wipe the 1-hour metadata cache and exit |

---

## Output Anatomy

### Header panel

Shows pipeline name, status, run ID, start/end times, duration, error message
(top-level), and cache location.

### Activity tree

Each node follows this pattern:

```
<status-icon>  <activity-icon> <ActivityName>  ⏱ <duration>  <start> → <end>  🏢 <workspace>
  └── ⚠  <error message if any>
  └── ⚙  params  <key: value table>
```

**Status icons:** ✅ Succeeded/Completed · ❌ Failed · ▶ InProgress · 🚫 Cancelled · ⏭️ Skipped

**Activity icons:** 📓 Notebook · 🔗 InvokePipeline · 🔁 ForEach · 🔍 Lookup · 📝 SetVariable · 📋 Copy · ❓ If · 🔄 Until

### ForEach iterations

ForEach activities expand into an `↻ N iteration(s)` sub-node listing every
parallel/sequential child run.

### Invoked child pipelines

`InvokePipeline` activities recurse automatically: the child pipeline's own
activities are fetched and rendered as a nested sub-tree.

---

## Caching

Workspace and item metadata is cached for **1 hour** under
`~/.cache/track_pipeline/`. Activity run data is never cached (always live).

Run `--clear-cache` if workspace or item names have changed recently.

---

## Common Failure Patterns

| Error substring | Likely cause |
|---|---|
| `Failed to report consumption for this gateway` | On-premises data gateway is down or its host machine is offline |
| `Activity failed because an inner activity failed` | Look at the child activity for the real error |
| `Workspace '...' not found` | Workspace name mismatch or stale cache — run `--clear-cache` |
| `Only N run(s) available` | `--run-selector` index exceeds available history |

---

## Script Location

```
~/.agents/skills/track-pipeline/track_pipeline.py
```

The script is self-contained. It uses `fab` and `az rest` for all Fabric API
calls — no additional Python SDK required.
