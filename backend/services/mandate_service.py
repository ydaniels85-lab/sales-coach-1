from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any


def create_nupay_mandate(lead: dict[str, Any], amount: float, debit_day: int | None = None) -> dict[str, Any]:
    """
    Safe placeholder NuPay/DebiCheck adapter.

    Replace this mock with the real NuPay API once merchant credentials and the official API contract are available.
    Never hard-code production credentials in this file. Use environment variables instead.
    """
    mode = os.getenv("NUPAY_MODE", "mock").lower()
    reference = f"NP-MOCK-{secrets.token_hex(4).upper()}"
    client = lead.get("parsed", {}).get("client", {})
    return {
        "mode": mode,
        "provider": "NuPay",
        "reference": reference,
        "lead_id": lead.get("id"),
        "client_name": client.get("full_name", "Unknown Client"),
        "amount": round(float(amount or 0), 2),
        "debit_day": debit_day,
        "status": "pending_client_authorisation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": "Mock mandate created. Replace with live NuPay API call when credentials are available.",
    }
