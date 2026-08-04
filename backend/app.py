"""
Fin-Tastic Sales Coach - Multi-Tenant Refined Backend

Run:
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  python app.py

Tenant isolation rule:
  Every client, upload, user list, and portal link is scoped to X-Tenant-ID.
  Users inside the same tenant share the same tenant client database.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover
    pdfplumber = None

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

try:
    import pypdfium2 as pdfium  # type: ignore
except Exception:  # pragma: no cover
    pdfium = None

APP_NAME = "Fin-Tastic Sales Coach API"
APP_VERSION = "2026.07-datanamix-ocr-parser-fix"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("FINTASTIC_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = Path(os.environ.get("FINTASTIC_UPLOAD_DIR", str(DATA_DIR / "uploads")))
FRONTEND_DIST = BASE_DIR / "frontend_dist"
DB_PATH = DATA_DIR / "sales_coach_db.json"
for folder in (DATA_DIR, UPLOAD_DIR):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Tenant-ID", "x-tenant-id", "X-User-ID", "x-user-id", "Accept", "Origin"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

DEFAULT_TENANTS = [
    {
        "id": "liberty-credit-specialists",
        "name": "Liberty Credit Specialists",
        "ncr": "NCRDC-1829",
        "users": [
            {"id": "lib-admin", "name": "Yunoos Daniels", "role": "Admin", "email": "ydaniels85@gmail.com"},
            {"id": "lib-agent-1", "name": "Sales Agent 1", "role": "Consultant", "email": "agent1@liberty.local"},
            {"id": "lib-manager", "name": "Manager", "role": "Manager", "email": "manager@liberty.local"},
        ],
    },
    {
        "id": "apex-debt-solutions",
        "name": "Apex Debt Solutions",
        "ncr": "NCRDC-2491",
        "users": [
            {"id": "apex-admin", "name": "Apex Admin", "role": "Admin", "email": "admin@apex.local"},
            {"id": "apex-agent-1", "name": "Apex Consultant", "role": "Consultant", "email": "consultant@apex.local"},
        ],
    },
    {
        "id": "pretoria-debt-administrators",
        "name": "Pretoria Debt Administrators",
        "ncr": "NCRDC-0083",
        "users": [
            {"id": "pta-admin", "name": "Pretoria Admin", "role": "Admin", "email": "admin@pta.local"},
            {"id": "pta-agent-1", "name": "Pretoria Consultant", "role": "Consultant", "email": "consultant@pta.local"},
        ],
    },
]

CREDITOR_DIRECTORY: Dict[str, Dict[str, str]] = {
    "absa": {"name": "ABSA", "department": "Debt Review Department", "email": "debtreview@absa.co.za", "phone": "0860 111 007"},
    "standard bank": {"name": "Standard Bank", "department": "Debt Review Department", "email": "debt.review@standardbank.co.za", "phone": "0860 123 000"},
    "fnb": {"name": "FNB", "department": "Debt Review Department", "email": "debtreview@fnb.co.za", "phone": "087 575 9404"},
    "first national bank": {"name": "FNB", "department": "Debt Review Department", "email": "debtreview@fnb.co.za", "phone": "087 575 9404"},
    "nedbank": {"name": "Nedbank", "department": "Debt Review Department", "email": "debtreview@nedbank.co.za", "phone": "0860 555 111"},
    "capitec": {"name": "Capitec", "department": "Debt Review Department", "email": "debtcare@capitecbank.co.za", "phone": "0860 102 043"},
    "african bank": {"name": "African Bank", "department": "Debt Review Department", "email": "debtreview@africanbank.co.za", "phone": "0861 111 011"},
    "wesbank": {"name": "WesBank", "department": "Debt Review Department", "email": "debt.review@wesbank.co.za", "phone": "0861 288 272"},
    "old mutual": {"name": "Old Mutual Finance", "department": "Debt Review Department", "email": "debtreview@oldmutualfinance.co.za", "phone": "0860 445 445"},
    "truworths": {"name": "Truworths", "department": "Debt Review Department", "email": "debtreview@truworths.co.za", "phone": "021 460 2300"},
    "foschini": {"name": "TFG", "department": "Debt Review Department", "email": "debtreview@tfg.co.za", "phone": "0860 834 834"},
    "ackermans": {"name": "Ackermans", "department": "Debt Review Department", "email": "debtreview@tenacityinc.co.za", "phone": "0860 900 100"},
    "mr price": {"name": "Mr Price Money", "department": "Debt Review Department", "email": "debtreview@mrpg.com", "phone": "0800 212 535"},
    "russells": {"name": "Russells", "department": "Debt Review Department", "email": "debtreview@jdg.co.za", "phone": "0860 113 639"},
    "bradlows": {"name": "Bradlows", "department": "Debt Review Department", "email": "debtreview@jdg.co.za", "phone": "0860 113 639"},
}

FURNITURE_KEYWORDS = ["russells", "bradlows", "lewis", "beares", "ok furniture", "fair price", "house & home", "rochester", "dial-a-bed", "jd group", "jdg"]
ASSET_KEYWORDS = ["home loan", "bond", "mortgage", "vehicle", "wesbank", "mfc", "toyota financial", "vw financial", "motor", "auto"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def money_to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).replace("R", "").replace("r", "").replace(" ", "").replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return float(text) if text not in {"", ".", "-"} else default
    except ValueError:
        return default


def clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(5)}"


def default_applicant() -> Dict[str, Any]:
    return {
        "firstName": "",
        "secondName": "",
        "surname": "",
        "fullName": "",
        "idNumber": "",
        "dateOfBirth": "",
        "gender": "",
        "maritalStatus": "",
        "email": "",
        "phone": "",
        "whatsapp": "",
        "physicalAddress": "",
        "employer": "",
        "occupation": "",
        "dateEmployed": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
    }


def default_bank() -> Dict[str, Any]:
    return {
        "accountHolder": "",
        "bankName": "",
        "accountType": "",
        "branchCode": "",
        "accountNumber": "",
        "debitDay": "25",
        "mandateAccepted": False,
    }


def demo_accounts() -> List[Dict[str, Any]]:
    return [
        {
            "id": "acc-demo-001",
            "creditorName": "WesBank Vehicle Finance",
            "accountNumber": "WB-458812",
            "accountType": "Vehicle Finance",
            "openingBalance": 189000,
            "currentBalance": 142500,
            "arrears": 5900,
            "monthlyInstallment": 4850,
            "reducedAmount": 3150,
            "lastPaidDate": "2026-05-25",
            "monthsInArrears": 1,
            "openDate": "2022-08-12",
            "status": "Active",
            "included": True,
            "isFurniture": False,
            "isAsset": True,
        },
        {
            "id": "acc-demo-002",
            "creditorName": "Russells Furniture",
            "accountNumber": "RS-77218",
            "accountType": "Furniture",
            "openingBalance": 24800,
            "currentBalance": 18120,
            "arrears": 2100,
            "monthlyInstallment": 980,
            "reducedAmount": 640,
            "lastPaidDate": "2026-04-28",
            "monthsInArrears": 2,
            "openDate": "2024-11-03",
            "status": "Active",
            "included": True,
            "isFurniture": True,
            "isAsset": False,
        },
    ]


def evaluate_sales(client: Dict[str, Any], accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    score_raw = client.get("creditScore")
    score_found = bool(client.get("scoreFound")) and score_raw not in (None, "")
    score = int(money_to_float(score_raw, -1)) if score_found else None
    included = [a for a in accounts if a.get("included", True)]
    debt_review = bool(client.get("debtReviewListed")) or (score_found and score == 0)
    outstanding = sum(money_to_float(a.get("currentBalance")) for a in included)
    arrears = sum(money_to_float(a.get("arrears")) for a in included)
    original_instalment = sum(money_to_float(a.get("monthlyInstallment")) for a in included)
    reduced = sum(money_to_float(a.get("reducedAmount")) for a in included)
    has_asset = any(a.get("isAsset") or any(k in str(a.get("creditorName", "")).lower() for k in ASSET_KEYWORDS) for a in included)
    has_furniture = any(a.get("isFurniture") or any(k in str(a.get("creditorName", "")).lower() for k in FURNITURE_KEYWORDS) for a in included)

    service = "Debt Mediation"
    urgency = "Medium"
    headline = "Debt mediation opportunity detected"
    reasons: List[str] = []
    next_steps: List[str] = []
    objection_handlers: List[str] = []

    if debt_review:
        service = "Debt Review Removal"
        urgency = "High"
        headline = "Debt Review Removal lead"
        reasons.append("The report indicates a debt-review flag or zero score, so removal must be checked before any other sale.")
        if outstanding > 0:
            reasons.append("Balances are still showing, so this can become a double sale: DR removal plus mediation.")
    elif has_asset:
        service = "Debt Review Sales Coach"
        urgency = "High"
        headline = "Asset-protection opportunity"
        reasons.append("Vehicle finance, home loan, or asset-style accounts were detected. Lead with asset protection and affordability.")
    elif score_found and score is not None and 400 <= score <= 650 and arrears > 0:
        service = "Debt Mediation"
        urgency = "High"
        headline = "Mediation lead with arrears pressure"
        reasons.append("The score and arrears pattern suggest the client needs urgent negotiated relief.")
    elif outstanding > 0:
        service = "Debt Mediation"
        urgency = "Medium"
        headline = "Debt mediation lead"
        reasons.append("Outstanding balances are present and can be structured into a realistic repayment plan.")
    else:
        service = "Needs Manual Review"
        urgency = "Low"
        headline = "Manual assessment needed"
        reasons.append("The current data is not enough to recommend a safe sale.")

    if has_furniture:
        reasons.append("Furniture accounts detected. Tag these clearly because clients often ask if household goods are at risk.")
    if original_instalment > 0:
        reasons.append(f"Estimated monthly relief is R{max(0, original_instalment - reduced):,.2f} before final affordability checks.")

    if service == "Debt Review Removal":
        next_steps = [
            "Confirm whether the client is still actively under debt review or only still listed at the bureau.",
            "Request ID, proof of address, latest payslip, bank statement, and existing NCT/court documents if available.",
            "Explain the R7,000 DRR fee and offer a 1-3 month payment arrangement.",
            "If balances remain, present mediation as the second sale to restructure active debts.",
        ]
        objection_handlers = [
            "I already paid my debt counsellor: explain that paid-up history and bureau flag status must still be verified.",
            "I only want my name cleared: explain that removal is step one, but active balances can still affect affordability and score recovery.",
        ]
    elif service == "Debt Review Sales Coach":
        next_steps = [
            "Confirm income, living expenses, and whether the client is behind on home or vehicle payments.",
            "Position the conversation around protecting the asset and building a sustainable plan.",
            "Prepare Form 16, consent, credit report, and COB request workflow if the client qualifies.",
        ]
        objection_handlers = [
            "I do not want debt review: explain that assets at risk need urgent protection and eligibility must be assessed first.",
            "I can catch up next month: compare arrears and instalments against nett income before accepting that answer.",
        ]
    elif service == "Debt Mediation":
        next_steps = [
            "Confirm all income, debit orders, and living expenses before making a proposal.",
            "Use included accounts only and adjust reduced amounts to match affordability.",
            "Send mediation mandate and upload-documents link before creditor communication.",
        ]
        objection_handlers = [
            "I can pay creditors myself: explain that one coordinated proposal reduces pressure and missed promises.",
            "I am not in arrears yet: explain mediation can prevent arrears when affordability is already under pressure.",
        ]

    return {
        "service": service,
        "urgency": urgency,
        "headline": headline,
        "reasons": reasons,
        "nextSteps": next_steps,
        "objectionHandlers": objection_handlers,
        "totals": {
            "outstanding": round(outstanding, 2),
            "arrears": round(arrears, 2),
            "originalInstalment": round(original_instalment, 2),
            "reducedInstalment": round(reduced, 2),
            "estimatedRelief": round(max(0, original_instalment - reduced), 2),
        },
        "flags": {
            "debtReviewListed": debt_review,
            "hasAsset": has_asset,
            "hasFurniture": has_furniture,
            "scoreZeroRule": bool(score_found and score == 0),
            "doubleSaleCandidate": debt_review and outstanding > 0,
        },
    }


def make_client(tenant_id: str, full_name: str = "New Client", user_id: str = "system") -> Dict[str, Any]:
    client = default_applicant()
    client.update(
        {
            "id": new_id("client"),
            "tenantId": tenant_id,
            "assignedUserId": user_id,
            "applicationType": "Single",
            "fullName": full_name,
            "spouse": default_applicant(),
            "bank": default_bank(),
            "creditScore": None,
            "scoreFound": False,
            "debtReviewListed": False,
            "notes": "",
            "status": "Lead Received",
            "serviceType": "Needs Manual Review",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "accounts": [],
            "coach": evaluate_sales({"creditScore": 0, "debtReviewListed": False}, []),
            "portalLinks": {},
        }
    )
    ensure_client_workflow(client)
    return client


def create_seed_db() -> Dict[str, Any]:
    db: Dict[str, Any] = {"version": APP_VERSION, "tenants": {}}
    for tenant in DEFAULT_TENANTS:
        tenant_id = tenant["id"]
        db["tenants"][tenant_id] = {
            "id": tenant_id,
            "name": tenant["name"],
            "ncr": tenant["ncr"],
            "users": tenant["users"],
            "clients": [],
            "uploads": [],
            "createdAt": now_iso(),
        }
    demo = make_client("liberty-credit-specialists", "Demo Asset Client", "lib-agent-1")
    demo.update({"phone": "0642965776", "whatsapp": "0642965776", "email": "client@example.com", "creditScore": 512, "scoreFound": True, "status": "Credit Report Uploaded"})
    demo["accounts"] = demo_accounts()
    demo["coach"] = evaluate_sales(demo, demo["accounts"])
    demo["serviceType"] = demo["coach"]["service"]
    db["tenants"]["liberty-credit-specialists"]["clients"].append(demo)

    apex_demo = make_client("apex-debt-solutions", "Apex Tenant Demo Client", "apex-agent-1")
    apex_demo.update({"creditScore": 0, "scoreFound": True, "debtReviewListed": True, "status": "Lead Received"})
    apex_demo["accounts"] = []
    apex_demo["coach"] = evaluate_sales(apex_demo, [])
    apex_demo["serviceType"] = apex_demo["coach"]["service"]
    db["tenants"]["apex-debt-solutions"]["clients"].append(apex_demo)
    return db


def load_db() -> Dict[str, Any]:
    if not DB_PATH.exists():
        db = create_seed_db()
        save_db(db)
        return db
    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = create_seed_db()
        save_db(db)
        return db
    changed = False
    for tenant in DEFAULT_TENANTS:
        if tenant["id"] not in db.get("tenants", {}):
            db.setdefault("tenants", {})[tenant["id"]] = {**tenant, "clients": [], "uploads": [], "createdAt": now_iso()}
            changed = True
    for tenant in db.get("tenants", {}).values():
        for client in tenant.get("clients", []):
            before = json.dumps(client, sort_keys=True, default=str)
            ensure_client_workflow(client)
            if json.dumps(client, sort_keys=True, default=str) != before:
                changed = True
    if changed:
        save_db(db)
    return db


def save_db(db: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DB_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    tmp.replace(DB_PATH)


def request_json() -> Dict[str, Any]:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return {}


def requested_tenant_id() -> str:
    payload = request_json()
    return (
        request.headers.get("X-Tenant-ID")
        or request.headers.get("x-tenant-id")
        or request.args.get("tenant_id")
        or request.form.get("tenantId")
        or payload.get("tenantId")
        or "liberty-credit-specialists"
    )


def requested_user_id() -> str:
    payload = request_json()
    return request.headers.get("X-User-ID") or request.headers.get("x-user-id") or request.args.get("user_id") or request.form.get("userId") or payload.get("userId") or "system"


def get_tenant(db: Dict[str, Any]) -> Tuple[str, Dict[str, Any] | None]:
    tenant_id = requested_tenant_id()
    return tenant_id, db.get("tenants", {}).get(tenant_id)


def tenant_error(tenant_id: str):
    return jsonify({"success": False, "error": f"Unknown tenant_id '{tenant_id}'. Supply a valid X-Tenant-ID header."}), 404


def find_client(tenant: Dict[str, Any], client_id: str) -> Dict[str, Any] | None:
    for client in tenant.get("clients", []):
        if client.get("id") == client_id:
            return client
    return None

def current_user(tenant: Dict[str, Any]) -> Dict[str, Any] | None:
    user_id = requested_user_id()
    return next((u for u in tenant.get("users", []) if u.get("id") == user_id), None)


def require_role(tenant: Dict[str, Any], allowed_roles: List[str]):
    user = current_user(tenant)
    role = (user or {}).get("role", "")
    if role not in allowed_roles:
        return jsonify({"success": False, "error": "Role not allowed for this action", "requiredRoles": allowed_roles, "currentRole": role or "Unknown"}), 403
    return None


def public_tenant_summary(db: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for tenant in db.get("tenants", {}).values():
        results.append(
            {
                "id": tenant.get("id"),
                "name": tenant.get("name"),
                "ncr": tenant.get("ncr"),
                "userCount": len(tenant.get("users", [])),
                "clientCount": len(tenant.get("clients", [])),
            }
        )
    return results



def required_documents_for(service: str) -> List[str]:
    common = ["POPIA consent", "ID copy", "Proof of address", "Latest payslip", "3 months bank statements", "Credit report"]
    if service == "Debt Review Removal":
        return common + ["DR removal mandate", "NCT/court order if available", "Paid-up letters where applicable", "Clearance or termination evidence", "NuPay mandate"]
    if service == "Debt Review Sales Coach":
        return common + ["Form 16", "17.1 notice", "COB request authority", "Budget and affordability sheet", "NuPay mandate"]
    if service == "Debt Mediation":
        return common + ["Mediation mandate", "Creditor proposal authority", "Settlement/arrangement mandate", "NuPay mandate"]
    return common + ["Service mandate", "NuPay mandate"]


def default_workflow_state(client: Dict[str, Any]) -> Dict[str, Any]:
    coach = client.get("coach") or evaluate_sales(client, client.get("accounts", []))
    service = coach.get("service") or client.get("serviceType") or "Needs Manual Review"
    required = required_documents_for(service)
    existing_docs = {item.get("name"): item for item in client.get("documents", {}).get("items", []) if isinstance(item, dict)}
    doc_items = []
    for name in required:
        existing = existing_docs.get(name, {})
        doc_items.append({
            "name": name,
            "status": existing.get("status") or "Missing",
            "filename": existing.get("filename") or "",
            "uploadedAt": existing.get("uploadedAt") or "",
            "source": existing.get("source") or "",
            "notes": existing.get("notes") or "",
        })
    # Keep previously uploaded/manual documents even if the service route changes.
    for name, existing in existing_docs.items():
        if name not in required:
            extra = deepcopy(existing)
            extra.setdefault("status", "Uploaded")
            doc_items.append(extra)
    documents = {
        "required": required,
        "items": doc_items,
        "requestStatus": client.get("documents", {}).get("requestStatus", "Not Sent"),
        "sentAt": client.get("documents", {}).get("sentAt", ""),
        "uploadLink": client.get("documents", {}).get("uploadLink", ""),
    }
    signature = {
        "status": client.get("signature", {}).get("status", "Not Sent"),
        "link": client.get("signature", {}).get("link", ""),
        "sentAt": client.get("signature", {}).get("sentAt", ""),
        "signedAt": client.get("signature", {}).get("signedAt", ""),
    }
    nupay = {
        "status": client.get("nupayMandate", {}).get("status", "Not Sent"),
        "mandateId": client.get("nupayMandate", {}).get("mandateId", ""),
        "link": client.get("nupayMandate", {}).get("link", ""),
        "amount": client.get("nupayMandate", {}).get("amount", coach.get("totals", {}).get("reducedInstalment", 0)),
        "debitDay": client.get("nupayMandate", {}).get("debitDay", client.get("bank", {}).get("debitDay", "25")),
        "sentAt": client.get("nupayMandate", {}).get("sentAt", ""),
        "cancelledAt": client.get("nupayMandate", {}).get("cancelledAt", ""),
        "history": client.get("nupayMandate", {}).get("history", []),
    }
    admin = {
        "status": client.get("adminHandover", {}).get("status", "Not Submitted"),
        "submittedAt": client.get("adminHandover", {}).get("submittedAt", ""),
        "submittedBy": client.get("adminHandover", {}).get("submittedBy", ""),
        "notes": client.get("adminHandover", {}).get("notes", ""),
        "snapshot": client.get("adminHandover", {}).get("snapshot", {}),
    }
    pda = {
        "pdaName": client.get("pdaInfo", {}).get("pdaName", ""),
        "pdaReference": client.get("pdaInfo", {}).get("pdaReference", ""),
        "proposalAmount": client.get("pdaInfo", {}).get("proposalAmount", coach.get("totals", {}).get("reducedInstalment", 0)),
        "paymentStartDate": client.get("pdaInfo", {}).get("paymentStartDate", ""),
        "status": client.get("pdaInfo", {}).get("status", "Not Submitted"),
        "notes": client.get("pdaInfo", {}).get("notes", ""),
    }
    return {"documents": documents, "signature": signature, "nupayMandate": nupay, "adminHandover": admin, "pdaInfo": pda}


def ensure_client_workflow(client: Dict[str, Any]) -> Dict[str, Any]:
    client.setdefault("bank", default_bank())
    client.setdefault("accounts", [])
    client["coach"] = evaluate_sales(client, client.get("accounts", []))
    client["serviceType"] = client["coach"]["service"]
    workflow = default_workflow_state(client)
    client.update(workflow)
    return client


def normalize_client_payload(payload: Dict[str, Any], tenant_id: str, existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = deepcopy(existing) if existing else make_client(tenant_id, payload.get("fullName") or "New Client", requested_user_id())
    protected = {"id", "tenantId", "createdAt"}
    for key, value in payload.items():
        if key not in protected:
            base[key] = value
    # Keep name fields stable and rebuild full name when users capture first/second/surname separately.
    for key, value in default_applicant().items():
        base.setdefault(key, value)
    name_parts = [clean_spaces(str(base.get("firstName", ""))), clean_spaces(str(base.get("secondName", ""))), clean_spaces(str(base.get("surname", "")))]
    composed_name = clean_spaces(" ".join(part for part in name_parts if part))
    if composed_name and (not clean_spaces(str(base.get("fullName", ""))) or str(base.get("fullName", "")).lower() in {"new client", "new parsed client"}):
        base["fullName"] = composed_name
    base["tenantId"] = tenant_id
    base["updatedAt"] = now_iso()
    base.setdefault("spouse", default_applicant())
    if isinstance(base.get("spouse"), dict):
        for key, value in default_applicant().items():
            base["spouse"].setdefault(key, value)
    base.setdefault("bank", default_bank())
    base.setdefault("accounts", [])
    ensure_client_workflow(base)
    return base



def detect_bureau(text: str) -> str:
    low = (text or "").lower()
    for key, label in [
        ("datanamix", "Datanamix"),
        ("compuscan", "Compuscan"),
        ("experian", "Experian"),
        ("transunion", "TransUnion"),
        ("xds", "XDS"),
        ("xpert decision systems", "XDS"),
        ("presage score", "XDS"),
    ]:
        if key in low:
            return label
    return "Unknown"


def configure_tesseract_command() -> None:
    """Point pytesseract to common Windows install locations when available."""
    if pytesseract is None:
        return
    env_cmd = os.environ.get("TESSERACT_CMD")
    candidates = [
        env_cmd,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def ocr_pdf_text(path: Path, max_pages: int = 12) -> Tuple[str, List[str]]:
    """OCR fallback for scanned/image-only PDFs such as Datanamix exports."""
    warnings: List[str] = []
    if pytesseract is None or pdfium is None:
        warnings.append("OCR is not available. Install pytesseract, pypdfium2, Pillow and Tesseract OCR for scanned PDFs.")
        return "", warnings
    configure_tesseract_command()
    parts: List[str] = []
    try:
        pdf = pdfium.PdfDocument(str(path))
        page_count = min(len(pdf), max_pages)
        for index in range(page_count):
            page = pdf[index]
            bitmap = page.render(scale=1.6)
            image = bitmap.to_pil()
            text = pytesseract.image_to_string(image, config="--psm 6", timeout=20) or ""
            text = text.replace("\xa0", " ").strip()
            if text:
                parts.append(f"\n--- OCR PAGE {index + 1} ---\n{text}")
        if parts:
            warnings.append(f"Used OCR fallback because the PDF has no embedded text. OCR pages read: {len(parts)}.")
        else:
            warnings.append("OCR ran, but no text was detected in the scanned PDF.")
    except Exception as exc:
        warnings.append(f"OCR extraction failed: {exc}")
    return "\n".join(parts).strip(), warnings


def extract_pdf_text(path: Path) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    parts: List[str] = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                    if text.strip():
                        parts.append(text)
        except Exception as exc:
            warnings.append(f"pdfplumber extraction failed: {exc}")
    if not parts and PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
        except Exception as exc:
            warnings.append(f"PyPDF2 extraction failed: {exc}")
    text = "\n".join(parts).replace("\xa0", " ").strip()
    if not text:
        ocr_text, ocr_warnings = ocr_pdf_text(path)
        warnings.extend(ocr_warnings)
        text = ocr_text
    if not text:
        warnings.append("No extractable text found. The report may be scanned; install/configure OCR for scanned reports.")
    return text, warnings


def regex_first(patterns: List[str], text: str, flags: int = re.I | re.M) -> str:
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            groups = [g for g in match.groups() if g]
            if groups:
                return clean_spaces(" ".join(groups))
    return ""


def label_value(flat: str, label: str, stops: List[str]) -> str:
    """Read values from reports where labels and values are laid out across columns.
    Example XDS: First Name HOWARD Postal Address ... Surname BALOYI Residential Address ...
    """
    label_re = re.escape(label).replace(r"\ ", r"\s+").replace(r"\.", r"\.?")
    stop_re = "|".join(re.escape(s).replace(r"\ ", r"\s+").replace(r"\.", r"\.?") for s in stops)
    if not stop_re:
        stop_re = r"$^"
    m = re.search(rf"\b{label_re}\s*:?[\s-]*(.*?)(?=\s+\b(?:{stop_re})\b|$)", flat or "", re.I | re.S)
    if not m:
        return ""
    value = clean_spaces(m.group(1))
    # Strip common false captures where the field is blank and the next column label follows immediately.
    if value.lower() in {"telephone no", "telephone no. (h)", "telephone no. (w)", "postal address", "residential address", "e-mail address"}:
        return ""
    return value.strip(" :-")


def title_case_name(value: str) -> str:
    value = clean_spaces(value)
    if not value:
        return ""
    words = []
    for word in value.split():
        if word.isupper() or word.islower():
            words.append(word.capitalize())
        else:
            words.append(word)
    return " ".join(words)


def extract_score(text: str) -> int | None:
    flat = clean_spaces((text or "").replace("\xa0", " "))
    patterns = [
        r"Score\s+Date\s+Exception\s+Code\s+Risk\s+Category\s+Final\s+Score.*?\d{4}[-/]\d{2}[-/]\d{2}.*?\b(\d{1,4})\s*(?:Refer\s+to\s+Exception|Negative\s+Reasons|Description)",
        r"XDS\s+Presage\s+Score.*?\b\d{6,13}\s+\d{4}/\d{2}/\d{2}\s+(\d{1,4})\b",
        r"Unique\s+Identifier\s+Score\s+Date\s+Final\s+Score.*?\b\d{6,13}\s+\d{4}/\d{2}/\d{2}\s+(\d{1,4})\b",
        r"\bFinal\s+Score\s*[:\-]?\s*(\d{1,4})\b",
        r"\bCredit\s+Score\s*[:\-]?\s*(\d{1,4})\b",
        r"\bScore\s*[:\-]\s*(\d{1,4})\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, flat, re.I | re.S)
        if not m:
            continue
        try:
            val = int(m.group(1))
        except Exception:
            continue
        if 0 <= val <= 999:
            return val
    return None


def detect_debt_review_status(text: str) -> bool:
    flat = clean_spaces((text or "").replace("\xa0", " "))
    upper = flat.upper()
    negative_phrases = [
        "DEBT REVIEW STATUS NOTHING ON RECORD",
        "DEBT REVIEW STATUS - NOTHING ON RECORD",
        "DEBT REVIEW NOTHING ON RECORD",
        "NOTHING ON RECORD",
        "NO DEBT REVIEW",
        "NOT UNDER DEBT REVIEW",
    ]
    # If a DR section explicitly says nothing/no record, do not flag from section headings alone.
    section = re.search(r"Debt\s+Review\s+Status\s+(.*?)(?:Dispute\s+Information|Tuesday|Monday|Wednesday|Thursday|Friday|Page:|$)", flat, re.I | re.S)
    if section:
        value = clean_spaces(section.group(1))
        if re.search(r"nothing\s+on\s+record|no\s+record|not\s+under", value, re.I):
            return False
        if value and not re.fullmatch(r"[-0 ]+", value):
            return True
    if any(p in upper for p in negative_phrases):
        return False
    positive_phrases = [
        "DEBT REVIEW LISTED AGAINST CONSUMER",
        "CONSUMER IS UNDER DEBT REVIEW",
        "UNDER DEBT REVIEW",
        "UNDER DEBT COUNSELLING",
        "DEBT COUNSELLING FLAG",
        "FORM 17.2 ACCEPTED",
        "DEBT RESTRUCTURING ACTIVE",
    ]
    return any(p in upper for p in positive_phrases)



def extract_names_from_lines(text: str) -> Dict[str, str]:
    """Conservative name extraction fallback for bureau reports where labels wrap across lines."""
    result = {"firstName": "", "secondName": "", "surname": "", "fullName": ""}
    lines = [clean_spaces(line) for line in (text or "").replace("\xa0", " ").splitlines() if clean_spaces(line)]
    joined = " \n ".join(lines)
    patterns = [
        r"First\s+Name\s*[:\-]?\s*(?P<first>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,2}).{0,80}?Second\s+Name\s*[:\-]?\s*(?P<second>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,2}).{0,80}?Surname\s*[:\-]?\s*(?P<surname>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,3})",
        r"First\s+Names?\s*[:\-]?\s*(?P<first>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,4}).{0,80}?Surname\s*[:\-]?\s*(?P<surname>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,3})",
        r"Forename\(s\)\s*[:\-]?\s*(?P<first>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,4}).{0,80}?Surname\s*[:\-]?\s*(?P<surname>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,3})",
        r"Consumer\s+Name\s*[:\-]?\s*(?P<full>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){1,6})(?=\s+(?:ID|Identity|Date|Gender|Address|Telephone|Cell|Email|Enquiry|\n))",
        r"Client\s+Name\s*[:\-]?\s*(?P<full>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){1,6})(?=\s+(?:ID|Identity|Date|Gender|Address|Telephone|Cell|Email|\n))",
        r"Full\s+Names?\s*[:\-]?\s*(?P<full>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){1,6})(?=\s+(?:ID|Identity|Date|Gender|Address|Telephone|Cell|Email|\n))",
        r"Name\s*[:\-]?\s*(?P<full>[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){1,6})(?=\s+(?:ID|Identity|Date|Gender|Address|Telephone|Cell|Email|\n))",
    ]
    stop_words = {"ID", "IDENTITY", "NUMBER", "DATE", "BIRTH", "GENDER", "ADDRESS", "TELEPHONE", "TEL", "CELL", "EMAIL", "MARITAL", "STATUS", "REPORT", "CREDIT"}
    for pattern in patterns:
        m = re.search(pattern, joined, re.I | re.S)
        if not m:
            continue
        gd = {k: clean_spaces(v or "") for k, v in m.groupdict().items()}
        if gd.get("full"):
            parts = [p for p in gd["full"].split() if p.upper() not in stop_words]
            if len(parts) >= 2:
                result["fullName"] = " ".join(parts[:6])
                result["firstName"] = parts[0]
                if len(parts) > 2:
                    result["secondName"] = " ".join(parts[1:-1])
                result["surname"] = parts[-1]
                return result
        first = gd.get("first", "")
        second = gd.get("second", "")
        surname = gd.get("surname", "")
        if first or surname:
            result["firstName"] = first
            result["secondName"] = second
            result["surname"] = surname
            result["fullName"] = " ".join(p for p in [first, second, surname] if p)
            return result
    # Line-by-line fallback: separate labels on adjacent lines.
    label_values: Dict[str, str] = {}
    for i, line in enumerate(lines):
        low = line.lower().strip(" :")
        for label, key in [("first name", "firstName"), ("second name", "secondName"), ("surname", "surname"), ("full name", "fullName"), ("full names", "fullName"), ("consumer name", "fullName"), ("client name", "fullName")]:
            if low == label and i + 1 < len(lines):
                candidate = re.sub(r"[^A-Za-z'\- ]", " ", lines[i+1]).strip()
                if candidate and len(candidate.split()) <= 6:
                    label_values[key] = candidate
            elif low.startswith(label):
                candidate = clean_spaces(re.sub(rf"^{re.escape(label)}\s*[:\-]?", "", line, flags=re.I))
                candidate = re.sub(r"[^A-Za-z'\- ]", " ", candidate).strip()
                if candidate and len(candidate.split()) <= 6:
                    label_values[key] = candidate
    if label_values:
        result.update({k: v for k, v in label_values.items() if v})
        if result.get("fullName") and (not result.get("firstName") or not result.get("surname")):
            parts = result["fullName"].split()
            if len(parts) >= 2:
                result["firstName"] = result.get("firstName") or parts[0]
                result["surname"] = result.get("surname") or parts[-1]
                result["secondName"] = result.get("secondName") or " ".join(parts[1:-1])
        result["fullName"] = result.get("fullName") or " ".join(p for p in [result.get("firstName", ""), result.get("secondName", ""), result.get("surname", "")] if p)
    return result


def extract_datanamix_basic_details(text: str) -> Dict[str, Any]:
    """Datanamix image/OCR-safe client detail extraction."""
    flat = clean_spaces((text or "").replace("\xa0", " "))
    first_name = regex_first([r"\bFirst\s+Name\s*[:\-]?\s*([A-Za-z'\-]+)(?=\s+Residential\s+Address|\s+Surname|\s+Second\s+Name|\s+IDno|\s+ID\s+Number)"], flat, re.I | re.S)
    surname = regex_first([r"\bSurname\s*[:\-]?\s*([A-Za-z'\-]+)(?=\s+Home\s+Telephone|\s+IDno|\s+Birth\s+Date|\s+Debt\s+Review|\s+Maiden\s+Name)"], flat, re.I | re.S)
    # If the first page OCR missed the surname, use the Debt Review section on page 6.
    if not first_name or not surname:
        first2 = regex_first([r"Debt\s+Review.*?First\s+Name\s*[:\-]?\s*([A-Za-z'\-]+)"], flat, re.I | re.S)
        sur2 = regex_first([r"Debt\s+Review.*?Surname\s*[:\-]?\s*([A-Za-z'\-]+)"], flat, re.I | re.S)
        first_name = first_name or first2
        surname = surname or sur2
    id_number = regex_first([r"\bID\s*Number\s*[:\-]?\s*(\d{13})", r"\bIDno\s*[:\-]?\s*(\d{13})", r"\bClient\s+Reference\s*[:\-]?\s*(\d{13})"], flat, re.I | re.S)
    birth_date = regex_first([r"\bBirth\s+Date\s*[:\-]?\s*(\d{4}[-/]\d{2}[-/]\d{2})"], flat, re.I | re.S)
    gender = regex_first([r"\bGender\s*[:\-]?\s*(Male|Female|M|F)(?=\s+Email\s+Address|\s+Birth\s+Date|\s+Marital\s+Status|\s+Employer)"], flat, re.I | re.S)
    marital = regex_first([r"\bMarital\s+Status\s*[:\-]?\s*([A-Za-z]+)(?=\s+Fraud|\s+Consumer|\s+General\s+Disclaimer|\s+---|$)"], flat, re.I | re.S)
    phone = regex_first([r"\bCellular\s+No\s*[:\-]?\s*((?:\+27|0)\d{8,10})", r"\bCellular\s+(?:\d{4}[-/]\d{2}[-/]\d{2}\s+)?((?:\+27|0)\d{8,10})"], flat, re.I | re.S)
    address = regex_first([r"\bResidential\s+Address\s*[:\-]?\s*(.*?)(?=\s+Second\s+Name\s*:|\s+Postal\s+Address\s*:|\s+Surname\s*:|\s+Home\s+Telephone|$)"], flat, re.I | re.S)
    employer = regex_first([r"\bEmployer\s+Details\s*[:\-]?\s*(.*?)(?=\s+Marital\s+Status|\s+Fraud|\s+General\s+Disclaimer|$)", r"\bEmployer\s+Detail\s+Designation\s+\d{4}[-/]\d{2}[-/]\d{2}\s+(.*?)(?=\s+\d{4}[-/]\d{2}[-/]\d{2}|\s+General\s+Disclaimer|$)"], flat, re.I | re.S)
    score = extract_score(text)
    debt_counsellor_first = regex_first([r"Debt\s+Counsellor\s+First\s+Name\s*[:\-]?\s*([A-Za-z'\-]+)"], flat, re.I | re.S)
    debt_counsellor_surname = regex_first([r"Debt\s+Counsellor\s+Surname\s*[:\-]?\s*([A-Za-z'\-]+)"], flat, re.I | re.S)
    debt_counsellor_phone = regex_first([r"Debt\s+Counsellor\s+Telephone\s+No\s*[:\-]?\s*['‘’]?((?:\+27|0)\d{8,10})"], flat, re.I | re.S)
    debt_counsellor_ncr = regex_first([r"Debt\s+Counsellor\s+Registration\s+No\s*[:\-]?\s*([A-Z0-9\-]+)"], flat, re.I | re.S)
    debt_review_status_date = regex_first([r"Debt\s+Review\s+Status\s+Date\s*[:\-]?\s*(\d{4}[-/]\d{2}[-/]\d{2})"], flat, re.I | re.S)
    return {
        "firstName": title_case_name(first_name),
        "secondName": "",
        "surname": title_case_name(surname),
        "fullName": title_case_name(" ".join(p for p in [first_name, surname] if p)) or "New Parsed Client",
        "idNumber": id_number,
        "dateOfBirth": birth_date,
        "gender": title_case_name(gender),
        "maritalStatus": title_case_name(marital),
        "email": regex_first([r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"], flat, re.I),
        "phone": clean_spaces(phone),
        "whatsapp": clean_spaces(phone),
        "physicalAddress": clean_spaces(address),
        "employer": clean_spaces(employer),
        "occupation": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
        "creditScore": score,
        "scoreFound": score is not None,
        "debtReviewListed": detect_debt_review_status(text),
        "debtReviewStatusDate": debt_review_status_date,
        "debtCounsellorName": title_case_name(" ".join(p for p in [debt_counsellor_first, debt_counsellor_surname] if p)),
        "debtCounsellorPhone": clean_spaces(debt_counsellor_phone),
        "debtCounsellorNcr": debt_counsellor_ncr.upper(),
    }

def extract_basic_details(text: str) -> Dict[str, Any]:
    flat = clean_spaces((text or "").replace("\xa0", " "))
    if "datanamix" in flat.lower():
        return extract_datanamix_basic_details(text)
    # XDS and Datanamix often use label-value pairs arranged in two columns.
    first_name = label_value(flat, "First Name", ["Postal Address", "Second Name", "Surname", "ID No", "ID Number", "Residential Address", "Title"])
    second_name = label_value(flat, "Second Name", ["Telephone No", "Home Telephone No", "Postal Address", "Surname", "ID No", "ID Number", "First Name"])
    surname = label_value(flat, "Surname", ["Residential Address", "Home Telephone No", "Telephone No", "ID No", "ID Number", "Birth Date", "Date of Birth", "Gender"])

    if not first_name:
        first_name = regex_first([
            r"\bFirst\s+Name\s*[:\-]?\s*([A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,3})(?=\s+(?:Postal\s+Address|Second\s+Name|Surname|ID\s+No|ID\s+Number|Residential\s+Address)\b)",
        ], flat)
    if not surname:
        surname = regex_first([
            r"\bSurname\s*[:\-]?\s*([A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){0,3})(?=\s+(?:Residential\s+Address|Home\s+Telephone|Telephone\s+No|ID\s+No|ID\s+Number|Birth\s+Date|Date\s+of\s+Birth)\b)",
        ], flat)

    # Remove accidental labels or telephone text from blank second-name captures.
    for bad in ["Telephone No", "Telephone No. (H)", "Telephone No. (W)", "Postal Address", "Residential Address"]:
        if second_name.lower().startswith(bad.lower()):
            second_name = ""

    explicit_full_name = regex_first([
        r"(?:Consumer|Client|Applicant)\s*(?:Name|Full\s*Name)?\s*[:\-]\s*([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,5})",
        r"(?:Name|Full\s*Names?)\s*[:\-]\s*([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,5})",
    ], flat)
    full_name = " ".join(part for part in [first_name, second_name, surname] if part).strip() or explicit_full_name
    line_names = extract_names_from_lines(text)
    if not first_name and line_names.get("firstName"):
        first_name = line_names["firstName"]
    if not second_name and line_names.get("secondName"):
        second_name = line_names["secondName"]
    if not surname and line_names.get("surname"):
        surname = line_names["surname"]
    full_name = " ".join(part for part in [first_name, second_name, surname] if part).strip() or line_names.get("fullName") or explicit_full_name

    id_number = regex_first([
        r"\bID\s+No\.?\s*[:\-]?\s*(\d{13})\b",
        r"\bID\s+Number\s*[:\-]?\s*(\d{13})\b",
        r"\bIdentity\s+Number\s*[:\-]?\s*(\d{13})\b",
        r"\bEnquiry\s+Input\s+(\d{13})\b",
        r"\b(\d{13})\b",
    ], flat)
    email = regex_first([r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"], flat, re.I)
    phone = regex_first([
        r"\bCellular/Mobile\s*[:\-]?\s*((?:\+27|0)[0-9\s\-]{8,14})",
        r"\bCell(?:ular)?\s*[:\-]?\s*((?:\+27|0)[0-9\s\-]{8,14})",
        r"\bMobile\s*[:\-]?\s*((?:\+27|0)[0-9\s\-]{8,14})",
        r"\bTelephone\s+No\.\s*\(H\)\s*[:\-]?\s*((?:\+27|0)[0-9\s\-]{8,14})",
        r"\bTel\s*[:\-]?\s*((?:\+27|0)[0-9\s\-]{8,14})",
    ], flat)
    address = (
        label_value(flat, "Residential Address", ["ID No", "ID Number", "Reference No", "External Reference", "Passport", "Potential Fraud", "Postal Address"])
        or regex_first([r"(?:Residential|Physical|Current)\s*Address\s*[:\-]?\s*(.{10,160}?)(?=\s+(?:ID\s+No|Reference\s+No|Postal\s+Address|Potential\s+Fraud|$))"], flat)
    )
    employer = (
        label_value(flat, "Current Employer", ["Date of Birth", "E-mail Address", "Email", "Gender", "Cellular", "Telephone", "Title"])
        or label_value(flat, "Employer", ["Designation", "Occupation", "Date Employed", "Gender", "Address"])
        or regex_first([r"(?:Current\s+Employer|Employer|Company)\s*[:\-]?\s*([A-Za-z0-9 &.'\-]{2,90})"], flat)
    )
    birth_date = regex_first([
        r"\bDate\s+of\s+Birth\s*[:\-]?\s*(\d{4}/\d{2}/\d{2}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        r"\bBirth\s+Date\s*[:\-]?\s*(\d{4}/\d{2}/\d{2}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
    ], flat)
    gender = label_value(flat, "Gender", ["Cellular", "Marital Status", "Title", "Date of Birth"]) or regex_first([r"\bGender\s*[:\-]?\s*(Male|Female|M|F)\b"], flat)
    marital = label_value(flat, "Marital Status", ["Current Employer", "Date of Birth", "Gender", "Title"]) or regex_first([r"\bMarital\s+Status\s*[:\-]?\s*([A-Za-z]+)\b"], flat)

    score = extract_score(text)
    score_found = score is not None
    debt_review = detect_debt_review_status(text)
    return {
        "firstName": title_case_name(first_name),
        "secondName": title_case_name(second_name),
        "surname": title_case_name(surname),
        "fullName": title_case_name(full_name) or "New Parsed Client",
        "idNumber": id_number,
        "dateOfBirth": birth_date,
        "gender": title_case_name(gender),
        "maritalStatus": title_case_name(marital),
        "email": email,
        "phone": clean_spaces(phone),
        "whatsapp": clean_spaces(phone),
        "physicalAddress": clean_spaces(address),
        "employer": clean_spaces(employer),
        "occupation": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
        "creditScore": score,
        "scoreFound": score_found,
        "debtReviewListed": debt_review,
    }


def looks_like_money_token(raw: str, allow_plain_small: bool = False) -> bool:
    token = (raw or "").strip()
    if not token:
        return False
    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", token) or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", token):
        return False
    compact = re.sub(r"\D", "", token)
    if not compact:
        return False
    # Avoid treating ID/account/phone/date fragments as balances.
    if len(compact) >= 8 and not any(ch in token for ch in ",.") and not token.lower().startswith("r"):
        return False
    has_money_marker = token.lower().startswith("r") or "," in token or "." in token or " " in token
    if has_money_marker:
        return True
    value = money_to_float(token, 0)
    return allow_plain_small or abs(value) >= 100


def mask_non_money_numbers(line: str) -> str:
    masked = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", line)
    masked = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", " ", masked)
    masked = re.sub(r"\b\d{13}\b", " ", masked)
    masked = re.sub(r"\b(?:19|20)\d{2}\b", " ", masked)
    masked = re.sub(r"\b\d{8,20}\b", " ", masked)
    return masked


def parse_money_token(raw: str | None) -> float:
    text_value = clean_spaces(str(raw or ""))
    if not looks_like_money_token(text_value, allow_plain_small=True):
        return 0.0
    return money_to_float(text_value)


def parse_table_money_cell(raw: str | None) -> float:
    text_value = clean_spaces(str(raw or ""))
    if not text_value:
        return 0.0
    if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", text_value):
        return 0.0
    # Table columns are already identified as money columns, so plain numbers are acceptable.
    return money_to_float(text_value)


def find_money_values(line: str, allow_plain_small: bool = False) -> List[float]:
    values: List[float] = []
    masked = mask_non_money_numbers((line or "").replace("\xa0", " "))
    money_re = r"(?:R\s*)?-?\d{1,3}(?:[ ,]\d{3})+(?:\.\d{2})?|(?:R\s*)?-?\d+(?:\.\d{2})|(?:R\s*)?\d{1,7}\b"
    for raw in re.findall(money_re, masked, flags=re.I):
        raw = raw.strip()
        if not looks_like_money_token(raw, allow_plain_small=allow_plain_small):
            continue
        value = money_to_float(raw)
        if abs(value) >= 1:
            values.append(value)
    return values


BAD_ACCOUNT_PHRASES = [
    "total no", "total number", "no. of", "number of accounts", "accounts in good standing", "account summary",
    "payment profile", "payment history", "payment behaviour", "monthly payment behaviour", "profile history", "history of payment",
    "enquiry", "enquiries", "judgment", "judgement", "court", "admin order", "default listing", "adverse",
    "consumer details", "personal details", "employment details", "address details", "credit report", "credit score", "score card",
    "summary", "legend", "footer", "page ", "subscriber code", "months in arrears", "total balance", "total arrears",
    "total current", "balance summary", "total outstanding", "definitions indicators", "nothing on record",
    "registered with the national credit regulator", "contact information", "telephone", "residential address", "postal address",
]

WEAK_ACCOUNT_WORDS = {"account", "accounts", "credit", "creditor", "active", "current", "status", "opening", "balance", "arrears", "monthly", "total", "no", "of", "counts", "consumer", "date", "opened", "profile", "payment", "history", "instalment", "installment"}

KNOWN_CREDITOR_ALIASES: List[Tuple[str, str]] = [
    ("absa", "ABSA"), ("standard bank", "Standard Bank"), ("std bank", "Standard Bank"),
    ("fnb", "FNB"), ("first national bank", "FNB"), ("nedbank", "Nedbank"), ("capitec", "Capitec"),
    ("african bank", "African Bank"), ("wesbank", "WesBank"), ("mfc", "MFC Vehicle Finance"),
    ("old mutual", "Old Mutual Finance"), ("old mut", "Old Mutual Finance"), (" om ", "Old Mutual Finance"),
    ("truworths", "Truworths"), ("foschini", "TFG"), ("tfg", "TFG"), ("ackermans", "Ackermans"),
    ("mr price", "Mr Price Money"), ("mtn", "MTN"), ("vodacom", "Vodacom"), ("telkom", "Telkom"),
    ("russells", "Russells"), ("bradlows", "Bradlows"), ("lewis", "Lewis"), ("beares", "Beares"),
    ("ok furniture", "OK Furniture"), ("house & home", "House & Home"), ("homechoice", "HomeChoice"),
    ("makro", "Makro"), ("game", "Game"), ("rcs", "RCS"), ("sanlam", "Sanlam"),
    ("direct axis", "DirectAxis"), ("directaxis", "DirectAxis"), ("finchoice", "FinChoice"),
    ("loan", "Loan Account"), ("vehicle finance", "Vehicle Finance"), ("home loan", "Home Loan"),
]

ACCOUNT_TYPE_MAP = {
    "B": "Building Loan", "C": "Credit Card", "D": "Debt Recovery", "E": "Single Credit Facility",
    "F": "Open Services", "G": "Garage Card", "H": "Home Loan", "I": "Installment Account",
    "L": "Life Insurance", "M": "One Month Personal Loan", "P": "Personal Loan", "R": "Revolving Credit",
    "S": "Short Term Insurance", "T": "Student Loan", "U": "Utility", "V": "Overdraft",
    "W": "Rental Asset", "X": "Rental Property", "Y": "Vehicle Asset Finance", "Z": "Revolving Non-Store Card",
}


def is_bad_account_line(line: str) -> bool:
    low = f" {clean_spaces(line).lower()} "
    if not low.strip():
        return True
    if any(phrase in low for phrase in BAD_ACCOUNT_PHRASES):
        return True
    if re.match(r"^(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", low.strip()):
        return True
    if re.match(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", low.strip()):
        return True
    return False


def known_creditor_name(line: str) -> str:
    low = f" {line.lower()} "
    for needle, label in KNOWN_CREDITOR_ALIASES:
        if needle in low:
            return label
    return ""


def extract_account_number(line: str) -> str:
    found = regex_first([
        r"(?:Acc(?:ount)?\s*(?:No|Number)|Ref(?:erence)?|Account\s*(?:No|Number|ID))\s*[:#\-]?\s*([A-Z0-9*\-/ ]{4,28})",
        r"\b([0-9*]{6,20})\b",
    ], line)
    digits = re.sub(r"\D", "", found or "")
    if re.fullmatch(r"\d{13}", digits or ""):
        return ""
    return digits or clean_spaces(found)


def clean_creditor_candidate(text_value: str) -> str:
    candidate = mask_non_money_numbers(text_value)
    candidate = re.sub(r"(?:R\s*)?-?\d{1,3}(?:[ ,]\d{3})+(?:\.\d{2})?|(?:R\s*)?-?\d+(?:\.\d{2})|(?:R\s*)?\d{1,7}\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"\b(?:acc(?:ount)?|no|number|ref(?:erence)?|type|credit account|active|closed|current|arrears|default|paid up|balance|monthly|installment|instalment|date|opened|profile|payment|history)\b", " ", candidate, flags=re.I)
    candidate = re.sub(r"[^A-Za-z0-9&' .\-]", " ", candidate)
    candidate = clean_spaces(candidate).strip(" -:")
    words = [w for w in candidate.split() if w.lower() not in WEAK_ACCOUNT_WORDS]
    return " ".join(words[:7]).strip() or ""


def infer_creditor_from_line(line: str) -> str:
    known = known_creditor_name(line)
    if known:
        return known
    first_money = re.search(r"(?:R\s*)?-?\d{1,3}(?:[ ,]\d{3})+(?:\.\d{2})?|(?:R\s*)?-?\d+(?:\.\d{2})", mask_non_money_numbers(line), flags=re.I)
    candidate_source = line[: first_money.start()] if first_money else line
    return clean_creditor_candidate(candidate_source)



def has_formal_creditor_signal(name: str) -> bool:
    low = f" {clean_spaces(name).lower()} "
    if known_creditor_name(low):
        return True
    formal_words = [
        " bank", "finance", "financial", "loan", "credit", "card", "cash", "store", "stores", "retail",
        "furniture", "clothing", "insurance", "cellular", "telecom", "municipal", "medical", "pharmacy",
        "university", "college", "school", "hospital", "motors", "motor", "vehicle", "home loan", "bond",
        "capital", "group", "pty", "ltd", "inc", "services", "accounts", "collections",
    ]
    return any(word in low for word in formal_words)

def is_plausible_creditor(name: str, require_meaningful: bool = True) -> bool:
    low = clean_spaces(name).lower()
    if not low or low == "unknown creditor":
        return False
    if any(bad in low for bad in ["total", "count", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "months", "payment profile", "payment history", "summary", "description", "consumer", "telephone", "address"]):
        return False
    words = [w for w in re.split(r"\W+", low) if w]
    meaningful = [w for w in words if w not in WEAK_ACCOUNT_WORDS and len(w) > 1]
    if require_meaningful and not meaningful:
        return False
    return True


def suggest_reduced_amount(balance: float, installment: float) -> float:
    if balance <= 0 and installment <= 0:
        return 0
    suggested = max(100, balance * 0.015, installment * 0.65 if installment > 0 else 0)
    if installment > 0:
        suggested = min(suggested, installment)
    return round(suggested / 10) * 10


def account_type_from_text(text_value: str) -> str:
    low = text_value.lower()
    is_furniture = any(k in low for k in FURNITURE_KEYWORDS)
    is_asset = any(k in low for k in ASSET_KEYWORDS)
    if is_asset:
        return "Asset"
    if is_furniture:
        return "Furniture"
    if "home loan" in low or "mortgage" in low or "mortage" in low or "bond" in low:
        return "Home Loan"
    if "vehicle" in low or "wesbank" in low or "mfc" in low:
        return "Vehicle Finance"
    if "loan" in low:
        return "Loan"
    return "Credit Account"


def normalize_date(raw: str) -> str:
    raw = clean_spaces(raw)
    if not raw:
        return ""
    m = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})", raw)
    return (m.group(1) if m else "").replace("/", "-")


def build_account_from_fields(
    creditor: str,
    account_number: str,
    account_type: str,
    opening: float,
    current: float,
    monthly: float,
    arrears: float,
    status: str = "Active",
    open_date: str = "",
    last_paid: str = "",
    raw_line: str = "",
    parser_source: str = "parser",
) -> Dict[str, Any]:
    canonical_creditor = known_creditor_name(creditor)
    if canonical_creditor and parser_source != "datanamix-ocr":
        creditor = canonical_creditor
    creditor = clean_spaces(creditor)
    if not is_plausible_creditor(creditor):
        creditor = infer_creditor_from_line(raw_line)
    low = f"{creditor} {account_type} {raw_line}".lower()
    is_furniture = any(k in low for k in FURNITURE_KEYWORDS)
    is_asset = any(k in low for k in ASSET_KEYWORDS) or account_type in {"Home Loan", "Vehicle Asset Finance", "Vehicle Finance", "Asset"}
    account_type = account_type or account_type_from_text(low)
    monthly = float(monthly or 0)
    current = float(current or 0)
    opening = float(opening or 0)
    arrears = float(arrears or 0)
    return {
        "id": hashlib.md5(f"{creditor}-{account_number}-{opening}-{current}-{monthly}-{arrears}".encode()).hexdigest()[:10],
        "creditorName": creditor,
        "accountNumber": re.sub(r"\D", "", account_number or "") or clean_spaces(account_number),
        "accountType": account_type,
        "openingBalance": round(opening, 2),
        "currentBalance": round(current, 2),
        "arrears": round(arrears, 2),
        "monthlyInstallment": round(monthly, 2),
        "reducedAmount": round(suggest_reduced_amount(current, monthly), 2),
        "lastPaidDate": normalize_date(last_paid),
        "monthsInArrears": int(max(0, round(arrears / monthly))) if monthly > 0 and arrears > 0 else 0,
        "openDate": normalize_date(open_date),
        "status": clean_spaces(status or "Active"),
        "included": clean_spaces(status or "Active").lower() not in {"closed", "paid", "paid up"},
        "isFurniture": is_furniture,
        "isAsset": is_asset,
        "rawLine": raw_line[:600],
        "parserSource": parser_source,
    }


def build_account(creditor: str, line: str, values: List[float], account_number: str = "", extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # Generic fallback order is deliberately conservative and used only for known creditor lines.
    opening = values[0] if len(values) > 0 else 0
    current = values[1] if len(values) > 1 else opening
    arrears = values[2] if len(values) > 2 else 0
    monthly = values[3] if len(values) > 3 else 0
    account = build_account_from_fields(creditor, account_number, account_type_from_text(line), opening, current, monthly, arrears, "Active", "", regex_first([r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})"], line), line, "strict-line-fallback")
    if extra:
        account.update({k: v for k, v in extra.items() if v not in [None, ""]})
    return account


def normalise_header(value: str) -> str:
    return clean_spaces(re.sub(r"[^a-z0-9 ]", " ", (value or "").lower()))


def header_has_bad_context(headers: List[str]) -> bool:
    text_value = " ".join(headers).lower()
    return any(bad in text_value for bad in ["payment profile", "payment history", "monthly payment behaviour", "payment behaviour", "status history", "profile month", "profile status"])


def find_header_col(headers: List[str], positives: List[str], negatives: List[str] | None = None) -> int:
    negatives = negatives or []
    normalised = [normalise_header(h) for h in headers]
    best_idx = -1
    best_score = 0
    for idx, header in enumerate(normalised):
        if not header:
            continue
        if any(neg in header for neg in negatives):
            continue
        score = 0
        for pos in positives:
            pos_norm = normalise_header(pos)
            if header == pos_norm:
                score = max(score, 100 + len(pos_norm))
            elif pos_norm in header:
                score = max(score, 50 + len(pos_norm))
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx


def parse_accounts_from_tables(path: Path) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    if pdfplumber is None:
        return accounts
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table or len(table) < 2:
                        continue
                    header_index = -1
                    headers: List[str] = []
                    for i, row in enumerate(table[:10]):
                        row_cells = [clean_spaces(str(cell or "").replace("\n", " ")) for cell in row]
                        row_text = " ".join(row_cells).lower()
                        if any(bad in row_text for bad in ["payment profile", "payment history", "monthly payment behaviour", "profile month"]):
                            header_index = -1
                            headers = []
                            break
                        has_creditor_header = any(x in row_text for x in ["company", "creditor", "subscriber", "institution", "supplier"])
                        has_account_header = "account" in row_text or "ref" in row_text
                        has_money_header = any(x in row_text for x in ["current balance", "outstanding balance", "open balance", "opening balance", "instalment", "installment", "arrears", "overdue"])
                        if has_creditor_header and has_account_header and has_money_header:
                            header_index = i
                            headers = row_cells
                            break
                    if header_index < 0 or not headers or header_has_bad_context(headers):
                        continue

                    creditor_col = find_header_col(headers, ["company", "creditor", "subscriber", "institution", "supplier", "name"], ["consumer", "client", "applicant"])
                    acc_col = find_header_col(headers, ["account no", "acc no", "account number", "account", "reference", "ref"], ["type", "status", "date"])
                    type_col = find_header_col(headers, ["type of account", "account type", "type", "category"], ["date"])
                    opening_col = find_header_col(headers, ["opening balance", "open balance", "original balance", "credit limit", "opening"], ["date", "status"])
                    current_col = find_header_col(headers, ["current balance", "outstanding balance", "balance outstanding", "outstanding", "current bal"], ["status", "date", "current status"])
                    monthly_col = find_header_col(headers, ["monthly instalment", "monthly installment", "instalment amount", "installment amount", "instalment", "installment", "repayment"], ["date", "history"])
                    arrears_col = find_header_col(headers, ["arrears balance", "arrears amount", "amount in arrears", "past due", "overdue", "arrears"], ["months", "status"])
                    last_paid_col = find_header_col(headers, ["last paid date", "last payment date", "last paid", "last payment"], ["amount"])
                    open_date_col = find_header_col(headers, ["date account opened", "open date", "date opened", "opened date"], ["status"])
                    status_col = find_header_col(headers, ["current status", "account status", "status", "condition"], ["current balance"])
                    money_cols = [c for c in [opening_col, current_col, monthly_col, arrears_col] if c >= 0]
                    # Do not parse tables unless at least current balance and one additional money column are clearly identified.
                    if creditor_col < 0 or current_col < 0 or len(set(money_cols)) < 2:
                        continue

                    for row in table[header_index + 1:]:
                        cells = [clean_spaces(str(cell or "").replace("\n", " ")) for cell in row]
                        line = " ".join(cells)
                        if not clean_spaces(line) or is_bad_account_line(line):
                            continue
                        if len([x for x in cells if x]) < 3:
                            continue
                        creditor = cells[creditor_col] if 0 <= creditor_col < len(cells) else ""
                        known = known_creditor_name(line)
                        if known:
                            creditor = known
                        if not is_plausible_creditor(creditor):
                            continue
                        if not known_creditor_name(creditor) and not has_formal_creditor_signal(creditor):
                            # Unknown names without finance/store/service keywords are usually consumer/address/payment-profile fragments.
                            continue
                        opening = parse_table_money_cell(cells[opening_col]) if 0 <= opening_col < len(cells) else 0
                        current = parse_table_money_cell(cells[current_col]) if 0 <= current_col < len(cells) else 0
                        monthly = parse_table_money_cell(cells[monthly_col]) if 0 <= monthly_col < len(cells) else 0
                        arrears = parse_table_money_cell(cells[arrears_col]) if 0 <= arrears_col < len(cells) else 0
                        if current <= 0 and opening <= 0 and monthly <= 0:
                            continue
                        if current < 100 and opening < 100 and monthly < 100 and arrears < 100:
                            continue
                        account_number = cells[acc_col] if 0 <= acc_col < len(cells) else extract_account_number(line)
                        account_type = cells[type_col] if 0 <= type_col < len(cells) else account_type_from_text(line)
                        if len(account_type) == 1:
                            account_type = ACCOUNT_TYPE_MAP.get(account_type.upper(), account_type)
                        accounts.append(build_account_from_fields(
                            creditor=creditor,
                            account_number=account_number,
                            account_type=account_type,
                            opening=opening,
                            current=current,
                            monthly=monthly,
                            arrears=arrears,
                            status=cells[status_col] if 0 <= status_col < len(cells) else "Active",
                            open_date=cells[open_date_col] if 0 <= open_date_col < len(cells) else "",
                            last_paid=cells[last_paid_col] if 0 <= last_paid_col < len(cells) else "",
                            raw_line=line,
                            parser_source="strict-table",
                        ))
    except Exception:
        return accounts
    return dedupe_accounts(accounts)


def money_re_named(name: str) -> str:
    return rf"R\s*(?P<{name}>\d{{1,3}}(?:[ ]\d{{3}})*|\d+)(?:\.\d{{2}})?"


def parse_xds_accounts(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    m = re.search(r"Payment\s+Profile:\s+Credit\s+Account\s+Status(.*?)(?:Definitions\s+Indicators|Monthly\s+Payment\s+Behaviour|Payment\s+Profile:\s+National|Public\s+Domain\s+Records|$)", text or "", re.I | re.S)
    if not m:
        return accounts
    section = m.group(1).replace("\xa0", " ")
    section = re.sub(r"Last\s+Paid\s+Date.*?Company\s+Account\s+No\.?\s+Date\s+Account\s+Opened", " ", section, flags=re.I | re.S)
    flat = clean_spaces(section)
    date = r"\d{4}/\d{2}/\d{2}"
    status = r"Active|In\s+Arrears|Closed|Paid\s+Up|Paid|Current|Written\s+Off|Handed\s+Over"
    pattern_date_first = re.compile(
        rf"(?P<open_date>{date})\s+(?P<creditor>[A-Za-z][A-Za-z0-9&().'\- ]{{2,90}}?)\s+"
        rf"(?P<acc>\d[\d ]{{5,24}})\s+{money_re_named('opening')}\s+{money_re_named('current')}\s+{money_re_named('monthly')}\s+{money_re_named('arrears')}\s+"
        rf"(?P<type>[A-Z])\s+(?P<status>{status})\s+(?P<last>{date})",
        re.I,
    )
    spans: List[Tuple[int, int]] = []
    for match in pattern_date_first.finditer(flat):
        creditor = clean_spaces(match.group("creditor"))
        if is_bad_account_line(creditor):
            continue
        code = match.group("type").upper()
        accounts.append(build_account_from_fields(
            creditor=creditor,
            account_number=match.group("acc"),
            account_type=ACCOUNT_TYPE_MAP.get(code, code),
            opening=parse_money_token(match.group("opening")),
            current=parse_money_token(match.group("current")),
            monthly=parse_money_token(match.group("monthly")),
            arrears=parse_money_token(match.group("arrears")),
            status=match.group("status"),
            open_date=match.group("open_date"),
            last_paid=match.group("last"),
            raw_line=match.group(0),
            parser_source="xds-credit-status",
        ))
        spans.append(match.span())

    pattern_money_first = re.compile(
        rf"{money_re_named('opening')}\s+{money_re_named('current')}\s+{money_re_named('monthly')}\s+{money_re_named('arrears')}\s+"
        rf"(?P<type>[A-Z])\s+(?P<status>{status})\s+(?P<last>{date})\s+"
        rf"(?P<acc>\d[\d ]{{5,24}})\s+"
        rf"(?:(?P<creditor1>[A-Za-z][A-Za-z0-9&().'\- ]{{2,90}}?)\s+(?P<open_date1>{date})|(?P<open_date2>{date})\s+(?P<creditor2>[A-Za-z][A-Za-z0-9&().'\- ]{{2,90}}?))"
        rf"(?=\s+(?:R\s*\d|{date}\s+[A-Za-z]|B\s+B\s+-|C\s+C\s+-|$))",
        re.I,
    )
    for match in pattern_money_first.finditer(flat):
        if any(match.start() >= s and match.end() <= e for s, e in spans):
            continue
        creditor = clean_spaces(match.group("creditor1") or match.group("creditor2") or "")
        open_date = match.group("open_date1") or match.group("open_date2") or ""
        if is_bad_account_line(creditor):
            continue
        code = match.group("type").upper()
        accounts.append(build_account_from_fields(
            creditor=creditor,
            account_number=match.group("acc"),
            account_type=ACCOUNT_TYPE_MAP.get(code, code),
            opening=parse_money_token(match.group("opening")),
            current=parse_money_token(match.group("current")),
            monthly=parse_money_token(match.group("monthly")),
            arrears=parse_money_token(match.group("arrears")),
            status=match.group("status"),
            open_date=open_date,
            last_paid=match.group("last"),
            raw_line=match.group(0),
            parser_source="xds-credit-status",
        ))
    return dedupe_accounts(accounts)


def parse_supplier_style_accounts(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    flat = clean_spaces((text or "").replace("\xa0", " "))
    pattern = re.compile(
        r"SUPPLIER\s+(?P<creditor>.*?)\s+ACCOUNT\s+TYPE\s+(?P<type>.*?)\s+ACCOUNT\s+NO\.?\s+(?P<acc>.*?)\s+"
        r"(?:OVERDUE|ARREARS)\s+AMOUNT\s+R\s*(?P<arrears>[\d ,]+(?:\.\d{2})?).*?"
        r"OPEN\s+BALANCE\s+R\s*(?P<opening>[\d ,]+(?:\.\d{2})?).*?"
        r"CURRENT\s+BALANCE\s+R\s*(?P<current>[\d ,]+(?:\.\d{2})?).*?"
        r"MONTHLY\s+INSTAL(?:L)?MENT\s+R\s*(?P<monthly>[\d ,]+(?:\.\d{2})?)"
        r"(?:.*?(?:LAST\s+PAYMENT\s+DATE|LAST\s+PAID\s+DATE|DATE\s+OF\s+LAST\s+PAYMENT)\s*[:\-]?\s*(?P<last>\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}))?",
        re.I | re.S,
    )
    for m in pattern.finditer(flat):
        accounts.append(build_account_from_fields(
            creditor=m.group("creditor"),
            account_number=m.group("acc"),
            account_type=m.group("type") or account_type_from_text(m.group(0)),
            opening=parse_money_token(m.group("opening")),
            current=parse_money_token(m.group("current")),
            monthly=parse_money_token(m.group("monthly")),
            arrears=parse_money_token(m.group("arrears")),
            status="Active",
            last_paid=m.group("last") or "",
            raw_line=m.group(0),
            parser_source="supplier-style",
        ))
    return dedupe_accounts(accounts)


def remove_consumer_name_accounts(accounts: List[Dict[str, Any]], basic: Dict[str, Any]) -> List[Dict[str, Any]]:
    name_bits = [clean_spaces(str(basic.get(k, ""))).lower() for k in ["firstName", "secondName", "surname", "fullName"] if clean_spaces(str(basic.get(k, "")))]
    result: List[Dict[str, Any]] = []
    for account in accounts:
        creditor = clean_spaces(account.get("creditorName", "")).lower()
        if creditor and any(bit and creditor == bit for bit in name_bits):
            continue
        result.append(account)
    return result


def dedupe_accounts(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for account in accounts:
        creditor = clean_spaces(account.get("creditorName", ""))
        if not is_plausible_creditor(creditor):
            continue
        if is_bad_account_line(creditor):
            continue
        current = round(money_to_float(account.get("currentBalance")), 2)
        monthly = round(money_to_float(account.get("monthlyInstallment")), 2)
        opening = round(money_to_float(account.get("openingBalance")), 2)
        arrears = round(money_to_float(account.get("arrears")), 2)
        source = str(account.get("parserSource", ""))
        if max(abs(opening), abs(current), abs(monthly), abs(arrears)) <= 0 and source != "datanamix-ocr":
            continue
        # Low-value rows with no known creditor are usually payment-history fragments. Datanamix account blocks are label-based, so they are safe.
        if source != "datanamix-ocr" and not known_creditor_name(creditor) and max(abs(opening), abs(current), abs(monthly), abs(arrears)) < 100:
            continue
        key = (creditor.lower(), str(account.get("accountNumber", ""))[-10:], current, monthly, arrears)
        if key in seen:
            continue
        seen.add(key)
        account["creditorName"] = creditor
        deduped.append(account)
    return deduped



def datanamix_money(raw: str) -> float:
    value = clean_spaces(raw or "")
    # OCR commonly reads R0 as RO.
    value = re.sub(r"\bR\s*[Oo]\b", "R0", value, flags=re.I)
    value = re.sub(r"\b[Oo]\b", "0", value)
    return money_to_float(value, 0.0)


def datanamix_label_value(block: str, label: str, stops: List[str]) -> str:
    label_re = re.escape(label).replace(r"\ ", r"\s+").replace(r"\/", r"\s*/\s*")
    stop_re = "|".join(re.escape(s).replace(r"\ ", r"\s+").replace(r"\/", r"\s*/\s*") for s in stops)
    if not stop_re:
        stop_re = r"$^"
    m = re.search(rf"\b{label_re}\s*:?\s*(.*?)(?=\s+(?:{stop_re})\s*:|$)", block or "", re.I | re.S)
    if not m:
        return ""
    return clean_spaces(m.group(1)).strip(" :-|")


def clean_datanamix_creditor(name: str, continuation: str = "") -> str:
    text_value = clean_spaces(f"{name} {continuation}".replace("|", " ").replace("‘", " ").replace("’", " ").replace(chr(34), " "))
    text_value = re.sub(r"\bDMCc(?=\d)", "DMC", text_value, flags=re.I)
    text_value = re.sub(r"\b(?:Current\s+Balance|Instalment\s+Amount|Arrears\s+Amount|Open\s+Balance|Credit\s+Limit|No\s+Of\s+Participants|Type\s+of\s+Account|Last\s+Paid\s+Date|Date\s+Account\s+Opened|Account\s+Status)\b.*", "", text_value, flags=re.I)
    text_value = re.sub(r"\bAccount\s+No\b.*", "", text_value, flags=re.I)
    text_value = re.sub(r"[^A-Za-z0-9&'()./\- ]", " ", text_value)
    text_value = clean_spaces(text_value).strip(" -:.")
    return text_value


def parse_datanamix_accounts(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    if not text or "datanamix" not in text.lower():
        return accounts
    flat = clean_spaces(text.replace("\xa0", " "))
    # Only use the account-status section; this avoids enquiry/history/payment grids.
    section = regex_first([
        r"Consumer\s+Account\s+Status\s+(.*?)(?:Consumer\s+24\s+Monthly\s+Payment\s+History|Definition\s+Code\s+Descriptions|Consumer\s+NLR\s+Account\s+Status|Debt\s+Review\s+Case|Directorships|Defaults|Debt\s+Review|Adverse\s+Information|Consumer\s+Address\s+History|Enquiry\s+History|General\s+Disclaimer|$)"
    ], flat, re.I | re.S) or flat
    # Stop before payment-history grids if OCR did not preserve the heading exactly.
    section = re.split(r"Definition\s+Code\s+Descriptions|Consumer\s+24\s+Monthly\s+Payment\s+History|SEP\s+2025\s+AUG\s+2025", section, maxsplit=1, flags=re.I)[0]
    pieces = re.split(r"\bSubscriber\s+Name\s*:\s*", section, flags=re.I)
    for raw_block in pieces[1:]:
        block = clean_spaces(raw_block)
        block = re.split(r"\bSubscriber\s+Name\s*:|Definition\s+Code\s+Descriptions|General\s+Disclaimer", block, maxsplit=1, flags=re.I)[0]
        m = re.search(r"^(?P<creditor>.*?)(?:[\s\'‘’\"]+Account\s+No\s*:\s*(?P<acc>[0-9 ]{4,24})(?P<after>.*))$", block, re.I | re.S)
        if not m:
            continue
        creditor = clean_datanamix_creditor(m.group("creditor"))
        after = clean_spaces(m.group("after") or "")
        continuation = ""
        cont_m = re.match(r"[,\s'‘’\"-]*(?P<cont>[A-Za-z][A-Za-z0-9&'()./\- ]{1,60}?)\s+Current\s+Balance\b", after, re.I)
        if cont_m:
            continuation = cont_m.group("cont")
        creditor = clean_datanamix_creditor(creditor, continuation)
        if not is_plausible_creditor(creditor, require_meaningful=True):
            continue
        current = datanamix_money(datanamix_label_value(block, "Current Balance", ["Instalment Amount", "Arrears Amount", "Open Balance / Credit Limit"]))
        monthly = datanamix_money(datanamix_label_value(block, "Instalment Amount", ["Arrears Amount", "Open Balance / Credit Limit", "No Of Participants In Joint Loan"]))
        arrears = datanamix_money(datanamix_label_value(block, "Arrears Amount", ["Open Balance / Credit Limit", "No Of Participants In Joint Loan", "Type of Account"]))
        opening = datanamix_money(datanamix_label_value(block, "Open Balance / Credit Limit", ["No Of Participants In Joint Loan", "Type of Account", "Last Paid Date"]))
        acc_type = datanamix_label_value(block, "Type of Account", ["Last Paid Date", "Date Account Opened", "Account Status"]) or account_type_from_text(creditor)
        last_paid = datanamix_label_value(block, "Last Paid Date", ["Date Account Opened", "Account Status"])
        open_date = datanamix_label_value(block, "Date Account Opened", ["Account Status", "Subscriber Name"])
        status = datanamix_label_value(block, "Account Status", ["Subscriber Name", "Definition Code Descriptions", "General Disclaimer"]) or "Active"
        accounts.append(build_account_from_fields(
            creditor=creditor,
            account_number=m.group("acc") or "",
            account_type=acc_type,
            opening=opening,
            current=current,
            monthly=monthly,
            arrears=arrears,
            status=status,
            open_date=open_date,
            last_paid=last_paid,
            raw_line=block,
            parser_source="datanamix-ocr",
        ))
    return dedupe_accounts(accounts)


def parse_generic_lines(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    for line in [clean_spaces(x) for x in (text or "").splitlines() if clean_spaces(x)]:
        if is_bad_account_line(line):
            continue
        known = known_creditor_name(line)
        # The generic line fallback caused most of the bad rows. Use it only for known creditor names.
        if not known:
            continue
        values = find_money_values(line, allow_plain_small=False)
        if len(values) < 3:
            continue
        account_number = extract_account_number(line)
        accounts.append(build_account(known, line, values, account_number))
    return dedupe_accounts(accounts)


def parse_accounts(text: str, bureau: str = "Unknown") -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    bureau_lower = bureau.lower()
    if bureau_lower == "datanamix":
        datanamix_accounts = parse_datanamix_accounts(text)
        if datanamix_accounts:
            return dedupe_accounts(datanamix_accounts)[:80]
    if bureau_lower == "xds":
        accounts.extend(parse_xds_accounts(text))
    accounts.extend(parse_supplier_style_accounts(text))
    if len(accounts) < 1:
        accounts.extend(parse_generic_lines(text))
    return dedupe_accounts(accounts)[:80]


def match_creditor(name: str) -> Dict[str, Any]:
    low = (name or "").lower()
    for key, data in CREDITOR_DIRECTORY.items():
        if key in low or low in key:
            return {**data, "matched": True, "needsReview": False}
    return {"name": name or "Unknown Creditor", "department": "Debt Review Department", "email": "", "phone": "", "matched": False, "needsReview": True}


def parse_credit_report(path: Path, original_filename: str) -> Dict[str, Any]:
    text, warnings = extract_pdf_text(path)
    bureau = detect_bureau(text or original_filename)
    basic = extract_basic_details(text) if text else {"fullName": "New Parsed Client", "creditScore": None, "scoreFound": False, "debtReviewListed": False}
    used_ocr = any("OCR fallback" in w or "OCR pages read" in w for w in warnings)
    # Scanned Datanamix reports are image-based; pdf table extraction is slow and unreliable there.
    table_accounts = [] if used_ocr or bureau.lower() == "datanamix" else parse_accounts_from_tables(path)
    text_accounts = parse_accounts(text, bureau) if text else []
    # For XDS, the text parser is safer than pdfplumber's table extraction because XDS tables often wrap columns.
    if bureau.lower() == "xds" and text_accounts:
        accounts = dedupe_accounts(text_accounts)[:80]
        if table_accounts:
            warnings.append("Ignored pdf table rows because the XDS text parser found safer account rows.")
    else:
        accounts = dedupe_accounts(table_accounts + text_accounts)[:80]
    accounts = remove_consumer_name_accounts(accounts, basic)
    if text and table_accounts:
        warnings.append(f"Strict table parser found {len(table_accounts)} account row(s).")
    if text and text_accounts:
        warnings.append(f"Strict text parser found {len(text_accounts)} account row(s).")
    if text and not basic.get("firstName") and not basic.get("surname"):
        warnings.append("Client first name/surname were not confidently detected. Check report quality or capture manually.")
    if text and not accounts:
        warnings.append("No account rows were confidently detected. Capture or verify accounts manually, or upload a clearer text-based PDF.")
    if accounts:
        warnings.append("Parser is now strict: verify balances against the PDF, and add any missing creditors manually before sending a proposal.")
    else:
        warnings.append("The parser rejected weak rows instead of importing possible payment-history fragments. Add creditor rows manually or upload a clearer text-based report.")
    coach = evaluate_sales(basic, accounts)
    return {
        "success": True,
        "uploadedAt": now_iso(),
        "filename": original_filename,
        "bureau": bureau,
        "confidence": 90 if accounts and basic.get("idNumber") and (basic.get("firstName") or basic.get("surname")) else 65 if accounts else 45,
        "warnings": warnings,
        "client": basic,
        "accounts": accounts,
        "coach": coach,
        "creditorMatches": [match_creditor(a.get("creditorName", "")) for a in accounts],
        "parserDebug": {
            "firstName": basic.get("firstName"),
            "secondName": basic.get("secondName"),
            "surname": basic.get("surname"),
            "fullName": basic.get("fullName"),
            "idNumber": basic.get("idNumber"),
            "accountCount": len(accounts),
        },
    }


@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"success": True, "app": APP_NAME, "version": APP_VERSION, "isolation": "X-Tenant-ID scoped"})


@app.get("/health")
@app.get("/api/health")
def health():
    db = load_db()
    return jsonify({"success": True, "status": "ok", "version": APP_VERSION, "tenants": len(db.get("tenants", {}))})


@app.route("/api/tenants", methods=["GET", "POST"])
def tenants():
    db = load_db()
    if request.method == "GET":
        return jsonify({"success": True, "tenants": public_tenant_summary(db)})

    payload = request_json()
    name = clean_spaces(payload.get("name") or payload.get("companyName") or "")
    ncr = clean_spaces(payload.get("ncr") or payload.get("ncrNumber") or "")
    admin_name = clean_spaces(payload.get("adminName") or "Tenant Admin")
    admin_email = clean_spaces(payload.get("adminEmail") or payload.get("email") or "")
    if not name:
        return jsonify({"success": False, "error": "Tenant name is required"}), 400

    base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tenant"
    tenant_id = base_slug
    counter = 2
    while tenant_id in db.setdefault("tenants", {}):
        tenant_id = f"{base_slug}-{counter}"
        counter += 1

    admin_user = {
        "id": f"{tenant_id}-admin",
        "name": admin_name,
        "role": "Admin",
        "email": admin_email,
    }
    db["tenants"][tenant_id] = {
        "id": tenant_id,
        "name": name,
        "ncr": ncr,
        "users": [admin_user],
        "clients": [],
        "uploads": [],
        "createdAt": now_iso(),
    }
    save_db(db)
    return jsonify({
        "success": True,
        "tenant": {
            "id": tenant_id,
            "name": name,
            "ncr": ncr,
            "userCount": 1,
            "clientCount": 0,
        },
        "user": admin_user,
        "tenants": public_tenant_summary(db),
    }), 201


@app.get("/api/users")
def users():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    return jsonify({"success": True, "tenantId": tenant_id, "users": tenant.get("users", [])})


@app.post("/api/auth/login")
def auth_login():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    user_id = requested_user_id()
    user = next((u for u in tenant.get("users", []) if u.get("id") == user_id), None)
    if not user:
        return jsonify({"success": False, "error": "User not found inside this tenant", "tenantId": tenant_id}), 404
    return jsonify({"success": True, "tenant": {"id": tenant_id, "name": tenant.get("name"), "ncr": tenant.get("ncr")}, "user": user, "session": {"tenantId": tenant_id, "userId": user_id, "role": user.get("role")}})


@app.get("/api/me")
def me():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    user_id = requested_user_id()
    user = next((u for u in tenant.get("users", []) if u.get("id") == user_id), tenant.get("users", [{}])[0])
    return jsonify({"success": True, "tenant": {"id": tenant_id, "name": tenant.get("name"), "ncr": tenant.get("ncr")}, "user": user})


@app.get("/api/clients")
def list_clients():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    q = clean_spaces(request.args.get("q") or request.args.get("search") or "").lower()
    service = clean_spaces(request.args.get("service") or "")
    status = clean_spaces(request.args.get("status") or "")
    clients = []
    for client in tenant.get("clients", []):
        haystack = " ".join(str(client.get(key, "")) for key in ["fullName", "idNumber", "phone", "email", "status", "serviceType"]).lower()
        if q and q not in haystack:
            continue
        if service and client.get("serviceType") != service:
            continue
        if status and client.get("status") != status:
            continue
        clients.append(client)
    clients.sort(key=lambda c: c.get("updatedAt", ""), reverse=True)
    return jsonify({"success": True, "tenantId": tenant_id, "count": len(clients), "clients": clients})


@app.post("/api/clients")
def create_client_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = normalize_client_payload(request_json(), tenant_id)
    tenant.setdefault("clients", []).append(client)
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "clients": tenant.get("clients", [])}), 201


@app.get("/api/clients/<client_id>")
def read_client_route(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    return jsonify({"success": True, "tenantId": tenant_id, "client": client})


@app.put("/api/clients/<client_id>")
@app.patch("/api/clients/<client_id>")
def update_client_route(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    existing = find_client(tenant, client_id)
    if not existing:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    updated = normalize_client_payload(request_json(), tenant_id, existing)
    clients = tenant.get("clients", [])
    for i, client in enumerate(clients):
        if client.get("id") == client_id:
            clients[i] = updated
            break
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": updated, "clients": clients})


@app.delete("/api/clients/<client_id>")
def delete_client_route(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    before = len(tenant.get("clients", []))
    tenant["clients"] = [c for c in tenant.get("clients", []) if c.get("id") != client_id]
    if len(tenant["clients"]) == before:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "deletedClientId": client_id, "clients": tenant.get("clients", [])})


def handle_upload(client_id: str | None = None):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    file = request.files.get("file") or request.files.get("creditReport") or request.files.get("pdf")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No PDF file uploaded. Use form field 'file'."}), 400
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename)
    tenant_upload_dir = UPLOAD_DIR / tenant_id
    tenant_upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = tenant_upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_name}"
    file.save(saved_path)

    result = parse_credit_report(saved_path, file.filename)
    payload_client = result.get("client", {})
    accounts = result.get("accounts", [])
    user_id = requested_user_id()

    existing = find_client(tenant, client_id) if client_id else None
    if existing:
        existing.update(payload_client)
        existing["accounts"] = accounts
        existing["coach"] = evaluate_sales(existing, accounts)
        existing["serviceType"] = existing["coach"]["service"]
        existing["status"] = "Credit Report Uploaded"
        ensure_client_workflow(existing)
        existing["updatedAt"] = now_iso()
        client = existing
    else:
        client = make_client(tenant_id, payload_client.get("fullName") or "New Parsed Client", user_id)
        client.update(payload_client)
        client["accounts"] = accounts
        client["coach"] = evaluate_sales(client, accounts)
        client["serviceType"] = client["coach"]["service"]
        client["status"] = "Credit Report Uploaded"
        ensure_client_workflow(client)
        tenant.setdefault("clients", []).append(client)

    upload_record = {"id": new_id("upload"), "clientId": client["id"], "filename": file.filename, "storedPath": str(saved_path), "uploadedAt": now_iso(), "userId": user_id}
    tenant.setdefault("uploads", []).append(upload_record)
    save_db(db)
    result.update({"tenantId": tenant_id, "clientId": client["id"], "client": client, "accounts": client.get("accounts", []), "coach": client.get("coach"), "clients": tenant.get("clients", [])})
    return jsonify(result)


@app.post("/upload")
@app.post("/api/upload")
@app.post("/api/upload/credit-report")
def upload_route():
    # Safety rule: the generic upload endpoint always creates a NEW client.
    # To replace/update an existing client report, use /api/clients/<client_id>/credit-report/upload.
    return handle_upload(None)


@app.post("/api/clients/<client_id>/credit-report")
@app.post("/api/clients/<client_id>/upload-credit-report")
@app.post("/api/clients/<client_id>/credit-report/upload")
@app.post("/api/clients/<client_id>/documents/credit-report")
def client_upload_route(client_id: str):
    return handle_upload(client_id)


@app.get("/api/creditors/match")
def creditor_match_route():
    return jsonify({"success": True, "contact": match_creditor(request.args.get("name", ""))})


@app.post("/api/portal/links")
def portal_links_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    payload = request_json()
    client_id = payload.get("clientId") or payload.get("client_id")
    client = find_client(tenant, client_id or "")
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    base_url = (payload.get("baseUrl") or request.host_url.rstrip("/") + "/portal").rstrip("/")
    token_seed = f"{tenant_id}:{client_id}:{secrets.token_hex(8)}"
    token = hashlib.sha256(token_seed.encode()).hexdigest()[:24]
    links = {
        "signatureLink": f"{base_url}/{tenant_id}/signature/{client_id}/{token}",
        "uploadLink": f"{base_url}/{tenant_id}/upload/{client_id}/{token}",
        "createdAt": now_iso(),
    }
    client["portalLinks"] = links
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "clientId": client_id, **links})



def create_secure_link(kind: str, tenant_id: str, client_id: str, base_url: str) -> str:
    token_seed = f"{kind}:{tenant_id}:{client_id}:{secrets.token_hex(12)}"
    token = hashlib.sha256(token_seed.encode()).hexdigest()[:28]
    return f"{base_url.rstrip('/')}/{tenant_id}/{kind}/{client_id}/{token}"


def admin_snapshot(client: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
    coach = client.get("coach") or evaluate_sales(client, client.get("accounts", []))
    return {
        "tenantId": tenant_id,
        "submittedBy": user_id,
        "clientId": client.get("id"),
        "clientName": client.get("fullName"),
        "serviceType": coach.get("service"),
        "status": client.get("status"),
        "fees": {
            "drrFee": 7000 if coach.get("service") == "Debt Review Removal" else 0,
            "nupayAmount": client.get("nupayMandate", {}).get("amount", 0),
            "reducedInstalment": coach.get("totals", {}).get("reducedInstalment", 0),
            "originalInstalment": coach.get("totals", {}).get("originalInstalment", 0),
            "estimatedRelief": coach.get("totals", {}).get("estimatedRelief", 0),
        },
        "creditorsIncluded": [a for a in client.get("accounts", []) if a.get("included", True)],
        "documents": client.get("documents", {}),
        "signature": client.get("signature", {}),
        "nupayMandate": client.get("nupayMandate", {}),
        "pdaInfo": client.get("pdaInfo", {}),
        "createdAt": now_iso(),
    }


@app.post("/api/clients/<client_id>/documents/request")
def request_client_documents(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    payload = request_json()
    base_url = (payload.get("baseUrl") or request.host_url.rstrip("/") + "/portal").rstrip("/")
    client["documents"]["requestStatus"] = "Sent"
    client["documents"]["sentAt"] = now_iso()
    client["documents"]["uploadLink"] = create_secure_link("documents", tenant_id, client_id, base_url)
    for item in client["documents"].get("items", []):
        if item.get("status") == "Missing":
            item["status"] = "Requested"
    client["status"] = "Docs Requested"
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "uploadLink": client["documents"]["uploadLink"], "documents": client["documents"]})


@app.post("/api/clients/<client_id>/documents/upload")
def upload_client_document(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    doc_name = request.form.get("docName") or request.args.get("docName") or "Client document"
    file = request.files.get("file") or request.files.get("document")
    filename = request.form.get("filename") or (file.filename if file else f"{doc_name}.pdf")
    stored_path = ""
    if file and file.filename:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename)
        doc_dir = UPLOAD_DIR / tenant_id / "client_docs" / client_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        stored = doc_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_name}"
        file.save(stored)
        stored_path = str(stored)
    matched = False
    for item in client["documents"].get("items", []):
        if item.get("name") == doc_name:
            item.update({"status": "Uploaded", "filename": filename, "uploadedAt": now_iso(), "source": "portal", "storedPath": stored_path})
            matched = True
            break
    if not matched:
        client["documents"].setdefault("items", []).append({"name": doc_name, "status": "Uploaded", "filename": filename, "uploadedAt": now_iso(), "source": "portal", "storedPath": stored_path, "notes": ""})
    if all(item.get("status") == "Uploaded" for item in client["documents"].get("items", [])):
        client["status"] = "Docs Received"
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "documents": client["documents"]})


@app.post("/api/clients/<client_id>/signature/send")
def send_signature_link(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    payload = request_json()
    base_url = (payload.get("baseUrl") or request.host_url.rstrip("/") + "/portal").rstrip("/")
    client["signature"].update({"status": "Sent", "link": create_secure_link("signature", tenant_id, client_id, base_url), "sentAt": now_iso()})
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "signature": client["signature"]})


@app.post("/api/clients/<client_id>/signature/mark-signed")
def mark_signature_signed(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    client["signature"].update({"status": "Signed", "signedAt": now_iso()})
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "signature": client["signature"]})


@app.post("/api/clients/<client_id>/mandate/send")
def send_nupay_mandate(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    payload = request_json()
    coach = client.get("coach") or evaluate_sales(client, client.get("accounts", []))
    amount = money_to_float(payload.get("amount"), money_to_float(client.get("nupayMandate", {}).get("amount"), coach.get("totals", {}).get("reducedInstalment", 0)))
    debit_day = str(payload.get("debitDay") or client.get("bank", {}).get("debitDay") or "25")
    mandate_id = new_id("nupay")
    base_url = (payload.get("baseUrl") or request.host_url.rstrip("/") + "/portal").rstrip("/")
    event = {"at": now_iso(), "action": "Mandate sent", "amount": amount, "debitDay": debit_day}
    history = client.get("nupayMandate", {}).get("history", []) + [event]
    client["nupayMandate"] = {"status": "Pending Acceptance", "mandateId": mandate_id, "link": create_secure_link("nupay", tenant_id, client_id, base_url), "amount": amount, "debitDay": debit_day, "sentAt": now_iso(), "cancelledAt": "", "history": history}
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "mandate": client["nupayMandate"]})


@app.get("/api/clients/<client_id>/mandate/status")
def mandate_status(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    return jsonify({"success": True, "tenantId": tenant_id, "mandate": client.get("nupayMandate", {})})


@app.post("/api/clients/<client_id>/mandate/cancel")
def cancel_nupay_mandate(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    history = client.get("nupayMandate", {}).get("history", []) + [{"at": now_iso(), "action": "Mandate cancelled"}]
    client["nupayMandate"].update({"status": "Cancelled", "cancelledAt": now_iso(), "history": history})
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "mandate": client["nupayMandate"]})


@app.post("/api/clients/<client_id>/mandate/resend")
def resend_nupay_mandate(client_id: str):
    cancel_reason = request_json().get("reason", "Resent by consultant/admin")
    response = send_nupay_mandate(client_id)
    # send_nupay_mandate already updates the client. Add a reason to history after it returns by reloading.
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if tenant:
        client = find_client(tenant, client_id)
        if client:
            client.setdefault("nupayMandate", {}).setdefault("history", []).append({"at": now_iso(), "action": "Mandate resent", "reason": cancel_reason})
            save_db(db)
    return response


@app.put("/api/clients/<client_id>/pda")
@app.patch("/api/clients/<client_id>/pda")
def update_pda_info(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    pda = client.get("pdaInfo", {})
    for key, value in request_json().items():
        if key in {"pdaName", "pdaReference", "proposalAmount", "paymentStartDate", "status", "notes"}:
            pda[key] = value
    client["pdaInfo"] = pda
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "pdaInfo": pda})


@app.post("/api/clients/<client_id>/admin-submit")
def submit_to_admin(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    payload = request_json()
    user_id = requested_user_id()
    snapshot = admin_snapshot(client, tenant_id, user_id)
    client["adminHandover"] = {"status": "Submitted", "submittedAt": now_iso(), "submittedBy": user_id, "notes": payload.get("notes", ""), "snapshot": snapshot}
    client["status"] = "Submitted to Admin"
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "handover": client["adminHandover"]})


@app.get("/api/admin/clients")
def admin_clients():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    role_error = require_role(tenant, ["Admin", "Manager"])
    if role_error:
        return role_error
    status = request.args.get("status", "")
    clients = []
    for client in tenant.get("clients", []):
        ensure_client_workflow(client)
        if status and client.get("adminHandover", {}).get("status") != status and client.get("status") != status:
            continue
        clients.append(client)
    clients.sort(key=lambda c: c.get("adminHandover", {}).get("submittedAt") or c.get("updatedAt", ""), reverse=True)
    return jsonify({"success": True, "tenantId": tenant_id, "count": len(clients), "clients": clients})


@app.get("/<path:path>")
def frontend_spa(path: str):
    if path.startswith("api/"):
        return jsonify({"success": False, "error": "Not found", "path": f"/{path}"}), 404
    requested_file = FRONTEND_DIST / path
    if requested_file.exists() and requested_file.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"success": False, "error": "Frontend build not found"}), 404


@app.get("/api/debug/routes")
def debug_routes():
    routes = sorted(str(rule) for rule in app.url_map.iter_rules())
    return jsonify({"success": True, "routes": routes, "note": "All client, document, mandate, admin and PDA routes are tenant-scoped using X-Tenant-ID."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
