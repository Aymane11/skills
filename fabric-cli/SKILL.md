---
name: fabric-cli
description: >
  Use this skill whenever the user wants to interact with Microsoft Fabric using the `fab` CLI tool locally.
  Triggers include: installing or configuring the Fabric CLI, authenticating to a Fabric tenant,
  listing workspaces or their contents, exporting or importing Fabric items, inspecting or querying
  item properties, copying, moving, or deleting items. Use this skill even if the user just asks
  "how do I use fab", "how do I list my workspaces", or mentions fabric-cli in passing.
  NOT for: fabric-cicd, deployment pipelines, or CI/CD automation.
---

# Microsoft Fabric CLI (`fab`) Skill

The `fab` CLI is a cross-platform command-line tool for navigating, scripting, and automating
Microsoft Fabric environments locally. It exposes a file-system-style interface over workspaces
and items.

## Installation

```bash
pip install ms-fabric-cli           # install
pip install --upgrade ms-fabric-cli # upgrade
fab --version                       # verify
```

Requires Python ≥ 3.12. Works on Windows, macOS, and Linux.

---

## Authentication

### Check auth status
```bash
fab auth status
```

### Interactive (browser — recommended for local use)
```bash
fab auth login
# select "Interactive with a web browser" when prompted
```

### Service Principal — client secret
```bash
fab auth login -u <client_id> -p <client_secret> --tenant <tenant_id>
```

### Service Principal — certificate
```bash
fab auth login -u <client_id> --certificate /path/to/cert.pem --tenant <tenant_id>
# password-protected cert:
fab auth login -u <client_id> --certificate /path/to/cert.pfx -p <cert_password> --tenant <tenant_id>
```

### Managed Identity
```bash
fab auth login --identity                 # system-assigned
fab auth login --identity -u <client_id>  # user-assigned
```

---

## Path Convention

All workspace/item paths follow a UNIX-like convention:

```
/                                         # root — all workspaces
/<name>.Workspace                         # a workspace
/<name>.Workspace/<item>.<Type>           # an item inside a workspace
/<name>.Workspace/<item>.<Type>/...       # sub-path within an item
```

**Supported item types:** `Notebook`, `Report`, `SemanticModel`, `DataPipeline`,
`SparkJobDefinition`, `Lakehouse`, `KQLDatabase`, `KQLQueryset`, `KQLDashboard`,
`Eventhouse`, `Eventstream`, `MirroredDatabase`, `Reflex`, `MountedDataFactory`,
`CopyJob`, `VariableLibrary`, `Environment`

---

## Listing Workspaces and Their Contents

```bash
# list all workspaces
fab ls

# detailed list of all workspaces
fab ls -l

# list all workspaces including personal/hidden
fab ls -l -a

# list items in a workspace
fab ls ws1.Workspace

# detailed item list
fab ls ws1.Workspace -l

# detailed list including all items
fab ls ws1.Workspace -la

# filter items by name using JMESPath
fab ls ws1.Workspace -q "[].name"
fab ls ws1.Workspace -q "[].{name:name,id:id}"
fab ls ws1.Workspace -q "[?contains(name, 'Notebook')]"

# filter items by type (shell pipe)
fab ls ws1.Workspace -l | grep "\.Report"
```

---

## Inspecting Items with `get` and JMESPath

`fab get` retrieves item metadata as JSON. Use `-q` with a JMESPath expression to target
specific fields.

```bash
# get full workspace metadata
fab get ws1.Workspace

# get workspace ID only
fab get ws1.Workspace -q id

# get a specific item
fab get ws1.Workspace/nb1.Notebook

# verbose output (full JSON)
fab get ws1.Workspace/rep1.Report -v

# query a nested property
fab get ws1.Workspace/lh1.Lakehouse -q properties.sqlEndpointProperties

# save query result to file
fab get ws1.Workspace/lh1.Lakehouse -q properties.sqlEndpointProperties -o /tmp
fab get ws1.Workspace -q sparkSettings -o /tmp

# check if a workspace or item exists (exit 0 = exists)
fab exists ws1.Workspace
fab exists ws1.Workspace/nb1.Notebook
```

---

## Setting / Updating Properties

```bash
# rename a workspace
fab set ws1.Workspace -q displayName -i ws2

# update workspace description
fab set ws1.Workspace -q description -i "New description"

# update a nested spark setting
fab set ws1.Workspace -q sparkSettings.environment.runtimeVersion -i 1.2

# set a complex nested value (JSON string)
fab set ws1.Workspace -q sparkSettings.pool.defaultPool -i '{"name":"Starter Pool","type":"Workspace"}'

# rename an item
fab set ws1.Workspace/nb1.Notebook -q displayName -i "Updated Notebook Name"

# update item description
fab set ws1.Workspace/lh1.Lakehouse -q description -i "Production data lakehouse"

# bind a report to a semantic model
fab set ws1.Workspace/rep1.Report -q semanticModelId -i "00000000-0000-0000-0000-000000000000"
```

---

## Exporting Items (Fabric → local)

