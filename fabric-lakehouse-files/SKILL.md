---
name: fabric-lakehouse-files
description: >
  Use this skill when working with files and tables inside a Microsoft Fabric lakehouse:
  listing, downloading, uploading, reading Delta tables, or investigating files in the
  Files/ or Tables/ areas via OneLake.
  Also use when a file path behaves unexpectedly, shows stale data, or you need to know whether
  a directory is a shortcut and where it points.
  Trigger when users mention: lakehouse files, lakehouse tables, read lakehouse data,
  query lakehouse, OneLake, Delta table, upload to lakehouse, download from lakehouse,
  Fabric file operations, lakehouse shortcut, `fab cp`, Azure DataLake,
  `azure-storage-file-datalake`, polars, duckdb.
  Covers: `fab` CLI, Python SDK (Azure DataLake), shortcut detection via `fab ls`,
  local Delta table reads via DuckDB/polars, and shortcut target resolution.
---

# Microsoft Fabric Lakehouse File & Table Operations Skill

Fabric lakehouses expose their `Files/` and `Tables/` areas via OneLake (ADLS Gen2-compatible).
This skill covers three interaction modes:

1. **`fab` CLI** — fastest for ad-hoc file ops (ls, cp, export, import)
2. **Python SDK** — best for programmatic pipelines, bulk uploads, and reading Delta tables locally
3. **DuckDB / polars** — best for querying lakehouse table data on your local machine

## Path Convention

```
/<workspace>.Workspace/<lakehouse>.Lakehouse/Files/...
/<workspace>.Workspace/<lakehouse>.Lakehouse/Tables/<table_name>
```

**Example:**
```
/Facilities - Staging Refactor.Workspace/Facilities_Landing_Lakehouse.Lakehouse/Files/NDF
/Facilities - Staging Refactor.Workspace/Facilities_Landing_Lakehouse.Lakehouse/Tables/bronze_customers
```

> **Table paths are Delta Lake.** Each table is a directory containing `_delta_log/` and parquet files.

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

# List tables (Delta directories)
fab ls "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Tables" -la
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

# Upload a Python wheel (common pattern for shared libraries)
fab cp /tmp/dist/my_package-1.0.0-py3-none-any.whl \
       "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files/libs/my_package.whl" -f
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

# List Delta tables
for item in file_system.get_paths(path=f"{LAKEHOUSE}.Lakehouse/Tables", recursive=False):
    print(item.name, "(directory)" if item.is_directory else "(file)")
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

### Bulk / Chunked Upload (Large Files)

```python
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeFileClient

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Shared_Lakehouse"
REMOTE_PATH = f"{LAKEHOUSE}.Lakehouse/Files/large_dataset.parquet"
LOCAL_PATH = Path("/tmp/large_dataset.parquet")

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB chunks

credential = DefaultAzureCredential()
file_client = DataLakeFileClient(
    account_url=ACCOUNT_URL,
    file_system_name=WORKSPACE,
    file_path=REMOTE_PATH,
    credential=credential,
)

file_client.create_file()

offset = 0
with open(LOCAL_PATH, "rb") as f:
    while chunk := f.read(CHUNK_SIZE):
        file_client.append_data(data=chunk, offset=offset, length=len(chunk))
        offset += len(chunk)

file_client.flush_data(offset)
print(f"Uploaded {LOCAL_PATH} ({offset} bytes) in {offset // CHUNK_SIZE + 1} chunks")
```

---

## Option C: Reading Lakehouse Tables Locally (Delta Lake)

Lakehouse tables are **Delta Lake** directories. You can read them locally using DuckDB or polars + deltalake.

### Prerequisites

```bash
# For DuckDB approach
pip install duckdb polars azure-identity

# For polars + deltalake approach
pip install polars deltalake azure-identity
```

### Method 1: DuckDB with Azure Extension (Recommended)

DuckDB handles Azure auth and Delta format in one query. Best for exploration and analytics.

```python
import duckdb

con = duckdb.connect()
con.install_extension("azure")
con.load_extension("azure")

# Use Azure CLI login chain (requires `az login`)
con.sql("""
    CREATE SECRET azure_secret (
        TYPE AZURE,
        PROVIDER CREDENTIAL_CHAIN,
        CHAIN 'cli'
    );
""")

WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Bronze_Lakehouse"
TABLE = "bronze_customers"

# Read Delta table from OneLake into a polars DataFrame
# Note: use the DFS endpoint path
query = f"""
    SELECT *
    FROM delta_scan('abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}.Lakehouse/Tables/{TABLE}')
    LIMIT 100
"""

df = con.sql(query).pl()
print(df)
```

**DuckDB + Azure auth variants:**

