"""Scrittura atomica di ``status.json`` per sessione (fuori dal core)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autonode.core.sandbox.session_paths import session_status_file, validate_session_id


def write_session_status(session_id: str, payload: dict[str, Any]) -> None:
    """Write ``status.json`` atomically (temp + replace)."""
    sid = validate_session_id(session_id)
    path = Path(session_status_file(sid))
    path.parent.mkdir(parents=True, exist_ok=True)
    body = dict(payload)
    body.setdefault("updated_at", datetime.now(UTC).isoformat())
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
