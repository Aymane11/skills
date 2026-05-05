# fabric-cli-core

Core skill for Microsoft Fabric CLI operations. **Load this skill first** for any Fabric CLI task.

## What This Skill Provides

- Fabric hierarchy mental model (Tenant → Workspace → Folder → Item → OneLakeItem)
- Path conventions with dot entity suffixes (e.g., `.Workspace`, `.Notebook`)
- Authentication patterns (interactive, SPN, managed identity)
- Hidden entity discovery (`ls -a`)
- Security and sensitive data handling rules
- Critical operational rules
- Common item types reference

## Entry Point

Load [`SKILL.md`](./SKILL.md) to activate this skill.

## References

Detailed documentation in the `references/` folder:

| Reference | Description |
|-----------|-------------|
| [quickstart.md](./references/quickstart.md) | Copy-paste examples for common tasks |
| [reference.md](./references/reference.md) | All commands with flags and patterns |
| [semantic-models.md](./references/semantic-models.md) | TMDL, DAX queries, refresh, storage modes |
| [notebooks.md](./references/notebooks.md) | Job execution, parameters, scheduling |
| [reports.md](./references/reports.md) | Export, import, rebind to models |
| [workspaces.md](./references/workspaces.md) | Create, manage, permissions |
| [querying-data.md](./references/querying-data.md) | DAX and lakehouse table queries |
| [fab-api.md](./references/fab-api.md) | Direct REST API access patterns |
| [create-workspaces.md](./references/create-workspaces.md) | Workspace creation workflows |

---

## Workspace Export

### Setup (Avoid Interactive Prompts)

Before exporting, set Fabric CLI to command-line mode to avoid interactive prompts:

```bash
fab config set mode command_line
```

### Export Entire Workspace

To export all items from a workspace (notebooks, pipelines, lakehouses, etc.):

```bash
# Export all items with force flag (skip sensitivity label warnings)
fab export "WorkspaceName.Workspace" -o "/path/to/output" -a -f
```

Flags:
- `-a, --all` - Export all items in the workspace
- `-f, --force` - Force export without confirmation prompts

Example:
```bash
fab export "Facilities - Production.Workspace" -o "./export/Facilities_Production" -a -f
```

### Export Single Item

```bash
fab export "WorkspaceName.Workspace/NotebookName.Notebook" -o "/path/to/output" -f
```

### Export to Lakehouse

```bash
fab export "ws1.Workspace/lh1.Lakehouse/Files/export" -f -o "ws1.Workspace/lh1.Lakehouse"
```

### Notes
- Export creates a folder with item name (e.g., `notebook-name.Notebook/`)
- Each export includes `.platform` file and `notebook-content.ipynb` (for notebooks)
- For pipelines, exports as JSON definition
- Use parallel agents to export multiple workspaces simultaneously
