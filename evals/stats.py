from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_run_records(runs_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(p.read_text())
        for p in sorted(runs_dir.glob("*.json"))
    ]


def interval_stats(records: list[dict[str, Any]], interval_name: str) -> dict[str, Any]:
    durations = [
        iv["duration_ms"]
        for r in records
        for iv in r.get("intervals", [])
        if iv["name"] == interval_name and iv["duration_ms"] is not None
    ]
    if not durations:
        return {"interval": interval_name, "count": 0}
    return {
        "interval": interval_name,
        "count": len(durations),
        "min_ms": min(durations),
        "max_ms": max(durations),
        "avg_ms": round(sum(durations) / len(durations), 2),
    }


def run_summary(runs_dir: Path) -> dict[str, Any]:
    records = load_run_records(runs_dir)
    statuses = [r["status"] for r in records]
    return {
        "total": len(records),
        "complete": statuses.count("complete"),
        "failed": statuses.count("failed"),
        "pending": statuses.count("pending"),
    }
