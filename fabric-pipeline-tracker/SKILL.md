---
name: fabric-pipeline-tracker
description: >
  Use this skill to monitor and investigate Microsoft Fabric pipeline runs.
  Triggers include: checking pipeline status, investigating a failed run, listing
  recent runs, watching a live run, or exporting run details.
  Use when the user mentions a pipeline run, a run ID, "why did my pipeline fail",
  "Master_Orchestration", Fabric data pipeline status, or asks about notebook errors
  inside a pipeline.
  NOTE: Pipeline monitoring requires an active Fabric capacity. If commands fail
  with capacity-related errors, use the manage-fabric-capacities skill to resume
  the appropriate capacity first.
  NOT for: managing workspaces, deploying items, or Power BI-specific operations.
---

# Fabric Pipeline Tracker

Monitor Microsoft Fabric pipeline runs from the CLI using `track_pipeline.py`,
located at `~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py`.

> **Capacity requirement:** Pipeline runs and their activity logs are content
> operations — they require the workspace's Fabric capacity to be **Active**.
> `fab ls` works without capacity, but `track_pipeline.py` reads run history
> and activity outputs which need compute. If you see errors like "workspace
> unavailable" or "resource not accessible", check `manage-fabric-capacities`
> and resume the capacity first.

## Prerequisites

- Python 3.12+
- `rich` library: `pip install rich`
- `fab` CLI authenticated: `fab auth status`
- Azure CLI authenticated: `az account show`
- **Active Fabric capacity** for the target workspace

Assume all libraries are present, and authenticated, run the command, and when it fails then do the neccessary checks
---

## Basic Usage

```bash
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "<Workspace>" "<Pipeline>"
```

This shows the **latest run** by default.

### Examples

```bash
# Latest run of Master_Orchestration in Tourba - Production
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration"

# Latest run, compact output (errors + notebook URLs only — no params/lookups)
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" --compact

# Second most recent run
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" --run-selector 2

# Specific run by UUID
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --run-selector 80452338-7fab-4644-ab92-990e507cc5ef

# Live polling every 30 seconds
watch -n 30 python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" --compact

# Export run details to JSON
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --export /tmp/run.json

# Debug InvokePipeline activity inputs/outputs
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" --debug

# Clear metadata cache (workspaces/items are cached for 1 hour)
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py --clear-cache
```

---

## Arguments Reference

| Argument | Description |
|---|---|
| `workspace` | Fabric workspace display name (required unless `--clear-cache`) |
| `pipeline` | Data pipeline name (required unless `--clear-cache`) |
| `--run-selector N\|UUID` | `1` = latest (default), `2` = second most recent, or a run UUID |
| `--compact` | Hide params, lookups, SetVariable details — **errors and notebook URLs always shown** |
| `--export FILE.json` | Export run to JSON; suppresses terminal output |
| `--debug` | Dump raw input/output JSON for all InvokePipeline activities |
| `--format json` | Output JSON to stdout instead of the rich TUI |
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

### Notebook activities

For `TridentNotebook` activities, the script extracts and displays **clickable
Fabric UI URLs** directly from the pipeline activity output:

- **📸 snapshot** — Opens the notebook execution snapshot (code, cell outputs,
  errors, parameters as they existed at submission time). Constructed from the
  activity run ID, which maps 1:1 to the notebook job instance ID.
- **🔥 spark ui** — Opens the Spark monitoring page for the notebook session
  (available when the output contains `SparkMonitoringURL`).
- **📕 notebook error** — Shows the error returned inside the notebook result
  payload (distinct from the top-level pipeline activity error).
- **🏁 exit value** — Displays the exit value returned by the notebook (e.g.
  `mssparkutils.notebook.exit("...")`), useful for conditional branching.

These URLs are shown **even in `--compact` mode** so you can debug notebooks
without opening the Fabric portal.

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
| `capacity` / `not accessible` / `workspace unavailable` | Fabric capacity is **Paused** — see Capacity Recovery below |
| `compute` / `failed to connect` / `provisioning` | Capacity is still resuming or has been suspended |

---

## Capacity Recovery

