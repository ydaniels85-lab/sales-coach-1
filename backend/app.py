from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from parsers.credit_report_parser import parse_credit_report
from services.link_service import make_portal_link, utc_now
from services.mandate_service import create_nupay_mandate
from services.sales_coach import build_sales_coach
from storage import UPLOAD_DIR, list_handoffs, list_leads, save_handoffs, save_leads, update_lead

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

ALLOWED_EXTENSIONS = {"pdf"}


def ok(payload: Any = None, status: int = 200):
    data = {"success": True}
    if isinstance(payload, dict):
        data.update(payload)
    elif payload is not None:
        data["data"] = payload
    return jsonify(data), status


def fail(message: str, status: int = 400, **extra):
    return jsonify({"success": False, "error": message, **extra}), status


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_lead(parsed: dict[str, Any], file_info: dict[str, Any] | None = None, source: str = "upload") -> dict[str, Any]:
    lead_id = f"lead-{uuid.uuid4().hex[:10]}"
    coach = build_sales_coach(parsed)
    client = parsed.get("client", {})
    return {
        "id": lead_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source": source,
        "stage": "Credit Report Parsed",
        "status": "open",
        "client_name": client.get("full_name") or "Unknown Client",
        "client_phone": client.get("phone", ""),
        "client_email": client.get("email", ""),
        "recommended_service": coach.get("service_recommendation"),
        "lead_temperature": coach.get("lead_temperature"),
        "parsed": parsed,
        "sales_coach": coach,
        "file": file_info or {},
        "actions": {
            "signature_link": None,
            "document_link": None,
            "nupay_mandate": None,
            "sale_closed": False,
            "admin_handoff": False,
        },
        "consultant_notes": [],
    }


@app.get("/")
def root():
    return ok({"app": "Fin-Tastic Sales Coach API", "health": "/api/health"})


@app.get("/api/health")
@app.get("/health")
def health():
    return ok({"service": "fin-tastic-sales-coach", "status": "healthy", "time": utc_now()})


@app.get("/api/debug/routes")
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"rule": str(rule), "methods": sorted(rule.methods or [])})
    return ok({"routes": routes})


@app.post("/api/upload/credit-report")
def upload_credit_report():
    if "file" not in request.files:
        return fail("No file part named 'file' was uploaded.", 400)
    file = request.files["file"]
    if not file or not file.filename:
        return fail("No selected file.", 400)
    if not allowed_file(file.filename):
        return fail("Only PDF files are allowed.", 400)

    original_name = file.filename
    safe_name = secure_filename(original_name)
    stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe_name}"
    target = UPLOAD_DIR / stored_name
    file.save(target)

    parsed = parse_credit_report(target)
    manual_name = request.form.get("client_name", "").strip()
    if manual_name and parsed.get("client"):
        parsed["client"]["full_name"] = manual_name

    lead = make_lead(parsed, {"original_name": original_name, "stored_name": stored_name, "path": str(target)})
    leads = list_leads()
    leads.insert(0, lead)
    save_leads(leads)
    return ok({"lead": lead, "parsed": parsed})


@app.get("/api/leads")
def get_leads():
    return ok({"leads": list_leads()})


@app.post("/api/leads")
def create_manual_lead():
    payload = request.get_json(silent=True) or {}
    parsed = {
        "bureau": "Manual",
        "client": {
            "full_name": payload.get("client_name") or "Manual Lead",
            "phone": payload.get("phone", ""),
            "email": payload.get("email", ""),
            "id_number": payload.get("id_number", ""),
        },
        "report": {
            "filename": "manual",
            "credit_score": payload.get("credit_score"),
            "debt_review_flag": bool(payload.get("debt_review_flag")),
            "parser_warning": "Manual lead. Upload a credit report for accurate coaching.",
        },
        "totals": {
            "active_balance_total": float(payload.get("active_balance_total") or 0),
            "arrears_total": float(payload.get("arrears_total") or 0),
            "reduced_total": float(payload.get("reduced_total") or 0),
            "account_count": 0,
            "furniture_account_count": 0,
        },
        "accounts": [],
        "flags": {
            "score_zero": payload.get("credit_score") == 0,
            "has_active_balances": float(payload.get("active_balance_total") or 0) > 0,
            "has_arrears": float(payload.get("arrears_total") or 0) > 0,
            "needs_admin_review": True,
        },
    }
    lead = make_lead(parsed, source="manual")
    leads = list_leads()
    leads.insert(0, lead)
    save_leads(leads)
    return ok({"lead": lead}, 201)


@app.get("/api/leads/<lead_id>")
def get_lead(lead_id: str):
    lead = next((item for item in list_leads() if item.get("id") == lead_id), None)
    if not lead:
        return fail("Lead not found.", 404)
    return ok({"lead": lead})


def _lead_or_404(lead_id: str):
    lead = next((item for item in list_leads() if item.get("id") == lead_id), None)
    if not lead:
        return None, fail("Lead not found.", 404)
    return lead, None