```python
# If Azure CLI isn't working, use a bearer token directly
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://storage.azure.com/.default").token

con.sql(f"""
    CREATE SECRET azure_token (
        TYPE AZURE,
        PROVIDER CONFIG,
        ACCOUNT_NAME 'onelake',
        BEARER_TOKEN '{token}'
    );
""")
```

**Advanced DuckDB patterns:**

```python
# Filter pushdown — DuckDB reads only matching parquet files
con.sql(f"""
    SELECT customer_id, name, updated_at
    FROM delta_scan('abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}.Lakehouse/Tables/{TABLE}')
    WHERE updated_at > '2026-01-01'
""").pl()

# Aggregate directly in DuckDB before pulling to Python
summary = con.sql(f"""
    SELECT
        DATE_TRUNC('month', updated_at) as month,
        COUNT(*) as row_count
    FROM delta_scan('abfss://.../Tables/{TABLE}')
    GROUP BY 1
    ORDER BY 1
""").pl()
```

### Method 2: Polars + deltalake

Best when you need the result as a polars DataFrame and want explicit control over storage options.

```python
from azure.identity import DefaultAzureCredential
from deltalake import DeltaTable
import polars as pl

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Bronze_Lakehouse"
TABLE = "bronze_customers"

credential = DefaultAzureCredential()
token = credential.get_token("https://storage.azure.com/.default").token

storage_options = {
    "bearer_token": token,
}

table_path = f"{ACCOUNT_URL}/{WORKSPACE}/{LAKEHOUSE}.Lakehouse/Tables/{TABLE}"

# Load Delta table metadata
dt = DeltaTable(table_path, storage_options=storage_options)

# Read full table into polars
pa_table = dt.to_pyarrow_table()
df = pl.from_arrow(pa_table)

# Or read with predicate pushdown
pa_table = dt.to_pyarrow_table(partitions=[("year", "=", "2026")])
df = pl.from_arrow(pa_table)
```

**DeltaTable inspection:**

```python
# See schema
print(dt.schema())

# See version history
print(dt.history())

# See files that make up the table
print(dt.files())

# Optimize (if you have write permissions)
dt.optimize.compact()
dt.vacuum()
```

### Method 3: Direct Parquet Read (Simple Tables, No Delta Features)

If you only need the latest snapshot and the table is simple (no time travel, no deletes):

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
import polars as pl
from io import BytesIO

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Bronze_Lakehouse"
TABLE = "bronze_customers"

credential = DefaultAzureCredential()
service_client = DataLakeServiceClient(account_url=ACCOUNT_URL, credential=credential)
file_system = service_client.get_file_system_client(WORKSPACE)

# Read the latest parquet file(s) — simplest but misses Delta transactions
table_path = f"{LAKEHOUSE}.Lakehouse/Tables/{TABLE}"
paths = list(file_system.get_paths(path=table_path, recursive=True))
parquet_files = [p.name for p in paths if p.name.endswith(".parquet")]

# Download and concat
dfs = []
for pf in parquet_files[:5]:  # limit for safety
    file_client = file_system.get_file_client(pf)
    stream = file_client.download_file()
    data = stream.readall()
    dfs.append(pl.read_parquet(BytesIO(data)))

df = pl.concat(dfs)
```

> **Warning:** This bypasses Delta transaction logs. Use only for quick checks on append-only tables.

---

## Shortcut Detection and Resolution

`fab ls` reports a `Shortcut` type instead of `Directory` for shortcut entries:

```bash
fab ls "MyWorkspace.Workspace/MyLakehouse.Lakehouse/Files" -la
# Example output:
# rw-r-----   ...   FAC-Facilities.Shortcut   Shortcut
```

The OneLake DFS HEAD response also sets `x-ms-onelake-shortcut-path: true` on shortcut paths:

```bash
az rest --method HEAD \
  --url "https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{lakehouseId}/Files/{path}" \
  --resource "https://storage.azure.com" \
  --verbose 2>&1 | grep "x-ms-onelake-shortcut"
```

### Resolve shortcut target (Fabric REST API)

Step 1 — get the workspace ID:
```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[?displayName=='My Workspace'].id" -o tsv
```

Step 2 — get the lakehouse item ID:
```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/lakehouses" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[?displayName=='MyLakehouse'].id" -o tsv
```

Step 3 — resolve the shortcut (URL-encode `/` as `%2F` in the path):
```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{lakehouseId}/shortcuts/Files%2F{shortcutName}" \
  --resource "https://api.fabric.microsoft.com" \
  -o json
# Returns: { "name", "path", "target": { "oneLake": { "workspaceId", "itemId", "path" }, "type" } }
```

Step 4 — resolve target workspace and item names from the IDs in the response:
```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{targetWorkspaceId}" \
  --resource "https://api.fabric.microsoft.com" \
  --query "{id:id,name:displayName}" -o tsv