If the script fails with capacity-related errors, the workspace's Fabric capacity
is likely paused. Pipeline monitoring requires an active capacity because it reads
run history and activity outputs, not just workspace metadata.

### Quick check

```bash
# List capacities and their states
az fabric capacity list --query '[].{name:name, resourceGroup:resourceGroup, state:state}' -o table
```

### Resume the capacity

Use the `manage-fabric-capacities` skill to:
1. Identify the correct capacity for the workspace
2. Resume it with `az fabric capacity resume`
3. Wait for `state: Active`
4. Retry the pipeline tracker command

**Example:**

```bash
# If "Tourba - Production" fails, resume its capacity
az fabric capacity resume \
  --resource-group "tourba-prod" \
  --capacity-name "tourbafcwesteuropeprod"

# Wait for Active
while [ "$(az fabric capacity show --resource-group "tourba-prod" --capacity-name "tourbafcwesteuropeprod" --query state -o tsv)" != "Active" ]; do
  sleep 10
done

# Retry pipeline monitoring
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration"
```

---

---

## Programmatic Manipulation with JSON and jq

When you need to filter, compare, extract, or programmatically process pipeline run data, always use `--format json` or `--export` combined with `jq` instead of parsing the rich TUI output.

### Export to JSON and query with jq

```bash
# Export a run to JSON
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --export /tmp/run.json

# Get top-level run properties
jq '{runId, status, durationInMs, message}' /tmp/run.json

# List all activity names and their statuses
jq '.runOutput.activities[] | {name, status, type, durationInMs}' /tmp/run.json

# Find only failed activities
jq '.runOutput.activities[] | select(.status == "Failed")' /tmp/run.json

# Extract error messages from all activities
jq '.runOutput.activities[] | select(.error | not | not) | {name, error}' /tmp/run.json

# Get ForEach iteration count
jq '.runOutput.activities[] | select(.type == "ForEach") | {name, iterationCount}' /tmp/run.json

# Get notebook activity Spark UI URLs
jq '.runOutput.activities[] | select(.type == "TridentNotebook") | {name, notebookUrl: .output.SparkMonitoringURL}' /tmp/run.json
```

### Compare two runs

```bash
# Export two runs
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --run-selector 1 --export /tmp/run1.json
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --run-selector 2 --export /tmp/run2.json

# Compare durations
jq -n --slurpfile r1 /tmp/run1.json --slurpfile r2 /tmp/run2.json \
  '[$r1[0], $r2[0]] | map({runId, status, durationInMs})'

# Find activities that changed status between runs
jq -n --slurpfile r1 /tmp/run1.json --slurpfile r2 /tmp/run2.json \
  '[$r1[0].runOutput.activities[], $r2[0].runOutput.activities[]]
   | group_by(.name)
   | map(select(length == 2 and .[0].status != .[1].status))
   | map({name, old: .[0].status, new: .[1].status})'
```

### Extract specific nested data

```bash
# Get all SetVariable values
jq '.runOutput.activities[] | select(.type == "SetVariable") | {name, value: .output.value}' /tmp/run.json

# Get Lookup query results (first 5 rows)
jq '.runOutput.activities[] | select(.type == "Lookup") | {name, rows: .output.value[0:5]}' /tmp/run.json

# Get all InvokePipeline child run IDs
jq '.runOutput.activities[] | select(.type == "InvokePipeline") | {name, childRunId: .output.pipelineRunId}' /tmp/run.json

# Flatten all activity durations into a CSV
jq -r '.runOutput.activities[] | [.name, .type, .status, .durationInMs] | @csv' /tmp/run.json
```

### Pipe JSON directly (no temp file)

```bash
# If the script supports --format json for stdout:
python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py "Tourba - Production" "Master_Orchestration" \
  --format json | jq '.runOutput.activities[] | {name, status}'

# Or use process substitution
jq '.status' <(python ~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py \
  "Tourba - Production" "Master_Orchestration" --export /dev/stdout)
```

> **jq is required:** Install with `brew install jq` (macOS) or `apt-get install jq` (Linux).

## Script Location

```
~/.agents/skills/fabric-pipeline-tracker/track_pipeline.py
```

The script is self-contained. It uses `fab` and `az rest` for all Fabric API
calls — no additional Python SDK required.
