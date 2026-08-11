"""Audit-Log — adaptiert aus drift_limiter/store.py.

Append-only JSONL unter .ida-gate/events.jsonl. Bewusst simpel: jede
Gate-Entscheidung ist eine Zeile, offline lesbar, git-diffbar, EU-AI-Act-tauglich.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AuditEvent

STATE_DIR = ".ida-gate"
EVENT_LOG = "events.jsonl"


def resolve_state_dir(workspace: str | Path) -> Path:
    return Path(workspace).expanduser().resolve() / STATE_DIR


def ensure_state_dir(workspace: str | Path) -> Path:
    state_dir = resolve_state_dir(workspace)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def event_log_path(workspace: str | Path) -> Path:
    return resolve_state_dir(workspace) / EVENT_LOG


def append_event(workspace: str | Path, event: AuditEvent) -> None:
    ensure_state_dir(workspace)
    with event_log_path(workspace).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def read_events(workspace: str | Path) -> list[dict[str, Any]]:
    path = event_log_path(workspace)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events
