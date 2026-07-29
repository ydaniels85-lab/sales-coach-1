from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import re
import uuid

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

TENANTS_FILE = DATA_DIR / "tenants.json"
CLIENTS_FILE = DATA_DIR / "clients.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Tenant-ID", "x-tenant-id"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


DEFAULT_TENANTS = [
    {
        "id": "fin-tastic",
        "name": "Fin-Tastic Enterprise",
        "companyName": "Fin-Tastic Enterprise",
        "ncrNumber": "",
        "email": "ydaniels85@gmail.com",
        "phone": "0642965776",
        "status": "active",
        "active": True,
        "createdAt": "2026-01-01T00:00:00Z",
    }
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_list(path: Path, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                return value
    except Exception:
        pass
    path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return list(default)


def write_list(path: Path, value: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def money(value: Any) -> float:
    raw = str(value or "")
    raw = re.sub(r"(?i)\b(?:zar|r)\b", "", raw)
    raw = re.sub(r"[^0-9,.\-]", "", raw)
    if not raw:
        return 0.0
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        tail = raw.rsplit(",", 1)[-1]
        raw = raw.replace(",", ".") if len(tail) == 2 else raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def extract_pdf_text(path: Path) -> str:
    parts: list[str] = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(path) as pdf:
                parts = [(page.extract_text() or "") for page in pdf.pages]
        except Exception:
            parts = []

    text = "\n".join(parts).strip()
    if len(text) < 50 and PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:
            pass
    return text


def first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.M)
        if match:
            return clean(match.group(1))
    return ""


def detect_bureau(text: str) -> str:
    lower = text.lower()
    if "datanamix" in lower:
        return "Datanamix"
    if "xds" in lower:
        return "XDS"
    if "transunion" in lower:
        return "TransUnion"
    if "experian" in lower:
        return "Experian"
    if "compuscan" in lower or "mycreditcheck" in lower:
        return "Compuscan"
    return "Unknown"


def parse_accounts(text: str) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    lines = [clean(line) for line in text.splitlines() if clean(line)]
    creditor_words = (
        "bank", "capitec", "nedbank", "absa", "standard", "fnb", "wesbank",
        "loan", "finance", "stores", "credit", "card", "telkom", "vodacom",
        "mtn", "lewis", "homechoice", "truworths", "edgars", "foschini"
    )

    amount_pattern = re.compile(r"(?:R|ZAR)\s*([0-9][0-9 ,.]*[,.][0-9]{2})", re.I)
    for line in lines:
        lower = line.lower()
        if not any(word in lower for word in creditor_words):
            continue
        values = [money(v) for v in amount_pattern.findall(line)]
        if not values:
            continue

        first_amount = re.search(r"(?:R|ZAR)\s*[0-9]", line, re.I)
        name = clean(line[:first_amount.start()] if first_amount else line)
        name = re.sub(r"\b\d{6,}\b.*$", "", name).strip(" -:|")
        if len(name) < 3:
            continue

        account_number_match = re.search(r"\b[A-Z0-9\-]{6,}\b", line, re.I)
        account_number = account_number_match.group(0) if account_number_match else ""

        current = values[-1]
        monthly = values[-2] if len(values) >= 2 else 0.0
        opening = values[0] if len(values) >= 3 else current
        arrears = values[-3] if len(values) >= 4 else 0.0

        accounts.append({
            "id": f"acc-{uuid.uuid4().hex[:10]}",
            "creditorName": name[:100],
            "accountNumber": account_number,
            "openingBalance": opening,
            "currentBalance": current,
            "arrearsAmount": arrears,
            "monthlyInstalment": monthly,
            "reducedAmount": round(monthly * 0.65, 2) if monthly else 0.0,
            "accountStatus": "Active",
            "included": True,
        })

    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, float]] = set()
    for item in accounts:
        marker = (
            item["creditorName"].lower(),
            item["accountNumber"],
            item["currentBalance"],
        )
        if marker not in seen:
            seen.add(marker)
            unique.append(item)
    return unique[:100]


