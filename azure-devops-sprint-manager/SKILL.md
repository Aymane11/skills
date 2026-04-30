---
name: azure-devops-sprint-manager
description: Create new sprints (iterations) in Azure DevOps and populate them with user stories. Use when the user wants to create a sprint, add user stories to a sprint, plan a sprint, or set up a new iteration in Azure DevOps.
---

# Azure DevOps Sprint Manager

Create and populate sprints in Azure DevOps using the Azure CLI.

## Prerequisites

```bash
az extension add --name azure-devops
az devops configure --list  # Verify org/project defaults
```

## Your Job

When invoked, you must:

1. **Collect all required info** — Ask the user for anything missing before running a single command. Do not invent or assume values.
2. **Create the sprint** at the project level with start/end dates, then assign it to the team.
3. **Create user stories** inside that sprint.
4. **Report results** — Print a summary table with sprint dates and each story's ID + title.

---

## Required Information — Ask Before Proceeding

Collect everything in a **single message** listing all missing fields at once. Never ask one question, wait, then ask another.

### Sprint fields (all required)

| Field | How to get it |
|---|---|
| **Organization** | Check `az devops configure --list`; ask if not set |
| **Project** | Check `az devops configure --list`; ask if not set |
| **Team name** | Run `az devops team list --project {project} --output table`; present options if ambiguous |
| **Sprint name** | Must come from the user (e.g. "Sprint 9") |
| **Start date** | Must come from the user (format: YYYY-MM-DD) |
| **End date** | Must come from the user (format: YYYY-MM-DD) |

### User story fields

| Field | Required? | Notes |
|---|---|---|
| **Title** | Yes — for each story | Ask for all titles upfront |
| **Story points** | Optional | Ask once: "Do you want to set story points?" |
| **Assignee** | Optional | Ask once: "Should stories be assigned to someone?" |
| **Description** | Optional | Ask once: "Any description or acceptance criteria?" |
| **Priority** | Optional | 1=Critical, 2=High, 3=Medium, 4=Low |

### Example opening question (when nothing is provided)

> To create the sprint I need a few details:
> - **Sprint name** (e.g. "Sprint 9")
> - **Start date** (YYYY-MM-DD)
> - **End date** (YYYY-MM-DD)
> - **User stories** — list each title, and optionally story points, assignee, priority
>
> The project is `dataX` and team is `dataX Team` — confirm or correct these.

---

## Step-by-Step Workflow

### 1. Resolve org/project/team

```bash
# Check what defaults are already configured
az devops configure --list

# If not set, configure them
az devops configure --defaults organization=https://dev.azure.com/{org} project={project}
```

To find the team name when not provided by the user:
```bash
az devops team list --project {project} --output table
```

### 2. Determine the sprint path

Sprint paths follow the pattern: `{project}\Iteration\{SprintName}`

List existing iterations to understand naming conventions and avoid collisions:
```bash
az boards iteration project list --project {project} --output table
```

### 3. Create the sprint at project level

```bash
az boards iteration project create \
  --name "{SprintName}" \
  --path "{project}\\Iteration" \
  --start-date "YYYY-MM-DD" \
  --finish-date "YYYY-MM-DD" \
  --project {project}
```

This returns a JSON object — capture the `identifier` (UUID) field. You need it for the next step.

### 4. Assign the sprint to the team

Use `--id` with the UUID from step 3 (NOT `--path`):

```bash
az boards iteration team add \
  --team "{team-name}" \
  --id "{iteration-uuid}" \
  --project {project}
```

### 5. Create user stories in the sprint

Create each story one at a time. The `--iteration` flag must use the full path:

```bash
az boards work-item create \
  --title "{Story Title}" \
  --type "User Story" \
  --iteration "{project}\\Sprint {N}" \
  --project {project} \
  --output json
```

Optional fields to add when the user provides them:
- `--assigned-to "email@example.com"` — assignee
- `--description "..."` — acceptance criteria / description
- `--fields "Microsoft.VSTS.Scheduling.StoryPoints=5"` — story points
- `--fields "Microsoft.VSTS.Common.Priority=2"` — priority (1=high, 4=low)

To set multiple fields at once:
```bash
az boards work-item create \
  --title "{Story Title}" \
  --type "User Story" \
  --iteration "{project}\\{SprintName}" \
  --project {project} \
  --fields "Microsoft.VSTS.Scheduling.StoryPoints=3" "Microsoft.VSTS.Common.Priority=2"
```

### 6. Verify

```bash
# Confirm sprint is visible for the team
az boards iteration team list --team "{team-name}" --project {project} --output table

# Confirm stories landed in the sprint
az boards iteration team list-work-items \
  --team "{team-name}" \
  --path "{project}\\{SprintName}" \
  --project {project} \
  --output table
```

---

## Common Mistakes to Avoid

- **`az boards iteration team add` requires `--id` (UUID), not `--path`**. Always capture the UUID from the `iteration project create` output.
- **Sprint path separator is `\\` in bash strings** (`{project}\\Iteration\\{SprintName}`).
- **`--iteration` in `work-item create` uses the short path** (`{project}\\{SprintName}`), not the full `\Iteration\` path.
- If the sprint already exists at project level, skip step 3 and go straight to step 4. List existing iterations first to check.

---

## Example: Full End-to-End

```bash
# 1. Create sprint
SPRINT_JSON=$(az boards iteration project create \
  --name "Sprint 9" \
  --path "dataX\\Iteration" \
  --start-date "2026-05-11" \
  --finish-date "2026-05-22" \
  --project dataX \
  --output json)

SPRINT_ID=$(echo "$SPRINT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['identifier'])")

# 2. Assign to team
az boards iteration team add \
  --team "dataX Team" \
  --id "$SPRINT_ID" \
  --project dataX

# 3. Create user stories
az boards work-item create \
  --title "As a user, I can reset my password" \
  --type "User Story" \
  --iteration "dataX\\Sprint 9" \
  --project dataX \
  --fields "Microsoft.VSTS.Scheduling.StoryPoints=3"

az boards work-item create \
  --title "As an admin, I can view audit logs" \
  --type "User Story" \
  --iteration "dataX\\Sprint 9" \
  --project dataX \
  --fields "Microsoft.VSTS.Scheduling.StoryPoints=5"
```

---

## Output Format

After completing all steps, summarize results like this:

```
Sprint created: Sprint 9 (2026-05-11 → 2026-05-22)
Assigned to: dataX Team

User Stories created:
  #1042  As a user, I can reset my password       [3 pts]
  #1043  As an admin, I can view audit logs        [5 pts]
```
