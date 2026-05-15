---
name: excel-data-quality-analyzer
description: >
  Analyze Excel and spreadsheet-like source files from local folders, lakehouses,
  SharePoint, cloud storage, repositories, or enterprise platforms to detect
  data quality anomalies and produce actionable, business-focused reports.
  Read-only. Use to diagnose header, formatting, mixed type, schema, formula,
  structural, or source-native data issues before downstream ingestion.
---

# Excel Data Quality Analyzer Skill

Analyze Excel and spreadsheet-based source files to detect data quality anomalies and produce actionable reports for business and engineering teams.

## When to Load This Skill

**Activate when** any of the following occur:
- User mentions Excel or spreadsheet files with data quality issues
- User asks to "check", "analyze", "validate", or "inspect" source files
- User mentions anomalies like `#VALUE!`, mixed types in columns, malformed dates, formatting inconsistencies, or broken formulas
- User is setting up a Bronze/Silver/Raw ingestion pipeline and needs to understand source structure
- User wants to create a `DATA_ISSUES.md` or similar report
- User says things like "these files have problems", "dates are malformed", "numbers stored as text"
- User needs source-system diagnostics before transformation logic is implemented

**Do not activate for:**
- Reading files that are already known to be clean
- Writing or modifying source files (this skill is read-only)
- Pure schema modeling or transformation design without source analysis

---

# Workflow

## 1. Gather Context Before Analysis

Before running any automated checks:

1. Try to understand:
   - The business purpose of the file
   - The meaning of each sheet/tab
   - The expected structure and semantics
   - Whether the file is manually maintained or system-generated
   - Whether formatting conventions are intentional

2. Inspect:
   - Sheet names
   - Header layouts
   - Sample rows
   - Cell formatting patterns
   - Formula usage
   - Hidden rows/columns if relevant
   - Metadata or instruction sheets

3. Avoid assuming:
   - First row is always the header
   - Mixed types are always errors
   - Blank rows are accidental
   - Formatting inconsistencies are invalid
   - Every workbook follows the same structure

**Important:** Every source file is different. Structural understanding must come before quality validation.

---

## 2. Download or Access Source Files

Use the appropriate platform skill or connector to retrieve files locally.

Possible sources include:
- Local directories
- SharePoint
- OneDrive
- Lakehouses
- Cloud object storage
- Git repositories
- Enterprise document systems

```python
from pathlib import Path

# Files should be saved locally before analysis
````

---

## 3. Detect Header Rows and Workbook Structure

Use `openpyxl` (not `calamine`/`fastexcel`) because it handles workbook structure and irregular headers correctly.

```python
from openpyxl import load_workbook

wb = load_workbook("file.xlsx", data_only=False)

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]

    # Inspect first rows manually
    for row_idx in range(1, 8):
        row_values = [cell.value for cell in ws[row_idx]]
        print(f"Row {row_idx}: {row_values}")
```

### Common patterns to detect

| Pattern                           | Meaning                                 |
| --------------------------------- | --------------------------------------- |
| Company/title rows before headers | Headers start lower                     |
| Multi-row headers                 | Requires flattening or merging          |
| Summary rows above data           | Skip before ingestion                   |
| Empty spacer rows                 | Visual formatting only                  |
| Hidden technical columns          | May contain keys or formulas            |
| Formula-driven sheets             | Output may differ from displayed values |

---

## 4. Per-Column and Structural Anomaly Detection

Load sheets with the detected structure:

```python
import polars as pl

df = pl.read_excel(
    "file.xlsx",
    sheet_name=sheet_name,
    engine="openpyxl"
)
```

## Check each column for

| Anomaly                       | Detection Method                  | Example                        |
| ----------------------------- | --------------------------------- | ------------------------------ |
| Mixed types                   | `pl.Object`, inconsistent parsing | Dates mixed with status labels |
| `#VALUE!` / Excel errors      | String matching                   | Broken formulas                |
| European number formats       | Regex validation                  | `"1.200,00"`                   |
| Typo dates                    | Regex / parsing validation        | `"30/03/20226"`                |
| Non-breaking spaces           | Unicode inspection                | `"\xa0"`                       |
| Empty columns                 | Null count checks                 | Entirely blank column          |
| Formula inconsistencies       | Compare formulas across rows      | Broken copied formulas         |
| Duplicate headers             | Header uniqueness checks          | Two `"Amount"` columns         |
| Shifted rows                  | Unexpected null distributions     | Misaligned imports             |
| Merged-cell artifacts         | Header/content gaps               | Reporting templates            |
| Unexpected categorical values | Value profiling                   | `"annule"` in date column      |

---

## 5. Cross-Check Existing Tracking and Documentation

Do not rely only on `DATA_ISSUES.md`.

Before documenting findings, inspect any existing tracking or operational artifacts such as:

* `TODO.md`
* `BACKLOG.md`
* `KNOWN_ISSUES.md`
* `QUALITY_NOTES.md`
* Jira exports
* Dev notes
* Markdown documentation
* Project management files
* Notebook comments
* Existing validation scripts

Cross-reference:

* Already-known issues
* Previously accepted anomalies
* Temporary workarounds
* Open remediation tasks
* Historical context

Avoid duplicating already-tracked findings unless:

* Severity increased
* Scope expanded
* Existing documentation is incomplete
* Root cause differs from current assumptions

---

## 6. Business Report Generation

Create `DATA_ISSUES.md` with this structure:

```markdown
# Data Issues — <Source Name>

## File: <filename>

### Purpose
<What the file appears to represent>

### Structural Notes
<Header patterns, workbook structure, important assumptions>

### Sheet: <sheet_name>

#### Column: <column_name>

- **Issue**: <description>
- **Affected rows**: <count or examples>
- **Business impact**: <why this matters>
- **Recommended fix**: <specific action>
- **Can be enforced at source?**: Yes/No
- **If yes**: <specific steps>
- **If no**: <recommended downstream workaround>
```

### Prioritization Rules

1. If issue can be fixed at source:

   * Prefer source correction first
   * Avoid unnecessary cleaning code

2. Only suggest code fixes when:

   * Source fix is impractical
   * Data is externally controlled
   * Business team cannot remediate quickly
   * Pipeline stability requires immediate handling

---

## 7. Developer Backlog Integration

For issues requiring engineering work:

* Add remediation items to backlog/tracking systems
* Include:

  * File and sheet names
  * Affected columns
  * Sample problematic values
  * Estimated impact
  * Suggested validation rules

### Suggested Priorities

| Priority | Description                                  |
| -------- | -------------------------------------------- |
| High     | Blocks ingestion or causes incorrect metrics |
| Medium   | Quality degradation but pipeline survives    |
| Low      | Cosmetic or low-frequency anomalies          |

---

# Key Principles

* **Understand before validating**
* **Every source file is unique**
* **Source-first remediation**
* **Read-only analysis**
* **Document exact evidence**
* **Cross-check existing tracking before raising new issues**
* **Avoid assumptions based on previous files**
* **Distinguish intentional structure from true anomalies**

---

# Dependencies

* `openpyxl` — workbook structure and Excel-native inspection
* `polars` — dataframe analysis
* `pandas` — optional profiling
* `requests` — remote downloads if needed
* Platform-specific retrieval skills/connectors as appropriate