def parse_report(path: Path) -> dict[str, Any]:
    text = extract_pdf_text(path)
    bureau = detect_bureau(text)

    full_name = first_match(text, [
        r"(?:consumer|client|applicant)\s*(?:full\s*)?name\s*[:\-]\s*([A-Z][A-Za-z .'\-]{3,})",
        r"\bname\s*[:\-]\s*([A-Z][A-Za-z .'\-]{3,})",
    ])
    id_number = first_match(text, [
        r"(?:id|identity)\s*(?:number|no\.?)\s*[:\-]?\s*(\d{13})",
        r"\b(\d{13})\b",
    ])
    phone = first_match(text, [
        r"(?:cell|mobile|telephone|phone)\s*[:\-]?\s*(0\d{9})",
    ])
    email = first_match(text, [
        r"\b([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})\b",
    ])

    under_debt_review = bool(re.search(
        r"under\s+debt\s+review|debt\s+review\s+listed|debt\s+review\s+indicator",
        text,
        re.I,
    ))
    accounts = parse_accounts(text)
    warnings: list[str] = []
    if not text:
        warnings.append(
            "No extractable text was found. This PDF may be scanned and require OCR/Tesseract."
        )
    if not full_name:
        warnings.append("Client full name was not confidently detected.")
    if not id_number:
        warnings.append("Client ID number was not confidently detected.")
    if not accounts:
        warnings.append("No account rows were confidently detected.")

    confidence = 20
    confidence += 15 if bureau != "Unknown" else 0
    confidence += 20 if full_name else 0
    confidence += 20 if id_number else 0
    confidence += 25 if accounts else 0

    return {
        "bureau": bureau,
        "confidence": min(confidence, 100),
        "textLength": len(text),
        "warnings": warnings,
        "consumer": {
            "fullName": full_name,
            "idNumber": id_number,
            "tel": phone,
            "whatsapp": phone,
            "email": email,
        },
        "accounts": accounts,
        "flags": {
            "underDebtReview": under_debt_review,
            "debtReviewListed": under_debt_review,
        },
    }


def tenant_from_request() -> str:
    return (
        request.headers.get("X-Tenant-ID")
        or request.headers.get("x-tenant-id")
        or request.form.get("tenant_id")
        or "fin-tastic"
    )


@app.get("/")
def home():
    return jsonify({
        "app": "Fin-Tastic Enterprise",
        "status": "running",
        "api": "/api/health",
    })


@app.get("/api/health")
@app.get("/health")
def health():
    return jsonify({"success": True, "status": "ok", "parser": "ready"})


@app.get("/api/me")
def me():
    return jsonify({
        "success": True,
        "user": {
            "id": "admin",
            "name": "Yunoos Daniels",
            "email": "ydaniels85@gmail.com",
            "role": "super_admin",
            "isActive": True,
        },
    })


@app.route("/api/tenants", methods=["GET", "POST"])
def tenants_route():
    tenants = read_list(TENANTS_FILE, DEFAULT_TENANTS)

    if request.method == "GET":
        return jsonify({
            "success": True,
            "tenants": tenants,
            "currentTenant": tenants[0] if tenants else None,
        })

    payload = request.get_json(silent=True) or {}
    name = clean(payload.get("name") or payload.get("companyName") or payload.get("company_name"))
    if not name:
        return jsonify({"success": False, "error": "Tenant name is required."}), 400

    tenant = {
        "id": f"tenant-{uuid.uuid4().hex[:10]}",
        "name": name,
        "companyName": clean(payload.get("companyName") or name),
        "ncrNumber": clean(payload.get("ncrNumber") or payload.get("ncr_number")),
        "email": clean(payload.get("email")),
        "phone": clean(payload.get("phone")),
        "status": "active",
        "active": True,
        "createdAt": now_iso(),
    }
    tenants.append(tenant)
    write_list(TENANTS_FILE, tenants)

    return jsonify({
        "success": True,
        "tenant": tenant,
        "tenants": tenants,
    }), 201


@app.route("/api/tenants/<tenant_id>", methods=["GET", "PUT"])
def tenant_detail(tenant_id: str):
    tenants = read_list(TENANTS_FILE, DEFAULT_TENANTS)
    index = next((i for i, item in enumerate(tenants) if item.get("id") == tenant_id), None)
    if index is None:
        return jsonify({"success": False, "error": "Tenant not found."}), 404

    if request.method == "GET":
        return jsonify({"success": True, "tenant": tenants[index]})

    payload = request.get_json(silent=True) or {}
    allowed = {"name", "companyName", "ncrNumber", "email", "phone", "status", "active"}
    for field in allowed:
        if field in payload:
            tenants[index][field] = payload[field]
    tenants[index]["updatedAt"] = now_iso()
    write_list(TENANTS_FILE, tenants)
    return jsonify({"success": True, "tenant": tenants[index]})


