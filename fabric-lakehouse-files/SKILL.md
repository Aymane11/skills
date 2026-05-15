---
name: fabric-lakehouse-files
description: >
  Use this skill when you need to list, download, or upload files inside a Microsoft Fabric
  lakehouse (the Files/ or Tables/ areas). Covers both the `fab` CLI approach and the Python SDK
  approach (Azure DataLake SDK with DefaultAzureCredential). Does NOT cover reading file contents
  or downstream processing — only the lakehouse file operations themselves.
---

# Microsoft Fabric Lakehouse File Operations Skill

Fabric lakehouses expose their `Files/` and `Tables/` areas via OneLake (ADLS Gen2-compatible).
There are two ways to interact with files: the `fab` CLI (easiest for ad-hoc work) and the
Python SDK (best for programmatic pipelines).

## Path Convention

Lakehouse sub-paths follow this pattern:

```
/<workspace>.Workspace/<lakehouse>.Lakehouse/Files/...
/<workspace>.Workspace/<lakehouse>.Lakehouse/Tables/...
```

**Example:**
```
/Facilities - Staging Refactor.Workspace/Facilities_Landing_Lakehouse.Lakehouse/Files/NDF
```

---

## Option A: Fabric CLI (`fab`)

### Prerequisites

```bash
pip install ms-fabric-cli
fab --version
fab auth login          # interactive browser login (run once)
```

### Listing Files and Directories

```bash
# Top-level lakehouse contents (Files, Functions, TableMaintenance, Tables)
fab ls "MyWorkspace.Workspace/MyLakehouse.Lakehouse" -la

# List a sub-directory
fab ls "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files/NDF" -la

# Long listing with file sizes and dates
fab ls "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files" -l
```

### Downloading Files (Lakehouse → Local)

```bash
# Copy a single file from lakehouse to local disk
fab cp "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files/NDF/report.xlsx" /tmp/report.xlsx -f

# Copy from one lakehouse to another in the same workspace
fab cp "MyWorkspace.Workspace/Lakehouse1.Lakehouse/Files/data.csv" \
       "MyWorkspace.Workspace/Lakehouse2.Lakehouse/Files/data.csv" -f
```

> **Note:** The `-f` flag forces overwrite without prompting. Always use it in scripts.
> **Note:** Recursive directory copy (`fab cp <dir> <dir>`) is **not supported**.

### Uploading Files (Local → Lakehouse)

```bash
# Copy a local file into the lakehouse Files area
fab cp /tmp/local_report.xlsx "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files/report.xlsx" -f
```

---

## Option B: Python SDK (azure-storage-file-datalake)

Use this when `fab` is not available or when you need programmatic access in a Python script.

### Prerequisites

```bash
pip install azure-identity azure-storage-file-datalake
```

### Listing Files

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Landing_Lakehouse"

credential = DefaultAzureCredential()
service_client = DataLakeServiceClient(account_url=ACCOUNT_URL, credential=credential)
file_system = service_client.get_file_system_client(WORKSPACE)

# List files under a path
path = f"{LAKEHOUSE}.Lakehouse/Files/NDF"
for item in file_system.get_paths(path=path, recursive=False):
    print(item.name, item.content_length, item.is_directory)
```

### Downloading a File

```python
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeFileClient

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Landing_Lakehouse"
REMOTE_PATH = f"{LAKEHOUSE}.Lakehouse/Files/NDF/report.xlsx"
LOCAL_PATH = Path("/tmp/report.xlsx")

credential = DefaultAzureCredential()
file_client = DataLakeFileClient(
    account_url=ACCOUNT_URL,
    file_system_name=WORKSPACE,
    file_path=REMOTE_PATH,
    credential=credential,
)

download = file_client.download_file()
data = download.readall()

LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(LOCAL_PATH, "wb") as f:
    f.write(data)

print(f"Downloaded {len(data)} bytes to {LOCAL_PATH}")
```

### Uploading a File

```python
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeFileClient

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Shared_Lakehouse"
REMOTE_PATH = f"{LAKEHOUSE}.Lakehouse/Files/report.xlsx"
LOCAL_PATH = Path("/tmp/report.xlsx")

credential = DefaultAzureCredential()
file_client = DataLakeFileClient(
    account_url=ACCOUNT_URL,
    file_system_name=WORKSPACE,
    file_path=REMOTE_PATH,
    credential=credential,
)

with open(LOCAL_PATH, "rb") as f:
    data = f.read()

file_client.create_file()
file_client.append_data(data=data, offset=0, length=len(data))
file_client.flush_data(len(data))

print(f"Uploaded {len(data)} bytes to {REMOTE_PATH}")
```

---

## Quick Reference: Which Tool to Use

| Task | Recommended Tool |
|------|----------------|
| Ad-hoc listing / one-off download | `fab ls` / `fab cp` |
| Scripting / CI pipeline | Python SDK |
| Bulk upload of `.whl` or dataset | Python SDK |
| Interactive exploration | `fab` |

---

## Tips

- **Spaces in names:** Quote workspace/lakehouse names that contain spaces.
- **Authentication:** Both `fab auth login` and `DefaultAzureCredential()` use the same Azure CLI login session. If one works, the other usually does too.
- **Read-only operations:** `fab ls` and `fab cp <lakehouse> <local>` are safe read-only operations.
- **Finding workspace names:** Run `fab ls` at the root to see all workspaces, then copy the exact name.
- **Large files:** Both approaches work well for files up to several hundred MB. For GB-scale files, consider OneLake DFS REST API with chunked reads.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `not found in Fabric` (fab) | Verify the exact workspace/lakehouse name with `fab ls` |
| `AccountIsDisabled` (az storage) | OneLake is not a standard storage account — use `fab` or the Python SDK instead |
| `Issuer validation failed` (REST API) | Token audience mismatch — use the Python SDK which handles token exchange correctly |
| Auth errors | Run `fab auth login` or ensure `az account show` returns an active subscription |
| `bool is used as a file descriptor` warning | Harmless RuntimeWarning from `fab cp`, the copy still succeeds |
