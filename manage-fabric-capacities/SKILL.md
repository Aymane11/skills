---
name: manage-fabric-capacities
description: >
  Use this skill whenever the user wants to manage Microsoft Fabric capacities using the Azure CLI.
  Triggers include: listing, suspending, resuming, or checking Fabric capacities, checking name
  availability, or listing eligible SKUs.
  Use even if the user just asks "how do I pause my Fabric capacity", "resume capacity",
  "stop my Fabric capacity to save money", or mentions `az fabric` in passing.
  ALSO use when Fabric operations fail with "capacity not found", "workspace unavailable",
  "resource not accessible", or any error that suggests the capacity may be paused.
  NOT for: Fabric workspaces, items, pipelines (use fabric-pipeline-tracker), or the `fab` CLI tool.
---

# Azure Fabric Capacities Management

Manage Microsoft Fabric capacities using Azure CLI (`az`).

## Prerequisites

- Azure CLI v2.70.0+
- Microsoft.Fabric extension: `az extension add --name microsoft-fabric`

---

## Capacity Guard: When You Need a Running Capacity

| Operation | Needs Active Capacity? | Notes |
|-----------|------------------------|-------|
| `fab ls` (list workspaces) | No | Metadata API, always available |
| `fab ls <workspace>` (list items) | No | Item catalog is metadata-only |
| `fab get <item>` | No | Metadata reads work without capacity |
| `fab export <item>` | **Yes** | Reads item definition/content |
| `fab cp <lakehouse> <local>` | **Yes** | Reads file content from OneLake |
| `fab cp <local> <lakehouse>` | **Yes** | Writes file content to OneLake |
| `fab import <item>` | **Yes** | Creates/updates item content |
| `fab open <workspace>` | No | Just opens browser URL |
| Execute pipeline | **Yes** | Requires compute |
| Run notebook | **Yes** | Requires compute |
| Refresh semantic model | **Yes** | Requires compute |
| Query lakehouse tables (local DuckDB/polars) | **Yes** | Reads parquet files from OneLake |

> **Rule of thumb:** Metadata operations (`ls`, `get`, `exists`) work without capacity. Anything that reads or writes actual item **content** needs the capacity running.

---

## Commands

### List all capacities

```bash
az fabric capacity list
```

### List capacities names and resource groups only

```bash
az fabric capacity list --query '[].{name:name, resourceGroup:resourceGroup, state:state}' -o tsv
```

### Get capacity details

```bash
az fabric capacity show \
  --resource-group <resource-group> \
  --capacity-name <capacity-name>
```

### Suspend (pause) a capacity

```bash
az fabric capacity suspend \
  --resource-group <resource-group> \
  --capacity-name <capacity-name>
```

### Resume (activate) a capacity

```bash
az fabric capacity resume \
  --resource-group <resource-group> \
  --capacity-name <capacity-name>
```

### Check name availability

```bash
az fabric capacity check-name-availability \
  --location <location> \
  --name <capacity-name> \
  --type Microsoft.Fabric/capacities
```

### List eligible SKUs

```bash
az fabric capacity list-skus
```

---

## Capacity Guessing Logic

When the user wants to resume a capacity but doesn't specify which one, use this decision tree:

### Step 1: Check current workspace context

If the user has mentioned a workspace name, map it to a capacity:

| Workspace Name Pattern | Likely Capacity |
|------------------------|-----------------|
| Contains "Tourba" AND "Production" / "Prod" | `tourbafcwesteuropeprod` |
| Contains "Tourba" AND ("Staging" / "Dev" / "Test") | `tourbafcwesteuropestg` |
| Contains "Facilities" AND "Production" / "Prod" | `facilitiesfcwesteuropeprod` |
| Contains "Facilities" AND ("Staging" / "Dev" / "Test" / "Refactor") | `facilitiesfcwesteuropestg` |
| Contains "dataX" AND "Production" / "Prod" | `dataxfcwesteuropeprod` |
| Contains "dataX" AND ("Staging" / "Dev" / "Test") | `dataxfcwesteuropestg` |

> **Important:** These are heuristic mappings. Always verify with `az fabric capacity list` before acting.

### Step 2: If still ambiguous, present options

```
I found multiple capacities. Which one should I resume?

1. tourbafcwesteuropestg (Tourba staging/dev) — state: Paused
2. tourbafcwesteuropeprod (Tourba production) — state: Active
3. facilitiesfcwesteuropestg (Facilities staging/dev) — state: Paused
4. facilitiesfcwesteuropeprod (Facilities production) — state: Paused

Which capacity should I resume?
```

### Step 3: Resume and verify

After resuming, always verify the capacity reached `Active` state:

```bash
az fabric capacity show \
  --resource-group <resource-group> \
  --capacity-name <capacity-name> \
  --query "{name:name, state:state, provisioningState:provisioningState}"
```

Wait for `state: Active` before proceeding with content operations.

---

## Auto-Resume Workflow

When a Fabric operation fails due to a paused capacity, follow this workflow:

### 1. Detect the failure pattern

Common error messages that indicate a paused capacity:
- `"The capacity is not found or is not accessible"`
- `"Workspace unavailable"`
- `"Failed to connect to compute"`
- `"Resource not accessible"`
- Any error mentioning capacity state or provisioning

