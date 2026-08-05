from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_portal_link(lead_id: str, link_type: str) -> dict[str, Any]:
    token = secrets.token_urlsafe(18)
    return {
        "type": link_type,
        "token": token,
        "url": f"{FRONTEND_BASE_URL}/portal/{link_type}/{token}",
        "api_url": f"{PUBLIC_BASE_URL}/api/portal/{link_type}/{token}",
        "lead_id": lead_id,
        "created_at": utc_now(),
        "status": "created",
    }
