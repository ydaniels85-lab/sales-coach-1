from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
LEADS_FILE = DATA_DIR / "leads.json"
HANDOFFS_FILE = DATA_DIR / "handoffs.json"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


def _ensure_file(path: Path, default: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    _ensure_file(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".broken")
        os.replace(path, backup)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def list_leads() -> list[dict[str, Any]]:
    return read_json(LEADS_FILE, [])


def save_leads(leads: list[dict[str, Any]]) -> None:
    write_json(LEADS_FILE, leads)


def list_handoffs() -> list[dict[str, Any]]:
    return read_json(HANDOFFS_FILE, [])


def save_handoffs(handoffs: list[dict[str, Any]]) -> None:
    write_json(HANDOFFS_FILE, handoffs)


def find_lead(lead_id: str) -> dict[str, Any] | None:
    return next((lead for lead in list_leads() if lead.get("id") == lead_id), None)


def update_lead(lead_id: str, updater: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
    leads = list_leads()
    for index, lead in enumerate(leads):
        if lead.get("id") == lead_id:
            updated = updater(dict(lead))
            leads[index] = updated
            save_leads(leads)
            return updated
    return None
