from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def run_state_path(root: Path, run_id: str) -> Path:
    if not SAFE_ID.fullmatch(run_id):
        raise ValueError("Invalid TideAware run id")
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{run_id}.json"


def write_run_state(path: Path, payload: dict[str, Any]) -> None:
    partial = path.with_suffix(f".{os.getpid()}.part")
    partial.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(partial, path)


def read_run_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None