```bash
# export a single item to a local directory
fab export ws1.Workspace/nb1.Notebook -o /tmp/export/

# export an entire workspace
fab export ws1.Workspace -o /tmp/export/

# export all items, skip confirmation
fab export ws1.Workspace -o /tmp/export/ -a -f

# export to a Fabric lakehouse path
fab export ws1.Workspace/nb1.Notebook -o /ws1.Workspace/lh1.Lakehouse/Files/exports
```

> **Note:** Sensitivity labels are **not** exported. On Windows, certain characters in item
> names are invalid as folder names — rename before exporting if needed.

---

## Importing Items (local → Fabric)

```bash
# import a single item (overwrites if it already exists with -f)
fab import ws1.Workspace/nb1.Notebook -i /tmp/export/nb1.Notebook -f

# import a notebook from a Python file
fab import ws1.Workspace/nb1.Notebook -i /tmp/nb1.py --format .py -f

# import from a local path (no overwrite — will prompt if item exists)
fab import ws1.Workspace/nb1_imported.Notebook -i /tmp/exports/nb1.Notebook
```

**Importable item types:** `Notebook`, `SparkJobDefinition`, `DataPipeline`, `Report`,
`SemanticModel`, `KQLDatabase`, `KQLQueryset`, `KQLDashboard`, `Eventhouse`, `Eventstream`,
`MirroredDatabase`, `Reflex`, `MountedDataFactory`, `CopyJob`, `VariableLibrary`, `Environment`

---

## Copying and Moving Items

```bash
# copy an item within the same workspace
fab cp ws1.Workspace/nb1.Notebook ws1.Workspace/nb1_copy.Notebook

# copy to a different workspace
fab cp ws1.Workspace/nb1.Notebook ws2.Workspace/nb1.Notebook

# copy a workspace (all its items)
fab cp ws1.Workspace ws2.Workspace

# move an item to a different workspace
fab mv ws1.Workspace/nb1.Notebook ws2.Workspace

# move and rename
fab mv ws1.Workspace/nb1.Notebook ws2.Workspace/nb_renamed.Notebook
```

> `-f` skips overwrite confirmation. Sensitivity labels are **not** copied.

---

## Creating and Deleting

```bash
# create a workspace
fab mkdir MyWorkspace.Workspace

# create a workspace assigned to a capacity
fab mkdir MyWorkspace.Workspace -P capacityname=capac1

# delete an item (prompts for confirmation)
fab rm ws1.Workspace/nb1.Notebook

# force delete, no prompt
fab rm ws1.Workspace/nb1.Notebook -f
fab rm ws1.Workspace -f

# delete current directory context
fab rm .
```

---

## Navigation (interactive mode)

```bash
fab config set mode interactive   # enable interactive shell
fab auth login                    # authenticate

fab cd ws1.Workspace              # change into a workspace
fab cd "My workspace.Personal"    # workspace with spaces
fab cd ~                          # go to root
fab pwd                           # print current path
fab open ws1.Workspace            # open in browser
```

---

## Shortcuts (OneLake links)

```bash
# create a OneLake shortcut
fab ln ws1.Workspace/shortcut1 --type oneLake --target /ws2.Workspace/lh1.Lakehouse

# external shortcut types: adlsGen2, amazonS3, dataverse, googleCloudStorage, s3Compatible
```

---

## Common Flags Reference

| Flag | Meaning |
|------|---------|
| `-f` / `--force` | Skip confirmation prompts; overwrite existing |
| `-a` / `--all` | Include all items (used with `ls`, `export`) |
| `-l` / `--long` | Long/detailed listing |
| `-o` / `--output` | Output path (for `export`, `get`) |
| `-i` / `--input` | Input path or value (for `import`, `set`) |
| `-q` / `--query` | JMESPath expression to filter/target JSON fields |
| `-v` / `--verbose` | Full JSON output |
| `-P` / `--params` | `key=value` pairs, comma-separated (for `mkdir`) |
| `--format` | Input format for notebooks (`.ipynb` default, `.py` supported) |
| `--type` | Shortcut type (for `ln`) |
| `--target` | Shortcut target path (for `ln`) |

---

## Scripting Patterns

### Promote an item across workspaces via export/import

```bash
#!/usr/bin/env bash
set -euo pipefail

ITEM="rep1.Report"
SRC="ws_dev.Workspace"
DST="ws_prod.Workspace"
TMPDIR=$(mktemp -d)

fab export "$SRC/$ITEM" -o "$TMPDIR" -f
fab import "$DST/$ITEM" -i "$TMPDIR/$ITEM" -f

rm -rf "$TMPDIR"
```

### Check existence before acting

```bash
if fab exists ws1.Workspace/nb1.Notebook; then
  echo "Item exists, exporting..."
  fab export ws1.Workspace/nb1.Notebook -o /tmp/out -f
else
  echo "Item not found"
  exit 1
fi
```

### List all Report items in a workspace

```bash
fab ls ws1.Workspace -l | grep "\.Report"
# or with JMESPath:
fab ls ws1.Workspace -q "[?contains(name, 'Report')].name"
```

---

## Further Reference

- Official docs: https://microsoft.github.io/fabric-cli/
- Auth examples: https://microsoft.github.io/fabric-cli/examples/auth_examples
- Workspace examples: https://microsoft.github.io/fabric-cli/examples/workspace_examples
- Item examples: https://microsoft.github.io/fabric-cli/examples/item_examples
