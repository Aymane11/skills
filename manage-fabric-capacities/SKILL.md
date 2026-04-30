---
name: manage-fabric-capacities
description: >
  Use this skill whenever the user wants to manage Microsoft Fabric capacities using the Azure CLI.
  Triggers include: listing, suspending, resuming, or checking Fabric capacities, checking name
  availability, or listing eligible SKUs. Use even if the user just asks "how do I pause my Fabric
  capacity" or mentions az fabric in passing.
  NOT for: Fabric workspaces, items, pipelines, or the fab CLI tool.
---

# Azure Fabric Capacities Management

Manage Microsoft Fabric capacities using Azure CLI (`az`).

## Prerequisites

- Azure CLI v2.70.0+
- Microsoft.Fabric extension: `az extension add --name microsoft-fabric`

## Commands

### List all capacities

```bash
az fabric capacity list
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

## Common workflows

### Pause all active capacities

```bash
# Get all capacities
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

## State values

- `Active` - Capacity is running
- `Paused` - Capacity is suspended
- `Suspending` - In the process of pausing
- `Resuming` - In the process of resuming