@app.post("/api/leads/<lead_id>/send-signature-link")
def send_signature_link(lead_id: str):
    lead, error = _lead_or_404(lead_id)
    if error:
        return error
    link = make_portal_link(lead_id, "signature")

    def updater(item: dict[str, Any]):
        item["updated_at"] = utc_now()
        item["stage"] = "Signature Link Sent"
        item.setdefault("actions", {})["signature_link"] = link
        return item

    updated = update_lead(lead_id, updater)
    return ok({"lead": updated, "link": link})


@app.post("/api/leads/<lead_id>/send-document-link")
def send_document_link(lead_id: str):
    lead, error = _lead_or_404(lead_id)
    if error:
        return error
    link = make_portal_link(lead_id, "documents")

    def updater(item: dict[str, Any]):
        item["updated_at"] = utc_now()
        item["stage"] = "Document Upload Link Sent"
        item.setdefault("actions", {})["document_link"] = link
        return item

    updated = update_lead(lead_id, updater)
    return ok({"lead": updated, "link": link})


@app.post("/api/leads/<lead_id>/send-nupay-mandate")
def send_nupay_mandate(lead_id: str):
    payload = request.get_json(silent=True) or {}
    lead, error = _lead_or_404(lead_id)
    if error:
        return error

    suggested = (lead.get("sales_coach", {}).get("money_summary", {}) or {}).get("suggested_reduced_total", 0)
    amount = float(payload.get("amount") or suggested or 0)
    debit_day = payload.get("debit_day")
    if debit_day not in (None, ""):
        try:
            debit_day = int(debit_day)
        except ValueError:
            return fail("debit_day must be a number from 1 to 31.", 400)
        if debit_day < 1 or debit_day > 31:
            return fail("debit_day must be between 1 and 31.", 400)
    mandate = create_nupay_mandate(lead, amount, debit_day)

    def updater(item: dict[str, Any]):
        item["updated_at"] = utc_now()
        item["stage"] = "NuPay Mandate Sent"
        item.setdefault("actions", {})["nupay_mandate"] = mandate
        return item

    updated = update_lead(lead_id, updater)
    return ok({"lead": updated, "mandate": mandate})


@app.post("/api/leads/<lead_id>/close-sale")
def close_sale(lead_id: str):
    payload = request.get_json(silent=True) or {}
    note = payload.get("note", "Sale closed by consultant.")

    def updater(item: dict[str, Any]):
        item["updated_at"] = utc_now()
        item["stage"] = "Sale Closed"
        item["status"] = "closed"
        item.setdefault("actions", {})["sale_closed"] = True
        item.setdefault("consultant_notes", []).append({"time": utc_now(), "note": note})
        return item

    updated = update_lead(lead_id, updater)
    if not updated:
        return fail("Lead not found.", 404)
    return ok({"lead": updated})


@app.post("/api/leads/<lead_id>/pass-to-admin")
def pass_to_admin(lead_id: str):
    payload = request.get_json(silent=True) or {}
    lead, error = _lead_or_404(lead_id)
    if error:
        return error
    handoff_id = f"handoff-{uuid.uuid4().hex[:10]}"
    handoff = {
        "id": handoff_id,
        "lead_id": lead_id,
        "created_at": utc_now(),
        "status": "new",
        "admin_stage": "Admin Intake",
        "client_name": lead.get("client_name"),
        "recommended_service": lead.get("recommended_service"),
        "lead_temperature": lead.get("lead_temperature"),
        "summary": lead.get("sales_coach", {}).get("reason"),
        "actions": lead.get("actions", {}),
        "parsed": lead.get("parsed", {}),
        "sales_coach": lead.get("sales_coach", {}),
        "handoff_note": payload.get("note", "Passed to admin for workflow/PDA processing."),
    }
    handoffs = list_handoffs()
    handoffs.insert(0, handoff)
    save_handoffs(handoffs)

    def updater(item: dict[str, Any]):
        item["updated_at"] = utc_now()
        item["stage"] = "Passed To Admin"
        item.setdefault("actions", {})["admin_handoff"] = True
        item["handoff_id"] = handoff_id
        return item

    updated = update_lead(lead_id, updater)
    return ok({"lead": updated, "handoff": handoff})


@app.get("/api/admin/handoffs")
def get_handoffs():
    return ok({"handoffs": list_handoffs()})


@app.get("/api/uploads/<path:filename>")
def get_upload(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/api/portal/<link_type>/<token>")
def portal_link(link_type: str, token: str):
    return ok({
        "link_type": link_type,
        "token": token,
        "status": "demo_link_active",
        "message": "This is a demo portal endpoint. Connect this to your real e-sign/document portal later.",
    })


@app.errorhandler(404)
def not_found(error):
    return fail("Not found", 404, path=request.path, hint="Check /api/debug/routes")


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
