#!/usr/bin/env python3
"""
track_pipeline.py — Monitor a Fabric pipeline run from the CLI.

Usage:
  python3 track_pipeline.py <workspace> <pipeline> [--run <N|UUID>]
  watch -n 30 python3 track_pipeline.py "Facilities-Lakehouse-Dev" PL_Master_Full_Refresh
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

FABRIC_API = "https://api.fabric.microsoft.com"

STATUS_STYLE: Dict[str, Tuple[str, str]] = {
    "Succeeded":  ("✅", "bold green"),
    "Completed":  ("✅", "bold green"),
    "Failed":     ("❌", "bold red"),
    "InProgress": ("▶ ", "bold bright_yellow"),
    "Cancelled":  ("🚫", "bold orange3"),
    "Skipped":    ("⏭️ ", "dim"),
}

ACTIVITY_ICON: Dict[str, str] = {
    "TridentNotebook": "📓",
    "InvokePipeline":  "🔗",
    "ForEach":         "🔁",
    "Lookup":          "🔍",
    "SetVariable":     "📝",
    "Wait":            "⏸ ",
    "Copy":            "📋",
    "If":              "❓",
    "Until":           "🔄",
}


# ──────────────────────────────────────────────────────────────────────────────
# Disk cache  (1-hour TTL — workspace & item metadata rarely changes)
# ──────────────────────────────────────────────────────────────────────────────

_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "track_pipeline"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_TTL = 3600


def _cache_path(key: str) -> Path:
    return _CACHE_DIR / f"{key.replace('/', '_').replace(' ', '_')}.json"


def cache_get(key: str):
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        envelope = json.loads(p.read_text())
        if time.time() - envelope["created_at"] > _CACHE_TTL:
            return None
        return envelope["value"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def cache_set(key: str, value) -> None:
    try:
        _cache_path(key).write_text(json.dumps({"created_at": time.time(), "value": value}))
    except OSError:
        pass


def cache_clear() -> None:
    shutil.rmtree(_CACHE_DIR, ignore_errors=True)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓ Cache cleared:[/green] {_CACHE_DIR}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI wrappers  (fab + az rest)
# ──────────────────────────────────────────────────────────────────────────────

def fab(*args) -> dict:
    """Run a `fab` command and return parsed JSON."""
    result = subprocess.run(["fab", *args], capture_output=True, text=True)
    return json.loads(result.stdout.strip())


def az_rest_post(url: str, body: dict) -> dict:
    """POST to a Fabric REST endpoint using `az rest` for auth."""
    result = subprocess.run(
        ["az", "rest", "--method", "post", "--url", url,
         "--resource", FABRIC_API, "--body", json.dumps(body)],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout.strip())


# ──────────────────────────────────────────────────────────────────────────────
# Fabric data access
# ──────────────────────────────────────────────────────────────────────────────

def get_workspaces() -> Dict[str, str]:
    """Return {displayName: id} for all workspaces (cached)."""
    cached = cache_get("all_workspaces")
    if cached is not None:
        return cached
    data = fab("api", "workspaces", "-X", "get", "--output_format", "json")
    ws_map = {ws["displayName"]: ws["id"] for ws in data["result"]["data"][0]["text"]["value"]}
    cache_set("all_workspaces", ws_map)
    return ws_map


def get_workspace_id(name: str) -> Optional[str]:
    return get_workspaces().get(name)


_items_cache: Dict[str, dict] = {}


def get_items(ws_id: str) -> Dict[str, dict]:
    """Return {item_id: {name, type}} for all items in a workspace (cached)."""
    if ws_id in _items_cache:
        return _items_cache[ws_id]
    cached = cache_get(f"items_{ws_id}")
    if cached is not None:
        _items_cache[ws_id] = cached
        return cached
    data = fab("api", f"workspaces/{ws_id}/items", "-X", "get", "--output_format", "json")
    item_map = {
        item["id"]: {"name": item["displayName"], "type": item["type"]}
        for item in data["result"]["data"][0]["text"]["value"]
    }
    cache_set(f"items_{ws_id}", item_map)
    _items_cache[ws_id] = item_map
    return item_map


def get_notebooks(ws_id: str) -> Dict[str, str]:
    """Return {notebook_id: displayName} for a workspace."""
    return {
        item_id: meta["name"]
        for item_id, meta in get_items(ws_id).items()
        if meta["type"] == "Notebook"
    }


def get_run_id(workspace: str, pipeline: str, run_arg: Optional[str]) -> str:
    """
    Resolve a run ID from --run argument:
      None / "1"  → latest run
      "2", "3", … → Nth most-recent (1-based)
      UUID string → use directly
    """
    if run_arg is not None and not run_arg.isdigit():
        return run_arg  # already a UUID

    idx = (int(run_arg) - 1) if run_arg and run_arg.isdigit() else 0
    data = fab("job", "run-list", f"{workspace}.Workspace/{pipeline}.DataPipeline", "--output_format", "json")
    runs = data["result"]["data"]
    if idx >= len(runs):
        console.print(f"[red]❌ Only {len(runs)} run(s) available (requested #{idx + 1}).[/red]")
        sys.exit(1)
    return runs[idx]["id"]


def get_run_status(workspace: str, pipeline: str, run_id: str) -> dict:
    """Fetch master run metadata."""
    data = fab(
        "job", "run-status",
        f"{workspace}.Workspace/{pipeline}.DataPipeline",
        "--id", run_id, "--output_format", "json",
    )
    return data["result"]["data"][0]


def get_child_run_id(child_ws_id: str, child_pipeline_id: str, after: str) -> Optional[str]:
    """
    For a still-running InvokePipeline (output is empty), find the child run ID
    by listing recent runs of the child pipeline and picking the one that started
    after `after`.
    """
    try:
        # Find the pipeline name from its ID
        items = get_items(child_ws_id)
        meta = items.get(child_pipeline_id)
        if not meta:
            return None
        pipeline_name = meta["name"]

        # Find the workspace name
        ws_name_by_id = {v: k for k, v in get_workspaces().items()}
        ws_name = ws_name_by_id.get(child_ws_id)
        if not ws_name:
            return None

        data = fab("job", "run-list", f"{ws_name}.Workspace/{pipeline_name}.DataPipeline", "--output_format", "json")
        runs = data["result"]["data"]
        # Pick the most recent run that started on or after `after`
        for run in runs:
            run_start = run.get("startTimeUtc") or run.get("startTime") or ""
            if run_start >= after[:19]:
                return run["id"]
    except Exception:
        pass
    return None


def get_activity_runs(ws_id: str, run_id: str, after: str, before: str) -> List[dict]:
    """Query all activity runs for a pipeline run via Fabric REST API."""
    return az_rest_post(
        f"{FABRIC_API}/v1/workspaces/{ws_id}/datapipelines/pipelineruns/{run_id}/queryactivityruns",
        {
            "filters": [],
            "orderBy": [{"orderBy": "ActivityRunStart", "order": "ASC"}],
            "lastUpdatedAfter": after,
            "lastUpdatedBefore": before,
        },
    ).get("value", [])


# ──────────────────────────────────────────────────────────────────────────────
# Activity processing helpers
# ──────────────────────────────────────────────────────────────────────────────

def tag_foreach_children(activities: List[dict]) -> List[dict]:
    """
    Tag each activity with its ForEach parent name (or None).
    Fabric doesn't populate iterationHash, so we use temporal overlap instead.
    """
    containers = [
        {
            "name": a["activityName"],
            "start": a["activityRunStart"],
            "end": a.get("activityRunEnd") or "2099-01-01T00:00:00Z",
        }
        for a in activities if a["activityType"] == "ForEach"
    ]
    result = []
    for act in activities:
        parent = None
        if act["activityType"] != "ForEach":
            start = act.get("activityRunStart", "")
            for c in containers:
                if c["start"] <= start <= c["end"]:
                    parent = c["name"]
                    break
        result.append({**act, "_parent": parent})
    return result


def extract_params(input_dict: Optional[dict]) -> Dict[str, str]:
    """
    Normalise both param formats into {key: "value (type)"}.
      - Notebook:  {k: {type, value}}
      - Pipeline:  {k: value}
    """
    raw = (input_dict or {}).get("parameters") or {}
    out = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "value" in v:
            typ = v.get("type") or type(v["value"]).__name__
            out[k] = f"{v['value']} ({typ})"
        else:
            out[k] = f"{v} ({type(v).__name__})"
    return out


def fetch_child_run(child_ws: str, child_run: str, after: str, before: str) -> Tuple[dict, list]:
    """Fetch notebooks map + tagged activities for one child pipeline run."""
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_nb   = ex.submit(get_notebooks, child_ws)
            fut_acts = ex.submit(get_activity_runs, child_ws, child_run, after, before)
            nb_map   = fut_nb.result()
            acts     = fut_acts.result()
        if acts:
            return nb_map, tag_foreach_children(acts)
    except Exception:
        pass
    return {}, []


def _resolve_child_run_id(act: dict, after: str) -> Optional[str]:
    """Resolve child run ID from output (completed) or by querying run-list (in-progress)."""
    run_id = (act.get("output") or {}).get("pipelineRunId")
    if run_id:
        return run_id
    if act.get("status") == "InProgress":
        inp = act.get("input") or {}
        child_ws = inp.get("workspaceId")
        child_pl = inp.get("pipelineId")
        act_start = act.get("activityRunStart", after)
        if child_ws and child_pl:
            return get_child_run_id(child_ws, child_pl, act_start)
    return None


def prefetch_child_runs(tagged: List[dict], after: str, before: str) -> dict:
    """
    Fetch all InvokePipeline child run data in parallel.
    Returns {(child_ws_id, child_run_id): (nb_map, tagged_activities)}.
    """
    invocations = [
        a for a in tagged
        if a["activityType"] == "InvokePipeline"
        and (a.get("input") or {}).get("workspaceId")
    ]
    if not invocations:
        return {}

    # Resolve child run IDs first (may require API calls for in-progress)
    resolved = []
    for a in invocations:
        child_run_id = _resolve_child_run_id(a, after)
        if child_run_id:
            resolved.append((a["input"]["workspaceId"], child_run_id))
            a["_resolved_child_run_id"] = child_run_id  # stash for build_tree

    if not resolved:
        return {}

    results = {}
    with ThreadPoolExecutor(max_workers=len(resolved)) as ex:
        futures = {
            ex.submit(fetch_child_run, ws_id, run_id, after, before): (ws_id, run_id)
            for ws_id, run_id in resolved
        }
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Rich rendering helpers
# ──────────────────────────────────────────────────────────────────────────────

def fmt_duration(ms: Optional[int]) -> str:
    if not ms:
        return "—"
    s = ms // 1000
    if s < 60:    return f"{s}s"
    if s < 3600:  return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def fmt_datetime(value, fallback="—") -> str:
    """Full YYYY-MM-DD HH:MM:SS for headers."""
    if not value or value == "null":
        return fallback
    return str(value)[:19].replace("T", " ")


def fmt_time(value, fallback="—") -> str:
    """HH:MM:SS only — keeps activity label lines short."""
    if not value or value == "null":
        return fallback
    s = str(value)
    return s[11:19] if "T" in s else s[8:16]


def status_style(status: str) -> Tuple[str, str]:
    return STATUS_STYLE.get(status, ("❓", "dim"))


def make_params_table(params: dict) -> Table:
    t = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    t.add_column(style="dim cyan", no_wrap=True, min_width=24)
    t.add_column(style="white")
    for k, v in params.items():
        t.add_row(k, str(v))
    return t


def make_activity_label(act: dict, ws_name: str, nb_map: dict, items: dict) -> Text:
    """Build the single-line rich Text label for an activity node."""
    atype  = act["activityType"]
    status = act["status"]
    sym, style = status_style(status)
    icon   = ACTIVITY_ICON.get(atype, "▸")
    is_running = status == "InProgress"

    # For running activities, compute elapsed time instead of duration
    if is_running and act.get("activityRunStart"):
        try:
            start_dt = datetime.strptime(act["activityRunStart"][:19], "%Y-%m-%dT%H:%M:%S")
            elapsed_ms = int((datetime.utcnow() - start_dt).total_seconds() * 1000)
            dur = fmt_duration(elapsed_ms) + " elapsed"
        except ValueError:
            dur = fmt_duration(act.get("durationInMs") or 0)
    else:
        dur = fmt_duration(act.get("durationInMs") or 0)

    label = Text()
    if is_running:
        label.append(" RUNNING ", style="bold black on bright_yellow")
        label.append("  ", style="")
    label.append(f"{sym}  ", style=style)
    label.append(f"{icon} {act['activityName']}", style=f"bold {style}")
    label.append(f"  ⏱ {dur}  ", style="cyan")
    label.append(
        f"{fmt_time(act.get('activityRunStart'), '—')}  →  {fmt_time(act.get('activityRunEnd'), 'running…')}",
        style="dim" if not is_running else "yellow",
    )

    inp = act.get("input") or {}

    if atype == "TridentNotebook":
        nb_id = inp.get("notebookId", "")
        if nb_id:
            label.append(f"  📓 {nb_map.get(nb_id, 'unknown')}", style="blue")
            label.append(f" ({nb_id})", style="dim")

    elif atype == "InvokePipeline":
        pl_id = inp.get("pipelineId", "")
        if pl_id:
            pl_name = (items.get(pl_id) or {}).get("name", "")
            if pl_name:
                label.append(f"  🔗 {pl_name}", style="blue")
                label.append(f" ({pl_id})", style="dim")

    label.append(f"  🏢 {ws_name}", style="magenta")
    return label


def attach_activity_details(node, act: dict, nb_map: dict, compact: bool = False) -> None:
    """Attach type-specific detail sub-nodes (error, params, lookup results, etc.).

    In compact mode, only show errors; hide params, lookups, and SetVariable details.
    """
    atype = act["activityType"]
    inp   = act.get("input") or {}
    outp  = act.get("output") or {}
    err   = (act.get("error") or {}).get("message") or ""

    # Always show errors, even in compact mode
    if err and err not in ("", "null"):
        node.add(Text(f"⚠  {err}", style="red"))

    if compact:
        return  # skip all details in compact mode

    params = extract_params(inp)
    if params:
        node.add(Text("⚙  params", style="bold dim")).add(make_params_table(params))

    if atype == "Lookup":
        _attach_lookup_details(node, inp, outp)

    elif atype == "SetVariable":
        var_name = inp.get("variableName", "")
        var_val  = inp.get("value", "")
        if var_name:
            node.add(Text(f"📝  {var_name}  =  {var_val}", style="dim"))


def _attach_lookup_details(node, inp: dict, outp: dict) -> None:
    db    = ((inp.get("datasetSettings") or {}).get("typeProperties") or {}).get("database", "")
    sql   = ((inp.get("source") or {}).get("sqlReaderQuery") or "").strip()
    count = outp.get("count")
    rows  = outp.get("value") or []

    if db:
        node.add(Text(f"🗄  {db}", style="dim"))
    if sql:
        node.add(Text("🔎 query", style="bold dim")).add(Text(sql, style="dim italic"))
    if count is not None:
        res_node = node.add(Text(f"📊 {count} row(s)", style="bold dim"))
        if rows:
            tbl = Table(box=None, show_header=True, padding=(0, 1, 0, 0), header_style="bold dim cyan")
            for col in rows[0].keys():
                tbl.add_column(col, style="dim", no_wrap=True)
            for row in rows:
                tbl.add_row(*[str(v) for v in row.values()])
            res_node.add(tbl)


# ──────────────────────────────────────────────────────────────────────────────
# Tree builder  (recursive)
# ──────────────────────────────────────────────────────────────────────────────

def build_tree(
    parent_node,
    tagged: List[dict],
    nb_map: dict,
    ws_id: str,
    after: str,
    before: str,
    child_data: Optional[dict] = None,
    compact: bool = False,
) -> None:
    """Recursively attach activity nodes to parent_node."""
    if child_data is None:
        child_data = prefetch_child_runs(tagged, after, before)

    ws_name_by_id = {v: k for k, v in get_workspaces().items()}
    current_ws_name = ws_name_by_id.get(ws_id, ws_id)
    items = get_items(ws_id)

    top_level = [a for a in tagged if a["_parent"] is None]
    foreach_children: Dict[str, list] = {}
    for a in tagged:
        if a["_parent"]:
            foreach_children.setdefault(a["_parent"], []).append(a)

    for act in top_level:
        atype     = act["activityType"]
        child_run = (act.get("output") or {}).get("pipelineRunId")
        child_ws  = (act.get("input") or {}).get("workspaceId")

        act_ws_name = ws_name_by_id.get(child_ws, child_ws) if (atype == "InvokePipeline" and child_ws) else current_ws_name
        child_items = get_items(child_ws) if (atype == "InvokePipeline" and child_ws) else items

        label = make_activity_label(act, act_ws_name, nb_map, child_items)
        node  = parent_node.add(label)

        attach_activity_details(node, act, nb_map, compact=compact)

        if atype == "ForEach":
            _build_foreach_children(node, foreach_children.get(act["activityName"], []), nb_map, current_ws_name, items, compact=compact)

        elif atype == "InvokePipeline" and child_ws:
            child_run = child_run or act.get("_resolved_child_run_id")
            if child_run:
                child_nb_map, child_tagged = child_data.get((child_ws, child_run), ({}, []))
                if child_tagged:
                    build_tree(node, child_tagged, child_nb_map, child_ws, after, before, child_data, compact=compact)
                elif act["status"] == "InProgress":
                    node.add(Text("⏳  child pipeline starting…", style="bold yellow"))
                else:
                    node.add(Text("(no activities yet)", style="dim"))
            else:
                node.add(Text("(child run ID not yet available)", style="dim"))


def _build_foreach_children(fe_node, children: List[dict], nb_map: dict, ws_name: str, items: dict, compact: bool = False) -> None:
    header = fe_node.add(Text(f"↻  {len(children)} iteration(s)", style="bold magenta"))
    for child in children:
        label = make_activity_label(child, ws_name, nb_map, items)
        cnode = header.add(label)
        attach_activity_details(cnode, child, nb_map, compact=compact)


# ──────────────────────────────────────────────────────────────────────────────
# Header panel
# ──────────────────────────────────────────────────────────────────────────────

def print_header(pipeline: str, run_id: str, master: dict, style: str, sym: str) -> None:
    start_utc = master.get("startTimeUtc", "—")
    end_utc   = master.get("endTimeUtc") or "—"
    status    = master["status"]
    err_msg   = (master.get("failureReason") or {}).get("message") or ""
    checked   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Compute duration when both timestamps are available
    duration_str = ""
    if start_utc and start_utc != "—" and end_utc and end_utc != "—":
        try:
            fmt = "%Y-%m-%dT%H:%M:%S"
            start_dt = datetime.strptime(start_utc[:19], fmt)
            end_dt   = datetime.strptime(end_utc[:19], fmt)
            duration_str = fmt_duration(int((end_dt - start_dt).total_seconds() * 1000))
        except ValueError:
            pass

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold dim", min_width=10)
    grid.add_column()

    grid.add_row("Pipeline", Text(pipeline, style=f"bold {style}"))
    grid.add_row("Status",   Text(f"{sym}  {status}", style=style))
    grid.add_row("Run ID",   Text(run_id, style="dim"))
    grid.add_row("Started",  Text(fmt_datetime(start_utc), style="cyan"))
    grid.add_row("Ended",    Text(fmt_datetime(end_utc, "running…"), style="cyan"))
    if duration_str:
        grid.add_row("Duration", Text(duration_str, style="cyan"))
    if err_msg:
        grid.add_row("Error", Text(err_msg, style="red"))
    grid.add_row("Checked", Text(checked, style="dim"))
    grid.add_row("Cache",   Text(str(_CACHE_DIR), style="dim"))

    console.print(Panel(grid, title="[bold]Fabric Pipeline Monitor[/bold]", border_style=style, expand=False))


def print_running_summary(tagged: List[dict], ws_name_by_id: dict, nb_map: dict, items: dict) -> None:
    """Print a compact 'currently active' banner when the pipeline is InProgress."""
    running = [a for a in tagged if a.get("status") == "InProgress"]
    if not running:
        return
    console.print(Panel(
        "\n".join(
            f"[bold bright_yellow]▶  {a['activityName']}[/bold bright_yellow]"
            f"  [dim]{a['activityType']}[/dim]"
            f"  [yellow]since {fmt_time(a.get('activityRunStart'), '?')}[/yellow]"
            + (f"  [magenta]{ws_name_by_id.get((a.get('input') or {}).get('workspaceId', ''), ws_name_by_id.get('', ''))}[/magenta]" if a['activityType'] == "InvokePipeline" else "")
            for a in running
        ),
        title="[bold bright_yellow] Currently Running [/bold bright_yellow]",
        border_style="bright_yellow",
        expand=False,
    ))
    console.print()


# ──────────────────────────────────────────────────────────────────────────────
# JSON export
# ──────────────────────────────────────────────────────────────────────────────

def _activity_to_dict(act: dict, parent_name: Optional[str] = None) -> dict:
    """Convert a single activity to JSON-serializable dict."""
    inp = act.get("input") or {}
    outp = act.get("output") or {}
    err = (act.get("error") or {}).get("message") or ""
    params = extract_params(inp)

    result = {
        "name": act["activityName"],
        "type": act["activityType"],
        "status": act["status"],
        "startTime": act.get("activityRunStart"),
        "endTime": act.get("activityRunEnd"),
        "durationMs": act.get("durationInMs"),
        "durationFormatted": fmt_duration(act.get("durationInMs")),
    }

    if parent_name:
        result["forEachParent"] = parent_name

    if err:
        result["error"] = err

    if params:
        result["parameters"] = params

    # Type-specific details
    if act["activityType"] == "TridentNotebook":
        nb_id = inp.get("notebookId")
        if nb_id:
            result["notebookId"] = nb_id

    elif act["activityType"] == "InvokePipeline":
        pl_id = inp.get("pipelineId")
        child_run = outp.get("pipelineRunId")
        child_ws = inp.get("workspaceId")
        if pl_id:
            result["pipelineId"] = pl_id
        if child_run:
            result["childRunId"] = child_run
        if child_ws:
            result["childWorkspaceId"] = child_ws

    elif act["activityType"] == "Lookup":
        db = ((inp.get("datasetSettings") or {}).get("typeProperties") or {}).get("database", "")
        sql = ((inp.get("source") or {}).get("sqlReaderQuery") or "").strip()
        count = outp.get("count")
        if db:
            result["database"] = db
        if sql:
            result["query"] = sql
        if count is not None:
            result["rowCount"] = count

    elif act["activityType"] == "SetVariable":
        var_name = inp.get("variableName", "")
        var_val = inp.get("value", "")
        if var_name:
            result["variableName"] = var_name
            result["variableValue"] = var_val

    return result


def export_to_json(filepath: str, master: dict, tagged: List[dict], nb_map: dict) -> None:
    """Export pipeline run to JSON file."""
    # Build ForEach parent mapping
    fe_names = {a["activityName"] for a in tagged if a["activityType"] == "ForEach"}
    foreach_windows = {
        a["activityName"]: (a["activityRunStart"], a.get("activityRunEnd") or "2099")
        for a in tagged if a["activityType"] == "ForEach"
    }

    # Categorize activities
    top_level = []
    foreach_children = {}

    for act in tagged:
        if act["activityType"] == "ForEach":
            top_level.append(_activity_to_dict(act))
        else:
            start = act.get("activityRunStart", "")
            parent = None
            for fe_name, (fe_start, fe_end) in foreach_windows.items():
                if fe_start <= start <= fe_end:
                    parent = fe_name
                    break
            if parent:
                foreach_children.setdefault(parent, []).append(_activity_to_dict(act, parent_name=parent))
            else:
                top_level.append(_activity_to_dict(act))

    # Add ForEach children back into their parents
    for activity in top_level:
        if activity["type"] == "ForEach" and activity["name"] in foreach_children:
            activity["children"] = foreach_children[activity["name"]]

    start_utc = master.get("startTimeUtc", "—")
    end_utc = master.get("endTimeUtc") or "—"
    duration_ms = None
    if start_utc and start_utc != "—" and end_utc and end_utc != "—":
        try:
            fmt = "%Y-%m-%dT%H:%M:%S"
            start_dt = datetime.strptime(start_utc[:19], fmt)
            end_dt = datetime.strptime(end_utc[:19], fmt)
            duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
        except ValueError:
            pass

    export_data = {
        "pipeline": {
            "status": master["status"],
            "startTime": start_utc,
            "endTime": end_utc,
            "durationMs": duration_ms,
            "durationFormatted": fmt_duration(duration_ms) if duration_ms else "—",
            "error": (master.get("failureReason") or {}).get("message") or None,
        },
        "activities": top_level,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
    }

    path = Path(filepath)
    path.write_text(json.dumps(export_data, indent=2))
    console.print(f"[green]✓ Exported to:[/green] {path.absolute()}")


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _run_selector(value: str) -> str:
    """Validate --run-selector: must be a positive integer or a UUID."""
    if value.isdigit():
        if int(value) < 1:
            raise argparse.ArgumentTypeError("run index must be >= 1")
        return value
    if _UUID_RE.match(value):
        return value
    raise argparse.ArgumentTypeError(f"expected a positive integer or UUID, got: {value!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="track_pipeline.py",
        description="Monitor a Fabric pipeline run with rich visualisation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh\n"
            "  %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh --compact\n"
            "  %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh --export run.json\n"
            "  %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh --run-selector 2\n"
            "  %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh --run-selector a89f98aa-...\n"
            "  %(prog)s --clear-cache\n"
            "  watch -n 30 %(prog)s 'Facilities-Lakehouse-Dev' PL_Master_Full_Refresh --compact"
        ),
    )
    parser.add_argument("workspace", nargs="?", help="Fabric workspace name")
    parser.add_argument("pipeline",  nargs="?", help="Data pipeline name")
    parser.add_argument(
        "--run-selector", metavar="N|UUID", default=None, type=_run_selector,
        help="Which run to inspect: 1=latest (default), 2=second-most-recent, … or a run UUID",
    )
    parser.add_argument(
        "--clear-cache", action="store_true",
        help="Clear the local metadata cache and exit",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Compact mode: hide parameters, lookup results, and SetVariable details (errors always shown)",
    )
    parser.add_argument(
        "--export", metavar="FILE.json", default=None,
        help="Export run details to a JSON file (no output shown if exporting)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Dump raw activity JSON for InvokePipeline activities (for troubleshooting)",
    )
    args = parser.parse_args()

    if not args.clear_cache and (not args.workspace or not args.pipeline):
        parser.error("workspace and pipeline are required unless --clear-cache is used")

    return args


def main() -> None:
    args = parse_args()

    if args.clear_cache:
        cache_clear()
        sys.exit(0)

    workspace = args.workspace
    pipeline  = args.pipeline

    ws_id = get_workspace_id(workspace)
    if not ws_id:
        console.print(f"[red]❌ Workspace '{workspace}' not found.[/red]")
        sys.exit(1)

    run_id = get_run_id(workspace, pipeline, args.run_selector)
    master = get_run_status(workspace, pipeline, run_id)

    status    = master["status"]
    start_utc = master.get("startTimeUtc", "—")
    sym, style = status_style(status)

    after  = start_utc if start_utc and start_utc != "—" else start_utc[:10] + "T00:00:00Z"
    before = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch activities and warm the items cache in parallel
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_acts  = ex.submit(get_activity_runs, ws_id, run_id, after, before)
        fut_items = ex.submit(get_items, ws_id)
        acts      = fut_acts.result()
        fut_items.result()

    if not acts:
        if not args.export:
            print_header(pipeline, run_id, master, style, sym)
            console.print("[dim]  (no activities yet)[/dim]")
        return

    nb_map = get_notebooks(ws_id)
    tagged = tag_foreach_children(acts)

    if getattr(args, "debug", False):
        invoke_acts = [a for a in tagged if a["activityType"] == "InvokePipeline"]
        console.print(f"\n[bold yellow]DEBUG: {len(invoke_acts)} InvokePipeline activity(ies)[/bold yellow]")
        for a in invoke_acts:
            console.print(f"\n[bold]--- {a['activityName']} (status={a['status']}) ---[/bold]")
            console.print("[dim]input:[/dim]")
            console.print(json.dumps(a.get("input") or {}, indent=2))
            console.print("[dim]output:[/dim]")
            console.print(json.dumps(a.get("output") or {}, indent=2))
        sys.exit(0)

    if args.export:
        export_to_json(args.export, master, tagged, nb_map)
    else:
        print_header(pipeline, run_id, master, style, sym)

        ws_name_by_id = {v: k for k, v in get_workspaces().items()}
        items = get_items(ws_id)

        # Collect all tagged activities including child pipelines for the running summary
        child_data = prefetch_child_runs(tagged, after, before)
        all_tagged = list(tagged)
        for (_, _), (_, child_acts) in child_data.items():
            all_tagged.extend(child_acts)

        if status == "InProgress":
            print_running_summary(all_tagged, ws_name_by_id, nb_map, items)
            console.print()

        root_label = Text()
        root_label.append(f"{sym}  ", style=style)
        root_label.append(pipeline, style=f"bold {style}")

        tree = Tree(root_label, guide_style="dim")
        build_tree(tree, tagged, nb_map, ws_id, after, before, child_data=child_data, compact=args.compact)
        console.print(tree)


if __name__ == "__main__":
    main()