az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{targetWorkspaceId}/items/{targetItemId}" \
  --resource "https://api.fabric.microsoft.com" \
  --query "{id:id,name:displayName,type:type}" -o tsv
```

> **Note:** The shortcut name in the API call is without the `.Shortcut` suffix that `fab ls` appends.

---

## Metadata & Introspection

### Check if a File Exists

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeFileClient
from azure.core.exceptions import ResourceNotFoundError

ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
WORKSPACE = "Facilities - Staging Refactor"
LAKEHOUSE = "Facilities_Landing_Lakehouse"
REMOTE_PATH = f"{LAKEHOUSE}.Lakehouse/Files/NDF/report.xlsx"

credential = DefaultAzureCredential()
file_client = DataLakeFileClient(
    account_url=ACCOUNT_URL,
    file_system_name=WORKSPACE,
    file_path=REMOTE_PATH,
    credential=credential,
)

try:
    props = file_client.get_file_properties()
    print(f"Exists: {props.size} bytes, last modified {props.last_modified}")
except ResourceNotFoundError:
    print("File does not exist")
```

### Read a Small File as Text

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeFileClient

file_client = DataLakeFileClient(...)
download = file_client.download_file()
text = download.readall().decode("utf-8")
print(text[:500])
```

### Get Table Schema (via DeltaTable)

```python
from azure.identity import DefaultAzureCredential
from deltalake import DeltaTable

credential = DefaultAzureCredential()
token = credential.get_token("https://storage.azure.com/.default").token

dt = DeltaTable(
    "https://onelake.dfs.fabric.microsoft.com/Workspace/Lakehouse.Lakehouse/Tables/my_table",
    storage_options={"bearer_token": token},
)

print(dt.schema().json())
print(f"Version: {dt.version()}")
print(f"Files: {len(dt.files())}")
```

---

## Quick Reference: Which Tool to Use

| Task | Recommended Tool |
|------|----------------|
| Ad-hoc listing / one-off download | `fab ls` / `fab cp` |
| Scripting / CI pipeline | Python SDK |
| Bulk upload of `.whl` or dataset | Python SDK |
| Interactive exploration | `fab` |
| Detect if a path is a shortcut | `fab ls -la` (look for `Shortcut` type) |
| Resolve where a shortcut points | Fabric REST API (`az rest`) — see above |
| Read lakehouse table locally (analytics) | DuckDB + azure extension |
| Read lakehouse table locally (data engineering) | polars + deltalake |
| Check table schema / Delta metadata | `deltalake.DeltaTable` |
| Stream large files | Python SDK chunked upload |

---

## Tips

- **Spaces in names:** Quote workspace/lakehouse names that contain spaces.
- **Authentication:** Both `fab auth login` and `DefaultAzureCredential()` use the same Azure CLI login session. If one works, the other usually does too.
- **Read-only operations:** `fab ls`, `fab cp <lakehouse> <local>`, and DuckDB `SELECT` queries are safe read-only operations.
- **Finding workspace names:** Run `fab ls` at the root to see all workspaces, then copy the exact name.
- **Large files:** Both approaches work well for files up to several hundred MB. For GB-scale files, use chunked upload or OneLake DFS REST API.
- **Table names:** In `fab ls`, tables appear as directories under `Tables/`. The actual table name is the directory name without any suffix.
- **DuckDB secrets:** Create the Azure secret once per connection. It persists for the lifetime of the DuckDB connection.
- **Token expiry:** `DefaultAzureCredential` tokens expire. For long-running scripts, refresh the token before large operations or use `AzureCliCredential` which auto-refreshes on request.
- **Deterministic mount paths in notebooks:** When working inside Fabric notebooks, mount paths are `/mnt/<lakehouse_name_lowercased>`. This skill focuses on **local** access to the same data via OneLake.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `not found in Fabric` (fab) | Verify the exact workspace/lakehouse name with `fab ls` |
| `AccountIsDisabled` (az storage) | OneLake is not a standard storage account — use `fab` or the Python SDK instead |
| `Issuer validation failed` (REST API) | Token audience mismatch — use the Python SDK which handles token exchange correctly |
| Auth errors | Run `fab auth login` or ensure `az account show` returns an active subscription |
| `bool is used as a file descriptor` warning | Harmless RuntimeWarning from `fab cp`, the copy still succeeds |
| DuckDB "No valid Azure credentials found" | Ensure `az login` is active, or pass bearer token explicitly |
| `deltalake` "Failed to read delta log" | Check bearer token is valid and table path points to a Delta directory (not a file) |
| Slow table reads | Use DuckDB predicate pushdown or polars `scan_delta` instead of reading all files |
| `AzureCliCredential` timeout | Run `az account get-access-token` to refresh the CLI session |