### 2. Check capacity state

```bash
# List all capacities with states
az fabric capacity list --query '[].{name:name, resourceGroup:resourceGroup, state:state}' -o table
```

### 3. Guess or select the capacity

Use the **Capacity Guessing Logic** above. If the workspace is known, map it. If multiple match, present options.

### 4. Resume the capacity

```bash
az fabric capacity resume \
  --resource-group "<guessed-resource-group>" \
  --capacity-name "<guessed-capacity-name>"
```

### 5. Wait and retry

```bash
# Poll every 10 seconds until Active
while true; do
  STATE=$(az fabric capacity show \
    --resource-group "<resource-group>" \
    --capacity-name "<capacity-name>" \
    --query "state" -o tsv)
  echo "State: $STATE"
  [ "$STATE" = "Active" ] && break
  sleep 10
done
```

> **Note:** Resume can take 30–120 seconds. Do not retry the original operation immediately.

### 6. Retry the original Fabric operation

Once `Active`, re-run the user's original command (e.g., `fab export`, `fab cp`, pipeline run).

---

## Common workflows

### Pause all active capacities

```bash
# Get all active capacities
az fabric capacity list --query '[?state=="Active"].{name:name, resourceGroup:resourceGroup}' -o tsv | \
while read -r name rg; do
  az fabric capacity suspend --resource-group "$rg" --capacity-name "$name"
done
```

### Resume all paused capacities

```bash
az fabric capacity list --query '[?state=="Paused"].{name:name, resourceGroup:resourceGroup}' -o tsv | \
while read -r name rg; do
  az fabric capacity resume --resource-group "$rg" --capacity-name "$name"
done
```

### Resume capacity for a specific workspace

```bash
WORKSPACE="Facilities - Staging Refactor"

# Guess capacity from workspace name
if echo "$WORKSPACE" | grep -qi "facilities"; then
  if echo "$WORKSPACE" | grep -qi "prod"; then
    CAP="facilitiesfcwesteuropeprod"
    RG="facilities-prod"
  else
    CAP="facilitiesfcwesteuropestg"
    RG="facilities-stg"
  fi
elif echo "$WORKSPACE" | grep -qi "tourba"; then
  if echo "$WORKSPACE" | grep -qi "prod"; then
    CAP="tourbafcwesteuropeprod"
    RG="tourba-prod"
  else
    CAP="tourbafcwesteuropestg"
    RG="tourba-dev"
  fi
fi

echo "Resuming $CAP..."
az fabric capacity resume --resource-group "$RG" --capacity-name "$CAP"
```

---

## State values

- `Active` - Capacity is running and ready for content operations
- `Paused` - Capacity is suspended; metadata ops work, content ops fail
- `Suspending` - In the process of pausing
- `Resuming` - In the process of resuming; wait before retrying operations

---

## Known Capacities

Use `az fabric capacity list` to get the current list. Known capacities:

| Capacity Name | Resource Group | Environment | Project |
|---------------|----------------|-------------|---------|
| tourbafcwesteuropestg | tourba-dev | staging | Tourba (staging and dev environments) |
| tourbafcwesteuropeprod | tourba-prod | production | Tourba (production environment) |
| facilitiesfcwesteuropestg | facilities-stg | staging | Facilities (staging and dev environments) |
| facilitiesfcwesteuropeprod | facilities-prod | production | Facilities (production environment) |

**Important**: This capacity list is not exhaustive. It includes only capacities for projects Facilities and Tourba.  
**Important**: The resource group name is NOT the same as the capacity name. Always use `az fabric capacity list` to find the correct resource group.

### Example: Resume Facilities Production Capacity

```bash
az fabric capacity resume --resource-group "facilities-prod" --capacity-name "facilitiesfcwesteuropeprod"
```

### Example: Pause Facilities Staging Capacity

```bash
az fabric capacity suspend --resource-group "facilities-stg" --capacity-name "facilitiesfcwesteuropestg"
```

---

## Integration with Other Fabric Skills

When using `fabric-cli`, `fabric-cli-core`, `fabric-cli-powerbi`, `fabric-lakehouse-files`, or `fabric-pipeline-tracker`:

1. If a content operation fails, check if the capacity is paused.
2. Use this skill to resume it.
3. Wait for `Active` state.
4. Retry the original operation.

**Example integrated flow:**

```bash
# 1. User tries to export a notebook
fab export "Facilities - Staging Refactor.Workspace/nb1.Notebook" -o /tmp/nb1 -f
# Fails: "Resource not accessible"

# 2. Check capacity state
az fabric capacity list --query '[?contains(name,"facilities")]'
# → facilitiesfcwesteuropestg is Paused

# 3. Resume
az fabric capacity resume --resource-group "facilities-stg" --capacity-name "facilitiesfcwesteuropestg"

# 4. Wait for Active
while [ "$(az fabric capacity show --resource-group "facilities-stg" --capacity-name "facilitiesfcwesteuropestg" --query state -o tsv)" != "Active" ]; do
  sleep 10
done

# 5. Retry export
fab export "Facilities - Staging Refactor.Workspace/nb1.Notebook" -o /tmp/nb1 -f
```