@app.get("/api/clients")
def clients_route():
    tenant_id = request.headers.get("X-Tenant-ID") or request.args.get("tenantId")
    clients = read_list(CLIENTS_FILE, [])
    if tenant_id:
        clients = [client for client in clients if client.get("tenantId") == tenant_id]
    return jsonify({"success": True, "clients": clients, "cases": clients})


@app.post("/api/upload/credit-report")
@app.post("/api/upload")
@app.post("/api/analyze-report")
def upload_credit_report():
    upload = (
        request.files.get("file")
        or request.files.get("creditReport")
        or request.files.get("report")
        or request.files.get("document")
    )
    if upload is None or not upload.filename:
        return jsonify({"success": False, "error": "Please select a PDF credit report."}), 400
    if not upload.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF credit reports are supported."}), 400

    filename = secure_filename(upload.filename)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    path = UPLOAD_DIR / stored_name
    upload.save(path)

    parsed = parse_report(path)
    consumer = parsed["consumer"]
    accounts = parsed["accounts"]
    tenant_id = tenant_from_request()

    client = {
        "id": f"client-{uuid.uuid4().hex[:12]}",
        "tenantId": tenant_id,
        "caseNumber": f"FT-{uuid.uuid4().hex[:6].upper()}",
        "serviceType": (
            "debt_review_removal"
            if parsed["flags"]["underDebtReview"]
            else "debt_mediation"
        ),
        "applicationType": "single",
        "workflowStage": "Credit Report Parsed",
        "primaryApplicant": {
            "fullName": consumer.get("fullName", ""),
            "idNumber": consumer.get("idNumber", ""),
            "tel": consumer.get("tel", ""),
            "whatsapp": consumer.get("whatsapp", ""),
            "email": consumer.get("email", ""),
            "physicalAddress": "",
            "employment": "",
            "salaryFrequency": "monthly",
            "nettSalary": 0,
            "livingExpenses": 0,
            "bankAccountHolder": "",
            "bankName": "",
            "bankAccountType": "",
            "bankBranchCode": "",
            "bankAccountNumber": "",
        },
        "jointApplicant": {},
        "accounts": accounts,
        "flags": parsed["flags"],
        "creditReport": {
            "filename": filename,
            "storedFilename": stored_name,
            "bureau": parsed["bureau"],
            "confidence": parsed["confidence"],
            "warnings": parsed["warnings"],
            "textLength": parsed["textLength"],
            "uploadedAt": now_iso(),
        },
        "workflow": {
            "currentStage": "credit_report_parsed",
            "currentStageLabel": "Credit Report Parsed",
            "nextActions": [
                "Review parsed client details.",
                "Review all account balances and instalments.",
                "Confirm the recommended service.",
            ],
        },
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }

    clients = read_list(CLIENTS_FILE, [])
    clients.insert(0, client)
    write_list(CLIENTS_FILE, clients)

    return jsonify({
        "success": True,
        "message": "Credit report uploaded and parsed.",
        "client": client,
        "result": {
            "client": client,
            "consumer": consumer,
            "accounts": accounts,
            "bureau": parsed["bureau"],
            "confidence": parsed["confidence"],
            "warnings": parsed["warnings"],
        },
        "parsed": parsed,
        "accounts": accounts,
        "warnings": parsed["warnings"],
    }), 201


@app.post("/api/clients/<client_id>/credit-report")
def upload_existing_client_report(client_id: str):
    # For compatibility, use the normal parser and return a newly created client.
    return upload_credit_report()


@app.get("/api/debug/routes")
def debug_routes():
    return jsonify({
        "success": True,
        "routes": [
            {"rule": str(rule), "methods": sorted(rule.methods)}
            for rule in app.url_map.iter_rules()
        ],
    })


@app.errorhandler(404)
def not_found(_error):
    return jsonify({
        "success": False,
        "error": "Not found",
        "path": request.path,
        "hint": "Check /api/debug/routes",
    }), 404


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({"success": False, "error": "The file is larger than 25 MB."}), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "1") == "1",
    )
