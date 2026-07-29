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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request
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
APP_VERSION = "2026.07-parser-dashboard-cleanup"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
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

# Hard CORS fallback. Flask-CORS can miss some preflight/error responses on
# Windows dev servers when a route throws or a method is not registered.
# This guarantees the React app at localhost:5173 receives CORS headers for
# every API/portal response, including 403/404/405/500 and OPTIONS preflights.
CORS_ALLOW_HEADERS = "Content-Type, Authorization, X-Tenant-ID, x-tenant-id, X-User-ID, x-user-id, Accept, Origin"
CORS_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


@app.before_request
def handle_cors_preflight():
    if request.method == "OPTIONS":
        return ("", 204)
    return None


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin") or "*"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = CORS_ALLOW_HEADERS
    response.headers["Access-Control-Allow-Methods"] = CORS_ALLOW_METHODS
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    # Keep backend failures visible to the frontend instead of showing a vague
    # browser CORS error. In debug mode Flask will still log the stack trace.
    code = getattr(exc, "code", 500)
    if code in {400, 401, 403, 404, 405}:
        return jsonify({"success": False, "error": getattr(exc, "description", str(exc)), "status": code}), code
    return jsonify({"success": False, "error": str(exc), "status": 500}), 500

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
    {
        "id": "khusela-debt-management",
        "name": "Khusela Debt Management",
        "tradingName": "Khusela Debt Management",
        "fullName": "Rosande Ruth Roberts",
        "ncr": "NCRDC3999",
        "phone": "076 949 0966",
        "fax": "",
        "email": "admin@kdebt.co.za",
        "finalRegistrationDate": "2022-05-23",
        "physicalAddress": "74 Maynard Road, 3rd Floor, CHB Building, Wynberg",
        "postalAddress": "25 Batts Road, Wynberg, 7800",
        "town": "Cape Town",
        "users": [
            {"id": "khusela-consultant-01", "name": "Khusela Consultant 1", "role": "Consultant", "email": "consultant01@kdebt.co.za"},
            {"id": "khusela-consultant-02", "name": "Khusela Consultant 2", "role": "Consultant", "email": "consultant02@kdebt.co.za"},
            {"id": "khusela-consultant-03", "name": "Khusela Consultant 3", "role": "Consultant", "email": "consultant03@kdebt.co.za"},
            {"id": "khusela-consultant-04", "name": "Khusela Consultant 4", "role": "Consultant", "email": "consultant04@kdebt.co.za"},
            {"id": "khusela-consultant-05", "name": "Khusela Consultant 5", "role": "Consultant", "email": "consultant05@kdebt.co.za"},
            {"id": "khusela-consultant-06", "name": "Khusela Consultant 6", "role": "Consultant", "email": "consultant06@kdebt.co.za"},
            {"id": "khusela-consultant-07", "name": "Khusela Consultant 7", "role": "Consultant", "email": "consultant07@kdebt.co.za"},
            {"id": "khusela-consultant-08", "name": "Khusela Consultant 8", "role": "Consultant", "email": "consultant08@kdebt.co.za"},
            {"id": "khusela-consultant-09", "name": "Khusela Consultant 9", "role": "Consultant", "email": "consultant09@kdebt.co.za"},
            {"id": "khusela-consultant-10", "name": "Khusela Consultant 10", "role": "Consultant", "email": "consultant10@kdebt.co.za"},
            {"id": "khusela-admin-01", "name": "Khusela Admin 1", "role": "Admin", "email": "admin01@kdebt.co.za"},
            {"id": "khusela-admin-02", "name": "Khusela Admin 2", "role": "Admin", "email": "admin02@kdebt.co.za"},
            {"id": "khusela-admin-03", "name": "Khusela Admin 3", "role": "Admin", "email": "admin03@kdebt.co.za"},
            {"id": "khusela-admin-04", "name": "Khusela Admin 4", "role": "Admin", "email": "admin04@kdebt.co.za"},
            {"id": "khusela-manager-01", "name": "Rosande Ruth Roberts", "role": "Manager", "email": "admin@kdebt.co.za"},
            {"id": "khusela-manager-02", "name": "Khusela Operations Manager", "role": "Manager", "email": "manager02@kdebt.co.za"}
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
DRR_SERVICE_FEE = 7000.0

PRODUCT_KNOWLEDGE_MODULES: List[Dict[str, Any]] = [
    {
        "id": "debt-review",
        "title": "Debt Review",
        "service": "Debt Review Sales Coach",
        "summary": "Debt Review is the statutory route for over-indebted consumers who need formal assessment, creditor notices, restructuring and payment monitoring.",
        "keyPoints": [
            "Do not begin statutory processing before signed Form 16 is received.",
            "Minimum client-upload docs: signed Form 16, ID copy, latest payslip and 3 months bank statements.",
            "Admin sequence: intake, Form 17.1, COB requests, COB capture, affordability assessment, Form 17.2, proposal, legal route, PDA/payment monitoring and eventually Form 19 where applicable.",
            "The consultant must not guarantee approval, court outcomes, asset protection or clearance; the registered debt counsellor/admin workflow must assess eligibility.",
        ],
        "salesAngles": [
            "Lead with affordability, protection and stability.",
            "Use the budget to show why the current instalments are unsustainable.",
            "Explain the benefit of one structured plan instead of many broken promises to creditors.",
        ],
    },
    {
        "id": "debt-review-removal",
        "title": "Debt Review Removal",
        "service": "Debt Review Removal",
        "summary": "Debt Review Removal focuses on verifying the client's debt-review status and selecting the correct upliftment/removal route.",
        "keyPoints": [
            "Minimum client-upload docs: ID copy, 3 months bank statements, signed Form 17.W / 17.3, latest payslip and POA.",
            "If the client has no active balances, the sales conversation should focus on removing the flag and rebuilding credit-worthiness.",
            "If balances remain, removal can become a double sale with mediation where appropriate.",
            "The R7,000 removal fee can be collected by NuPay DebiCheck over 1 to 3 months where accepted.",
        ],
        "salesAngles": [
            "Focus on status cleanup, credit-worthiness and future opportunity, not monthly debt relief when balances are zero.",
            "Never promise instant score improvement or guaranteed finance approval.",
            "Explain that paid-up accounts and a removed debt-review flag are two different outcomes.",
        ],
    },
    {
        "id": "debt-mediation",
        "title": "Debt Mediation",
        "service": "Debt Mediation",
        "summary": "Debt Mediation is a non-statutory negotiation service for clients who need reduced payment proposals without positioning it as Debt Review protection.",
        "keyPoints": [
            "Minimum client-upload docs: ID copy, 3 months bank statements, latest payslip and POA.",
            "The consultant must be clear that mediation is not statutory Debt Review protection.",
            "Use included accounts only and match reduced amounts to affordability.",
            "NuPay DebiCheck may collect the ongoing reduced payment where the client accepts the mandate.",
        ],
        "salesAngles": [
            "Show the original instalments versus the reduced proposal.",
            "Use budget pressure points to explain why one realistic plan is better than multiple unaffordable promises.",
            "Position the savings amount as breathing room for essentials and consistency.",
        ],
    },
    {
        "id": "nupay-pda-admin",
        "title": "NuPay, PDA and Admin Handover",
        "service": "Workflow",
        "summary": "Consultants must complete accurate handover data so admin can continue the correct service workflow and payment setup.",
        "keyPoints": [
            "NuPay DebiCheck can apply to DRR fee, mediation reduced payment, or both when applicable.",
            "The DRR 1/2/3 month selector only applies to the removal fee, not ongoing mediation payments.",
            "Admin must see documents, signature, fees, reduced amounts, included creditors, NuPay status and PDA fields.",
            "Tenant isolation means consultants and managers only see clients inside their own tenant.",
        ],
        "salesAngles": [
            "Good data protects the sale after handover.",
            "The consultant should not submit to admin until the client, budget, accounts and service route make sense.",
            "A complete document pack improves conversion and reduces admin delays.",
        ],
    },
]

PRODUCT_KNOWLEDGE_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "q1", "moduleId": "debt-review", "service": "Debt Review", "question": "What document starts the legal Debt Review application process?", "options": ["Signed Form 16", "Power of Attorney only", "NuPay mandate", "Credit report only"], "answerIndex": 0},
    {"id": "q2", "moduleId": "debt-review", "service": "Debt Review", "question": "Which client-upload documents are required for Debt Review in Fin-Tastic?", "options": ["Form 16, ID, latest payslip and 3 months bank statements", "ID, proof of address, POPIA and photos", "Only a credit report", "POA, Form 17.W and paid-up letters only"], "answerIndex": 0},
    {"id": "q3", "moduleId": "debt-review", "service": "Debt Review", "question": "What should the consultant avoid promising in Debt Review?", "options": ["Guaranteed approval or legal outcome", "That admin will verify documents", "That affordability matters", "That the budget must be captured"], "answerIndex": 0},
    {"id": "q4", "moduleId": "debt-review-removal", "service": "Debt Review Removal", "question": "When a DRR client has no balances, what should the sales conversation focus on?", "options": ["Reduced instalments only", "Removing the flag and rebuilding credit-worthiness", "Opening new credit immediately", "Ignoring the debt-review status"], "answerIndex": 1},
    {"id": "q5", "moduleId": "debt-review-removal", "service": "Debt Review Removal", "question": "Which fee can be collected via NuPay DebiCheck for DRR where accepted?", "options": ["R7,000 removal service fee", "A random monthly amount", "Only a creditor instalment", "No fee can ever be collected"], "answerIndex": 0},
    {"id": "q6", "moduleId": "debt-review-removal", "service": "Debt Review Removal", "question": "Which documents are required for Debt Review Removal in this workflow?", "options": ["ID, 3 months bank statements, signed 17.W/17.3, latest payslip and POA", "Signed Form 16 only", "Proof of address and photos only", "Only bank statements"], "answerIndex": 0},
    {"id": "q7", "moduleId": "debt-mediation", "service": "Debt Mediation", "question": "Debt Mediation should be positioned as...", "options": ["Statutory Debt Review protection", "A non-statutory negotiation/reduced-payment service", "A guaranteed loan approval", "A court order"], "answerIndex": 1},
    {"id": "q8", "moduleId": "debt-mediation", "service": "Debt Mediation", "question": "What must the consultant compare when selling mediation?", "options": ["Original instalments versus reduced proposal and budget affordability", "Only the client's age", "Only the credit score", "Only the consultant's target"], "answerIndex": 0},
    {"id": "q9", "moduleId": "nupay-pda-admin", "service": "NuPay", "question": "The 1/2/3 month selector in NuPay applies to...", "options": ["Ongoing mediation payments", "Debt Review Removal fee collection period", "Every account balance", "PDA reference number"], "answerIndex": 1},
    {"id": "q10", "moduleId": "nupay-pda-admin", "service": "Admin Handover", "question": "Before submitting to admin, the consultant should ensure...", "options": ["The selected service, client info, accounts, budget, documents/signature and NuPay status are clear", "Only the client's first name is captured", "The tenant is switched to another company", "No documents are requested"], "answerIndex": 0},
    {"id": "q11", "moduleId": "nupay-pda-admin", "service": "Tenant Isolation", "question": "Tenant isolation means...", "options": ["All companies share one client list", "Each tenant sees only its own clients and users", "Consultants can see competitor clients", "Admin users bypass every tenant"], "answerIndex": 1},
    {"id": "q12", "moduleId": "debt-mediation", "service": "Sales Coach", "question": "The best tonality when discussing financial pressure is...", "options": ["Calm, protective and numbers-based", "Fear-based and aggressive", "Guaranteeing outcomes", "Blaming the client"], "answerIndex": 0},
]


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

def default_living_budget() -> Dict[str, Any]:
    return {
        "rentOrBond": 0,
        "groceries": 0,
        "electricityWater": 0,
        "transport": 0,
        "schoolFees": 0,
        "insurance": 0,
        "medical": 0,
        "cellphoneInternet": 0,
        "clothing": 0,
        "maintenance": 0,
        "otherLivingExpenses": 0,
        "dependants": 0,
        "notes": "",
    }


def living_expense_total(budget: Dict[str, Any] | None) -> float:
    item = {**default_living_budget(), **(budget or {})}
    keys = ["rentOrBond", "groceries", "electricityWater", "transport", "schoolFees", "insurance", "medical", "cellphoneInternet", "clothing", "maintenance", "otherLivingExpenses"]
    return sum(money_to_float(item.get(key)) for key in keys)


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
    selected_services = client.get("serviceTypes") if isinstance(client.get("serviceTypes"), list) else []
    selected_removal_service = client.get("serviceType") == "Debt Review Removal" or "Debt Review Removal" in selected_services
    outstanding = sum(money_to_float(a.get("currentBalance")) for a in included)
    arrears = sum(money_to_float(a.get("arrears")) for a in included)
    original_instalment = sum(money_to_float(a.get("monthlyInstallment")) for a in included)
    reduced = sum(money_to_float(a.get("reducedAmount")) for a in included)
    estimated_relief = max(0.0, original_instalment - reduced)
    savings_percent = round((estimated_relief / original_instalment) * 100) if original_instalment > 0 else 0
    spouse = client.get("spouse") if isinstance(client.get("spouse"), dict) else {}
    household_income = money_to_float(client.get("nettSalary")) + (money_to_float(spouse.get("nettSalary")) if client.get("applicationType") == "Joint" else 0)
    living_expenses = living_expense_total(client.get("budget") if isinstance(client.get("budget"), dict) else {})
    available_after_living = household_income - living_expenses
    available_after_original = available_after_living - original_instalment
    available_after_reduced = available_after_living - reduced
    has_asset = any(a.get("isAsset") or any(k in str(a.get("creditorName", "")).lower() for k in ASSET_KEYWORDS) for a in included)
    has_furniture = any(a.get("isFurniture") or any(k in str(a.get("creditorName", "")).lower() for k in FURNITURE_KEYWORDS) for a in included)
    no_active_balances = outstanding <= 0 and original_instalment <= 0 and arrears <= 0
    no_balance_removal_lead = no_active_balances and (debt_review or selected_removal_service)

    service = "Debt Mediation"
    urgency = "Medium"
    headline = "Debt mediation opportunity detected"
    reasons: List[str] = []
    next_steps: List[str] = []
    objection_handlers: List[str] = []
    pain_points: List[str] = []
    budget_benefits: List[str] = []
    tonality_tips: List[str] = []
    talk_track: List[str] = []

    if no_balance_removal_lead:
        service = "Debt Review Removal"
        urgency = "High"
        headline = "Debt Review Removal: clear the flag and restore credit-worthiness"
        reasons.append("No active balances or monthly instalments are showing, so the sale should not be positioned as debt reduction.")
        reasons.append("Focus on verifying and removing the debt-review flag so the client can become credit-worthy again.")
    elif debt_review:
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
        reasons.append(f"Estimated monthly relief is R{estimated_relief:,.2f} before final affordability checks.")

    if household_income > 0 and living_expenses > 0:
        living_ratio = round((living_expenses / household_income) * 100)
        pain_points.append(f"Living expenses are using about {living_ratio}% of household nett income before debt repayments.")
    if original_instalment > 0 and household_income > 0:
        if available_after_original < 0:
            pain_points.append(f"Before the proposed reduction, the client is short by R{abs(available_after_original):,.2f} after living expenses and normal instalments.")
        else:
            pain_points.append(f"Before the proposed reduction, only R{available_after_original:,.2f} remains after living expenses and normal instalments.")
    if arrears > 0:
        pain_points.append(f"Arrears of R{arrears:,.2f} show that the pressure is already visible, not only theoretical.")
    if estimated_relief > 0:
        budget_benefits.append(f"The proposed reduction can free up about R{estimated_relief:,.2f} per month, roughly {savings_percent}% less than current instalments.")
        budget_benefits.append("That saving can be positioned as breathing room for groceries, transport, electricity and keeping the payment plan consistent.")
    if available_after_reduced >= 0 and reduced > 0:
        budget_benefits.append(f"After living expenses and the proposed payment, the budget still shows R{available_after_reduced:,.2f} available.")
    elif reduced > 0:
        budget_benefits.append("The current reduced proposal still does not fit the captured budget. Lower the reduced amounts before promising affordability.")

    if no_balance_removal_lead:
        pain_points.append("The pressure point is no longer monthly debt relief; it is the debt-review flag still blocking the client from being seen as credit-worthy.")
        pain_points.append("With no balances showing, the client may feel 'I am finished paying', but the bureau/status flag can still stop approvals.")
        budget_benefits.append("The main benefit is restoring borrowing power and credibility, not lowering an instalment.")
        budget_benefits.append("Once the flag is correctly removed, the client may have a better chance of qualifying for future credit, vehicle finance, home finance, rental checks, cellphone contracts and business opportunities, subject to lender assessment.")
        budget_benefits.append("The conversation should position the R7,000 removal fee as a clean-up and status-restoration service, not a payment-plan saving.")
        talk_track.append("The good news is that your report is not showing active balances to restructure. That means our focus is not mediation today — it is getting the debt-review flag removed correctly.")
        talk_track.append("When that flag remains, credit providers can still treat you as high risk even if you have paid your accounts. Removing it helps you start rebuilding your credit-worthiness.")
        talk_track.append("The benefit is not only today's report; it is what becomes possible again afterwards — applying with a cleaner profile and rebuilding trust with lenders.")

    tonality_tips = [
        ("Use a positive, future-focused tone: 'You have done the hard part by clearing the balances; now we need to clean up the status so your profile can move forward.'" if no_balance_removal_lead else "Use a calm, protective tone: 'I can see why this has become stressful, let us work from the numbers.'"),
        "Do not shame the client or sound excited about hardship; speak like you are helping them regain control.",
        "Ask permission before giving advice: 'Can I show you what the budget is telling us?'",
        "Anchor the sale on relief and stability, not fear. Avoid guaranteeing approvals, removals or legal outcomes.",
    ]
    talk_track.append(f"Based on your budget, your household income is R{household_income:,.2f} and your living expenses are R{living_expenses:,.2f}.")
    if estimated_relief > 0:
        talk_track.append(f"Your current instalments are about R{original_instalment:,.2f}. The proposed amount is R{reduced:,.2f}, which could free up around R{estimated_relief:,.2f} every month.")
    if available_after_original < 0:
        talk_track.append("Right now the numbers show a shortfall before we even look at emergencies. That is why a structured solution is important.")
    if available_after_reduced >= 0 and reduced > 0:
        talk_track.append(f"With the reduced amount, the budget becomes more manageable because there is still an estimated R{available_after_reduced:,.2f} left after living expenses and the proposal.")

    if service == "Debt Review Removal":
        if no_balance_removal_lead:
            next_steps = [
                "Verify that there are no remaining active balances that need mediation.",
                "Confirm the debt-review flag/status and whether the route is 17.W, 17.3, clearance/bureau correction, court/NCT or previous-DC follow-up.",
                "Request ID, 3 months bank statements, latest payslip, signed 17.W/17.3 and POA.",
                "Send NuPay DebiCheck for the R7,000 removal fee split over 1-3 months if the client accepts.",
                "Submit the removal pack and track bureau/status confirmation until the profile is updated.",
            ]
            objection_handlers = [
                "I have no debt, why must I pay anything: explain that the service is not for balances; it is to remove the status barrier that can keep causing declined applications.",
                "Will my score go up immediately: explain that removal can make the profile eligible to rebuild, but no score or approval can be guaranteed.",
                "I already paid everyone: agree with the client, then explain that paid-up accounts and a removed debt-review flag are two different outcomes and both must be reflected correctly.",
                "I only need a loan now: keep the tone honest — first remove the flag and rebuild credit-worthiness; do not promise a loan approval.",
            ]
        else:
            next_steps = [
                "Confirm whether the client is still actively under debt review or only still listed at the bureau.",
                "Request ID, 3 months bank statements, latest payslip, signed 17.W/17.3 and POA.",
                "Explain the R7,000 DRR fee and offer a 1-3 month payment arrangement.",
                "If balances remain, present mediation as the second sale to restructure active debts.",
            ]
            objection_handlers = [
                "I already paid my debt counsellor: explain that paid-up history and bureau flag status must still be verified.",
                "I only want my name cleared: explain that removal is step one, but active balances can still affect affordability and score recovery.",
                f"I cannot afford another fee: acknowledge it, then show the monthly split and compare it to the R{estimated_relief:,.2f} potential monthly relief where mediation also applies.",
            ]
    elif service == "Debt Review Sales Coach":
        next_steps = [
            "Confirm income, living expenses, and whether the client is behind on home or vehicle payments.",
            "Position the conversation around protecting the asset and building a sustainable plan.",
            "Request signed Form 16, ID, latest payslip and 3 months bank statements, then start the statutory workflow if the client qualifies.",
        ]
        objection_handlers = [
            "I do not want debt review: explain that assets at risk need urgent protection and eligibility must be assessed first.",
            "I can catch up next month: compare arrears and instalments against nett income before accepting that answer.",
            "I am worried about the process: explain the admin sequence clearly — Form 16, 17.1/COB, assessment, 17.2, proposal and payment setup.",
        ]
    elif service == "Debt Mediation":
        next_steps = [
            "Confirm all income, debit orders, and living expenses before making a proposal.",
            "Use included accounts only and adjust reduced amounts to match affordability.",
            "Send POA/upload-documents link and confirm ID, 3 months bank statements and latest payslip before creditor communication.",
        ]
        objection_handlers = [
            "I can pay creditors myself: explain that one coordinated proposal reduces pressure and missed promises.",
            "I am not in arrears yet: explain mediation can prevent arrears when affordability is already under pressure.",
            f"I need to think about it: bring the client back to the numbers and the potential R{estimated_relief:,.2f} monthly saving.",
        ]

    return {
        "service": service,
        "urgency": urgency,
        "headline": headline,
        "reasons": reasons,
        "nextSteps": next_steps,
        "objectionHandlers": objection_handlers,
        "painPoints": pain_points,
        "budgetBenefits": budget_benefits,
        "tonalityTips": tonality_tips,
        "talkTrack": talk_track,
        "totals": {
            "outstanding": round(outstanding, 2),
            "arrears": round(arrears, 2),
            "originalInstalment": round(original_instalment, 2),
            "reducedInstalment": round(reduced, 2),
            "estimatedRelief": round(estimated_relief, 2),
            "householdIncome": round(household_income, 2),
            "livingExpenses": round(living_expenses, 2),
            "availableAfterLivingExpenses": round(available_after_living, 2),
            "availableAfterReducedPayment": round(available_after_reduced, 2),
            "savingsPercent": savings_percent,
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
            "budget": default_living_budget(),
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
    for default_tenant in DEFAULT_TENANTS:
        tenant_id = default_tenant["id"]
        if tenant_id not in db.get("tenants", {}):
            db.setdefault("tenants", {})[tenant_id] = {**default_tenant, "clients": [], "uploads": [], "commissionSnapshots": [], "knowledgeAssessments": [], "createdAt": now_iso()}
            changed = True
        else:
            tenant_record = db["tenants"][tenant_id]
            # Keep tenant registration/profile fields current while preserving clients/uploads.
            for key, value in default_tenant.items():
                if key == "users":
                    existing_users = {u.get("id"): u for u in tenant_record.get("users", []) if isinstance(u, dict)}
                    merged_users = []
                    for default_user in value:
                        previous = existing_users.pop(default_user.get("id"), {})
                        merged_users.append({**default_user, **{k: v for k, v in previous.items() if k not in {"id", "role"}}})
                    # Preserve legacy users for older demo tenants, but keep Khusela exactly at 10 consultants, 4 admins and 2 managers.
                    if tenant_id != "khusela-debt-management":
                        for legacy_user in existing_users.values():
                            if legacy_user.get("id"):
                                merged_users.append(legacy_user)
                    if tenant_record.get("users") != merged_users:
                        tenant_record["users"] = merged_users
                        changed = True
                elif tenant_record.get(key) != value:
                    tenant_record[key] = value
                    changed = True
            tenant_record.setdefault("commissionSnapshots", [])
            tenant_record.setdefault("knowledgeAssessments", [])
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
                "tradingName": tenant.get("tradingName", tenant.get("name")),
                "fullName": tenant.get("fullName", ""),
                "ncr": tenant.get("ncr"),
                "phone": tenant.get("phone", ""),
                "fax": tenant.get("fax", ""),
                "email": tenant.get("email", ""),
                "finalRegistrationDate": tenant.get("finalRegistrationDate", ""),
                "physicalAddress": tenant.get("physicalAddress", ""),
                "postalAddress": tenant.get("postalAddress", ""),
                "town": tenant.get("town", ""),
                "userCount": len(tenant.get("users", [])),
                "clientCount": len(tenant.get("clients", [])),
            }
        )
    return results




def manager_commission_snapshot(tenant: Dict[str, Any], requested_by: str = "system") -> Dict[str, Any]:
    metrics = consultant_dashboard_metrics(tenant)
    snapshot = {
        "id": new_id("commission"),
        "createdAt": now_iso(),
        "createdBy": requested_by,
        "tenantId": tenant.get("id"),
        "period": datetime.now(timezone.utc).strftime("%Y-%m"),
        "summary": metrics.get("summary", {}),
        "leaderboard": metrics.get("leaderboard", []),
        "notes": "Stored for manager review and commission assessment. Figures are derived from tenant-isolated uploads, clients, documents and handover records.",
    }
    tenant.setdefault("commissionSnapshots", []).append(snapshot)
    # Keep the most recent 120 snapshots to avoid uncontrolled local JSON growth.
    tenant["commissionSnapshots"] = tenant.get("commissionSnapshots", [])[-120:]
    tenant["latestCommissionSnapshot"] = snapshot
    return snapshot


def public_product_knowledge() -> Dict[str, Any]:
    modules = deepcopy(PRODUCT_KNOWLEDGE_MODULES)
    questions = []
    for question in PRODUCT_KNOWLEDGE_QUESTIONS:
        safe = {key: value for key, value in question.items() if key != "answerIndex"}
        questions.append(safe)
    return {"modules": modules, "questions": questions, "passMark": 80, "totalQuestions": len(questions)}


def knowledge_leaderboard(tenant: Dict[str, Any]) -> List[Dict[str, Any]]:
    users = tenant.get("users", [])
    latest_by_user: Dict[str, Dict[str, Any]] = {}
    for result in tenant.get("knowledgeAssessments", []):
        uid = result.get("userId") or "unassigned"
        if uid not in latest_by_user or result.get("submittedAt", "") > latest_by_user[uid].get("submittedAt", ""):
            latest_by_user[uid] = result
    rows: List[Dict[str, Any]] = []
    for user in users:
        if user.get("role") != "Consultant":
            continue
        result = latest_by_user.get(user.get("id", ""), {})
        rows.append({
            "userId": user.get("id"),
            "name": user.get("name"),
            "email": user.get("email", ""),
            "scorePercent": result.get("scorePercent", 0),
            "correct": result.get("correct", 0),
            "total": result.get("total", len(PRODUCT_KNOWLEDGE_QUESTIONS)),
            "rank": 0,
            "level": result.get("level", "Not Assessed"),
            "passed": result.get("passed", False),
            "submittedAt": result.get("submittedAt", ""),
            "attempts": sum(1 for r in tenant.get("knowledgeAssessments", []) if r.get("userId") == user.get("id")),
        })
    rows.sort(key=lambda r: (r.get("scorePercent", 0), r.get("correct", 0), r.get("submittedAt", "")), reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def grade_product_assessment(tenant: Dict[str, Any], user_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    total = len(PRODUCT_KNOWLEDGE_QUESTIONS)
    correct = 0
    review: List[Dict[str, Any]] = []
    answer_map = {str(k): v for k, v in (answers or {}).items()}
    for question in PRODUCT_KNOWLEDGE_QUESTIONS:
        qid = question["id"]
        selected = answer_map.get(qid)
        try:
            selected_index = int(selected)
        except Exception:
            selected_index = -1
        is_correct = selected_index == int(question["answerIndex"])
        if is_correct:
            correct += 1
        review.append({
            "id": qid,
            "moduleId": question.get("moduleId"),
            "service": question.get("service"),
            "question": question.get("question"),
            "selectedIndex": selected_index,
            "correctIndex": question.get("answerIndex"),
            "correct": is_correct,
        })
    score = round((correct / total) * 100, 1) if total else 0.0
    if score >= 90:
        level = "Excellent product knowledge"
    elif score >= 80:
        level = "Passed"
    elif score >= 60:
        level = "Needs coaching"
    else:
        level = "Retraining required"
    user = next((u for u in tenant.get("users", []) if u.get("id") == user_id), {"id": user_id, "name": "Unknown User", "role": "Unknown", "email": ""})
    result = {
        "id": new_id("assessment"),
        "tenantId": tenant.get("id"),
        "userId": user_id,
        "userName": user.get("name"),
        "userRole": user.get("role"),
        "submittedAt": now_iso(),
        "correct": correct,
        "total": total,
        "scorePercent": score,
        "passed": score >= 80,
        "level": level,
        "review": review,
    }
    tenant.setdefault("knowledgeAssessments", []).append(result)
    tenant["knowledgeAssessments"] = tenant.get("knowledgeAssessments", [])[-500:]
    return result


def consultant_dashboard_metrics(tenant: Dict[str, Any]) -> Dict[str, Any]:
    """Return consultant leaderboard metrics for the active tenant only.

    Leads are counted from uploaded credit reports. DC value is the combined
    reduced-payment proposal value plus any applicable DRR removal fees.
    Documents received are counted from required document items marked Uploaded.
    """
    users = tenant.get("users", [])
    metrics: Dict[str, Dict[str, Any]] = {}

    def ensure_user(user_id: str, fallback_name: str = "Unassigned") -> Dict[str, Any]:
        user = next((u for u in users if u.get("id") == user_id), None)
        if not user:
            user = {"id": user_id or "unassigned", "name": fallback_name, "role": "Unassigned", "email": ""}
        uid = user.get("id") or "unassigned"
        if uid not in metrics:
            metrics[uid] = {
                "userId": uid,
                "name": user.get("name") or fallback_name,
                "role": user.get("role", ""),
                "email": user.get("email", ""),
                "leadsGenerated": 0,
                "uploadedReports": 0,
                "activeClients": 0,
                "clientsSubmitted": 0,
                "reducedInstallments": 0.0,
                "removalFees": 0.0,
                "dcValue": 0.0,
                "documentsReceived": 0,
                "requiredDocuments": 0,
                "documentCompletionRate": 0.0,
                "lastActivityAt": "",
            }
        return metrics[uid]

    for user in users:
        if user.get("role") == "Consultant":
            ensure_user(user.get("id", ""), user.get("name", "Consultant"))

    for upload in tenant.get("uploads", []):
        uid = upload.get("userId") or upload.get("uploadedBy") or "unassigned"
        row = ensure_user(uid)
        row["uploadedReports"] += 1
        row["leadsGenerated"] += 1
        at = upload.get("uploadedAt", "")
        if at > row.get("lastActivityAt", ""):
            row["lastActivityAt"] = at

    for client in tenant.get("clients", []):
        uid = client.get("assignedUserId") or client.get("createdBy") or client.get("adminHandover", {}).get("submittedBy") or "unassigned"
        row = ensure_user(uid)
        row["activeClients"] += 1
        updated = client.get("updatedAt", "") or client.get("createdAt", "")
        if updated > row.get("lastActivityAt", ""):
            row["lastActivityAt"] = updated
        if client.get("adminHandover", {}).get("status") == "Submitted" or client.get("status") == "Submitted to Admin":
            row["clientsSubmitted"] += 1

        coach = client.get("coach") or evaluate_sales(client, client.get("accounts", []))
        reduced = money_to_float(coach.get("totals", {}).get("reducedInstalment"))
        if not reduced:
            reduced = sum(money_to_float(a.get("reducedAmount")) for a in client.get("accounts", []) if a.get("included", True))
        row["reducedInstallments"] += reduced

        services = client.get("serviceTypes") or client.get("adminWorkflow", {}).get("services") or admin_services_for(client, coach)
        if "Debt Review Removal" in services or client.get("serviceType") == "Debt Review Removal":
            row["removalFees"] += DRR_SERVICE_FEE

        docs = client.get("documents", {}).get("items", []) if isinstance(client.get("documents"), dict) else []
        row["documentsReceived"] += sum(1 for d in docs if str(d.get("status", "")).lower() == "uploaded")
        row["requiredDocuments"] += len(docs)

    leaderboard = []
    for row in metrics.values():
        row["reducedInstallments"] = round(row["reducedInstallments"], 2)
        row["removalFees"] = round(row["removalFees"], 2)
        row["dcValue"] = round(row["reducedInstallments"] + row["removalFees"], 2)
        req = row.get("requiredDocuments") or 0
        row["documentCompletionRate"] = round((row["documentsReceived"] / req) * 100, 1) if req else 0.0
        # Weighted score keeps the ranking practical for daily consultant management.
        row["performanceScore"] = round((row["leadsGenerated"] * 10) + (row["dcValue"] / 1000) + (row["documentsReceived"] * 4) + (row["clientsSubmitted"] * 8), 2)
        leaderboard.append(row)

    leaderboard.sort(key=lambda r: (r.get("performanceScore", 0), r.get("dcValue", 0), r.get("leadsGenerated", 0), r.get("documentsReceived", 0)), reverse=True)
    for idx, row in enumerate(leaderboard, start=1):
        row["rank"] = idx

    summary = {
        "tenantClients": len(tenant.get("clients", [])),
        "uploadedReports": sum(r["uploadedReports"] for r in leaderboard),
        "leadsGenerated": sum(r["leadsGenerated"] for r in leaderboard),
        "dcValue": round(sum(r["dcValue"] for r in leaderboard), 2),
        "reducedInstallments": round(sum(r["reducedInstallments"] for r in leaderboard), 2),
        "removalFees": round(sum(r["removalFees"] for r in leaderboard), 2),
        "documentsReceived": sum(r["documentsReceived"] for r in leaderboard),
        "clientsSubmitted": sum(r["clientsSubmitted"] for r in leaderboard),
        "consultants": len([r for r in leaderboard if r.get("role") == "Consultant"]),
    }
    return {"summary": summary, "leaderboard": leaderboard}


def required_documents_for(service: str) -> List[str]:
    # Client-upload list only. Admin-generated statutory output documents
    # such as Form 17.1, Form 17.2, proposals and court/NCT packs are tracked
    # separately in the admin workflow and are not requested from the client.
    if service == "Debt Review Sales Coach":
        return [
            "Signed Form 16",
            "ID copy",
            "Latest payslip",
            "3 months bank statements",
        ]
    if service == "Debt Review Removal":
        return [
            "ID copy",
            "3 months bank statements",
            "Signed Form 17.W / 17.3",
            "Latest payslip",
            "Power of Attorney (POA)",
        ]
    if service == "Debt Mediation":
        return [
            "ID copy",
            "3 months bank statements",
            "Latest payslip",
            "Power of Attorney (POA)",
        ]
    return ["ID copy", "Latest payslip", "3 months bank statements"]


def admin_services_for(client: Dict[str, Any], coach: Dict[str, Any]) -> List[str]:
    primary = client.get("serviceType") or coach.get("service") or "Needs Manual Review"
    services: List[str] = []
    outstanding = money_to_float(coach.get("totals", {}).get("outstanding"))
    double_sale = bool(coach.get("flags", {}).get("doubleSaleCandidate")) or (primary == "Debt Review Removal" and outstanding > 0)
    if primary == "Debt Review Removal":
        services.append("Debt Review Removal")
        if double_sale:
            services.append("Debt Mediation")
    elif primary == "Debt Review Sales Coach":
        services.append("Debt Review Sales Coach")
    elif primary == "Debt Mediation":
        services.append("Debt Mediation")
    else:
        services.append("Needs Manual Review")
    seen = set()
    unique = []
    for service in services:
        if service not in seen:
            unique.append(service)
            seen.add(service)
    return unique



def clamp_drr_months(value: Any) -> int:
    months = int(money_to_float(value, 3))
    return max(1, min(3, months))


def nupay_mandate_breakdown(client: Dict[str, Any], coach: Dict[str, Any], drr_months: Any = None) -> Dict[str, Any]:
    services = client.get("serviceTypes") or client.get("adminWorkflow", {}).get("services") or admin_services_for(client, coach)
    includes_drr_fee = "Debt Review Removal" in services or client.get("serviceType") == "Debt Review Removal" or coach.get("service") == "Debt Review Removal"
    includes_mediation = "Debt Mediation" in services or client.get("serviceType") == "Debt Mediation" or coach.get("service") == "Debt Mediation" or money_to_float(coach.get("totals", {}).get("reducedInstalment")) > 0
    months = clamp_drr_months(drr_months or client.get("nupayMandate", {}).get("drrMonths") or 3) if includes_drr_fee else 0
    reduced_payment = round(money_to_float(coach.get("totals", {}).get("reducedInstalment")), 2) if includes_mediation else 0.0
    drr_total = DRR_SERVICE_FEE if includes_drr_fee else 0.0
    drr_monthly = round(drr_total / months, 2) if includes_drr_fee and months else 0.0
    total = round(reduced_payment + drr_monthly, 2)
    if includes_drr_fee and reduced_payment > 0:
        collection_mode = "DebiCheck: DRR service fee plus mediation reduced payment"
    elif includes_drr_fee:
        collection_mode = "DebiCheck: DRR service fee only"
    elif reduced_payment > 0:
        collection_mode = "DebiCheck: mediation reduced payment only"
    else:
        collection_mode = "No NuPay DebiCheck collection configured"
    return {
        "amount": total,
        "drrMonths": months,
        "includesDrrFee": includes_drr_fee,
        "includesMediationPayment": reduced_payment > 0,
        "components": {
            "reducedPayment": reduced_payment,
            "drrServiceFeeTotal": drr_total,
            "drrServiceFeeMonthly": drr_monthly,
            "totalMonthlyCollection": total,
            "ongoingMonthlyCollection": reduced_payment,
            "drrFeeMonthsRemaining": months,
            "collectionMode": collection_mode,
            "product": "NuPay DebiCheck",
            "reducedPaymentLabel": "Debt Mediation / reduced creditor payment",
            "drrFeeLabel": "Debt Review Removal service fee",
        },
    }

def admin_task_templates(services: List[str]) -> List[Dict[str, Any]]:
    """Service-aware admin workflow in the actual operational order.

    Debt Review tasks are intentionally sequenced from consultant handover to final
    Form 19/bureau closure. The legal/statutory section only starts after signed
    Form 16 is confirmed. Client-upload documents remain limited to the packs
    requested by the business owner; statutory generated outputs are tracked here.
    """
    rows: List[Dict[str, Any]] = []

    def slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def add_step(
        service: str,
        sequence: int,
        phase: str,
        label: str,
        *,
        due_business_days: int | None = None,
        due_from: str = "",
        regulation: str = "",
        evidence: str = "",
        minimum: bool = False,
        owner: str = "Admin",
        gate: str = "",
        outcome: str = "",
        notes: str = "",
    ) -> None:
        rows.append({
            "id": f"{slug(service)}-step-{sequence:02d}-{slug(label)[:42]}",
            "service": service,
            "sequence": sequence,
            "stepCode": f"{slug(service).upper()[:3]}-{sequence:02d}",
            "phase": phase,
            "label": label,
            "status": "Not Started",
            "notes": notes,
            "completedAt": "",
            "updatedAt": "",
            "ownerRole": owner,
            "dueBusinessDays": due_business_days,
            "dueFrom": due_from,
            "regulationRef": regulation,
            "evidenceRequired": evidence,
            "ncaMinimum": minimum,
            "gate": gate,
            "outcome": outcome,
        })

    for service in services:
        if service == "Debt Review Sales Coach":
            dr = "NCA s86 / Regulation 24 operational control"
            add_step(service, 1, "Consultant Handover", "Receive consultant handover and lock selected service as Debt Review", evidence="Consultant handover snapshot with client info, accounts, reduced amount and notes", outcome="Admin owns the file")
            add_step(service, 2, "Intake Verification", "Verify client profile, ID number, contact details, marital/joint status and spouse details", evidence="Updated client profile", minimum=True)
            add_step(service, 3, "Required Client Documents", "Confirm only required client docs: signed Form 16, ID copy, latest payslip and 3 months bank statements", evidence="Signed Form 16, ID copy, latest payslip, 3 months bank statements", minimum=True, gate="Do not start statutory notices until complete")
            add_step(service, 4, "Credit Agreement Review", "Verify all included credit agreements from credit report and mark excluded, closed, legal or prescribed-candidate accounts", evidence="Included-creditor schedule", minimum=True)
            add_step(service, 5, "Budget / Affordability", "Verify nett income, living-expense budget, dependants, bank details and available amount before proposal", evidence="Captured living budget and affordability summary", minimum=True)
            add_step(service, 6, "Form 16 Accepted", "Record Form 16 received/signed date and open the legal debt-review application timer", due_from="Signed Form 16", regulation="NCA s86 application control", evidence="Form 16 date and proof of receipt", minimum=True, gate="This is where the legal debt-review process starts")
            add_step(service, 7, "Form 17.1", "Send Form 17.1/application notice to every included credit provider and registered credit bureau", due_business_days=5, due_from="Form 16/application received", regulation=dr, evidence="17.1 copies and proof of dispatch per creditor/bureau", minimum=True)
            add_step(service, 8, "COB Requests", "Request Certificates of Balance from every included creditor and create follow-up dates", due_business_days=5, due_from="17.1 dispatch", regulation=dr, evidence="COB request log and creditor communication proof", minimum=True)
            add_step(service, 9, "COB Capture", "Capture COB balances, arrears, instalments, interest/rates and account status per creditor", evidence="COB copy per creditor", minimum=True)
            add_step(service, 10, "COB Reconciliation", "Compare COB values against parsed credit-report figures and resolve discrepancies", evidence="Reconciled creditor schedule with notes", minimum=True)
            add_step(service, 11, "Assessment", "Complete over-indebtedness assessment using income, living budget, bank statements, payslip and COBs", due_business_days=30, due_from="Debt-review application date", regulation="NCA s86(6) assessment control", evidence="Assessment worksheet", minimum=True)
            add_step(service, 12, "Assessment", "Check reckless-credit/legal-action indicators and flag accounts requiring legal/compliance review", evidence="Reckless/legal risk notes", minimum=True)
            add_step(service, 13, "Form 17.2 Decision", "Issue Form 17.2 outcome: rejected/not over-indebted or accepted/over-indebted/restructuring", due_business_days=30, due_from="Debt-review application date", regulation="NCA s86 / Regulation 24 decision notification", evidence="Form 17.2 and proof of dispatch", minimum=True, gate="If rejected, stop Debt Review workflow and close or move to mediation")
            add_step(service, 14, "Proposal", "Prepare restructuring proposal using available amount and included creditor schedule", evidence="Proposal calculation and creditor schedule", minimum=True)
            add_step(service, 15, "Creditor Negotiation", "Send proposal to every included creditor and track accepted, rejected, counter-offer or no response", evidence="Proposal dispatch proof and response register", minimum=True)
            add_step(service, 16, "Legal Pack", "Prepare consent order, NCT or magistrates court pack based on responses and case route", due_business_days=60, due_from="Debt-review application date", regulation="NCA s86(8), s87 and s86(10) risk control", evidence="Legal pack, case/reference number or submission proof", minimum=True)
            add_step(service, 17, "PDA Setup", "Capture PDA name, reference, proposed distribution amount, debit day and first payment date", evidence="PDA reference/payment schedule", minimum=True, owner="Admin/PDA")
            add_step(service, 18, "Active Debt Review", "Move case into active monitoring only after proposal/order/payment setup is confirmed", evidence="Active status note and first-payment plan", owner="Admin/PDA")
            add_step(service, 19, "Aftercare", "Monitor monthly PDA payments, missed payments, disputes, balance updates and client changes", evidence="Monthly aftercare/payment notes", owner="Admin/PDA")
            add_step(service, 20, "Variation", "If affordability changes, capture new budget/payslip/bank statements and run variation/re-proposal path", evidence="Variation pack or no-change note", owner="Admin/PDA")
            add_step(service, 21, "Paid-Up Tracking", "Collect paid-up letters/settlement confirmations and update included accounts", evidence="Paid-up letters and settlement confirmations", owner="Admin/PDA")
            add_step(service, 22, "Form 19 Clearance", "Issue Form 19 only when clearance requirements are met and all eligible obligations are satisfied", regulation="NCA s71 / NCR Form 19", evidence="Form 19, paid-up proof and debt counsellor approval", minimum=True, owner="Admin/PDA", gate="This is the successful legal end of Debt Review")
            add_step(service, 23, "Bureau Closure", "Send clearance/update to bureaus/NCR records and verify debt-review flag removal/update", evidence="Bureau update proof and final credit-report/status check", minimum=True, owner="Admin/PDA")
            add_step(service, 24, "Closed", "Notify client, lock audit trail and close the admin file", evidence="Client closure notice and final audit note", owner="Admin/PDA", outcome="Debt Review file completed")
        elif service == "Debt Review Removal":
            add_step(service, 1, "Removal Intake", "Receive consultant handover and lock selected service as Debt Review Removal", evidence="Consultant handover snapshot")
            add_step(service, 2, "Required Client Documents", "Confirm only required client docs: ID copy, 3 months bank statements, signed Form 17.W/17.3, latest payslip and POA", evidence="ID, 3 months bank statements, signed 17.W/17.3, latest payslip, POA", minimum=True)
            add_step(service, 3, "Status Verification", "Verify actual debt-review status from credit report/NCR/bureau/previous debt counsellor information", evidence="Debt-review status evidence", minimum=True)
            add_step(service, 4, "Route Decision", "Classify route: pre-17.2, post-17.2, court/NCT order, paid-up/clearance, incorrect bureau flag or legal review", evidence="Removal route decision note", minimum=True, gate="Do not promise removal until the legal route is known")
            add_step(service, 5, "Fee / Mandate", "Confirm R7,000 DRR service fee split and NuPay mandate collection status", evidence="Accepted NuPay mandate / fee record", minimum=True)
            add_step(service, 6, "Removal Pack", "Prepare removal/upliftment pack according to the verified route", evidence="Removal pack and supporting documents", minimum=True)
            add_step(service, 7, "Submission", "Submit bureau/NCR/court/NCT/previous-DC update action and store proof", evidence="Submission proof", minimum=True)
            add_step(service, 8, "Confirmation", "Track confirmation and verify credit-report/bureau update", evidence="Confirmation letter/status update/final report", minimum=True)
            add_step(service, 9, "Post Removal", "If balances remain, continue only the Debt Mediation workflow for those accounts", evidence="Remaining-balance and mediation note")
            add_step(service, 10, "Closed", "Notify client and close the DRR admin file", evidence="Client closure notice")
        elif service == "Debt Mediation":
            add_step(service, 1, "Mediation Intake", "Receive consultant handover and lock selected service as Debt Mediation", evidence="Consultant handover snapshot")
            add_step(service, 2, "Required Client Documents", "Confirm only required client docs: ID copy, 3 months bank statements, latest payslip and POA", evidence="ID, 3 months bank statements, latest payslip, POA", minimum=True)
            add_step(service, 3, "Authority / Limits", "Confirm client authority and make clear that mediation is not statutory Debt Review protection", evidence="POA/authority and disclosure note", minimum=True)
            add_step(service, 4, "Budget / Affordability", "Verify income, living budget, available amount and bank details", evidence="Captured affordability summary", minimum=True)
            add_step(service, 5, "Creditor Schedule", "Confirm included creditors and remove excluded, closed or non-negotiated accounts", evidence="Mediation creditor schedule", minimum=True)
            add_step(service, 6, "Proposal", "Prepare reduced-payment proposal per creditor using balance, arrears, original instalment and reduced amount", evidence="Proposal pack", minimum=True)
            add_step(service, 7, "Creditor Dispatch", "Send proposal to every included creditor and store proof", evidence="Email/proof of dispatch", minimum=True)
            add_step(service, 8, "Negotiation", "Track acceptance, rejection, counter-offer and escalation per creditor", evidence="Creditor response register", minimum=True)
            add_step(service, 9, "NuPay / Collection", "Send or confirm NuPay mandate for the ongoing reduced payment only", evidence="Accepted mandate and payment schedule", minimum=True, owner="Admin/PDA")
            add_step(service, 10, "Monitoring", "Monitor first payment, creditor responses and client/creditor status notes", evidence="Payment and status notes", owner="Admin/PDA")
            add_step(service, 11, "Closed / Active", "Move to active monitoring or close when arrangement is completed/cancelled", evidence="Closure or active-monitoring note", owner="Admin/PDA")
        else:
            add_step(service, 1, "Manual Review", "Review parser output and select the correct service route before sending statutory documents or sales promises", evidence="Manual-review note", minimum=True)
            add_step(service, 2, "Manual Review", "Confirm required documents and compliance risk before admin processing", evidence="Admin decision note", minimum=True)
    return rows

def merge_admin_workflow(client: Dict[str, Any], coach: Dict[str, Any]) -> Dict[str, Any]:
    services = admin_services_for(client, coach)
    existing = client.get("adminWorkflow") or {}
    generated_tasks = admin_task_templates(services)
    existing_tasks = {task.get("id"): task for task in existing.get("tasks", []) if isinstance(task, dict)}
    tasks = []
    for task in generated_tasks:
        previous = existing_tasks.get(task["id"], {})
        merged = {**task, **previous}
        tasks.append(merged)

    existing_creditors = {item.get("id"): item for item in existing.get("creditorActions", []) if isinstance(item, dict)}
    preferred_service = "Debt Mediation" if "Debt Mediation" in services else services[0]
    creditor_actions = []
    for account in client.get("accounts", []):
        if not account.get("included", True):
            continue
        action_id = account.get("id") or hashlib.sha1(f"{account.get('creditorName','')}:{account.get('accountNumber','')}".encode()).hexdigest()[:10]
        base = {
            "id": action_id,
            "service": preferred_service,
            "creditorName": account.get("creditorName", "Unknown Creditor"),
            "accountNumber": account.get("accountNumber", ""),
            "status": "Not Contacted",
            "currentBalance": money_to_float(account.get("currentBalance")),
            "originalInstallment": money_to_float(account.get("monthlyInstallment")),
            "proposedAmount": money_to_float(account.get("reducedAmount")),
            "response": "",
            "notes": "",
            "updatedAt": "",
        }
        creditor_actions.append({**base, **existing_creditors.get(action_id, {})})

    existing_fees = {item.get("id"): item for item in existing.get("feeItems", []) if isinstance(item, dict)}
    fee_items = []
    if "Debt Review Removal" in services:
        fee_items.append({
            "id": "drr-service-fee",
            "label": "Debt Review Removal service fee",
            "service": "Debt Review Removal",
            "amount": 7000,
            "status": "Not Invoiced",
            "dueDate": "",
            "paidAt": "",
            "notes": "Can be split over 1 to 3 months.",
        })
    reduced = money_to_float(coach.get("totals", {}).get("reducedInstalment"))
    if reduced > 0:
        fee_items.append({
            "id": "reduced-payment-proposal",
            "label": "Reduced payment / NuPay proposal",
            "service": preferred_service,
            "amount": reduced,
            "status": client.get("nupayMandate", {}).get("status", "Not Sent"),
            "dueDate": "",
            "paidAt": "",
            "notes": "Must match affordability and mandate.",
        })
    fee_items = [{**item, **existing_fees.get(item["id"], {})} for item in fee_items]

    return {
        "services": services,
        "activeService": existing.get("activeService") if existing.get("activeService") in services else services[0],
        "overallStatus": existing.get("overallStatus", "Handover Received"),
        "tasks": tasks,
        "creditorActions": creditor_actions,
        "feeItems": fee_items,
        "lastUpdatedAt": existing.get("lastUpdatedAt", ""),
    }


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
    # Do not keep old/non-required document rows in the required-document checklist.
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
    existing_mandate = client.get("nupayMandate", {}) if isinstance(client.get("nupayMandate"), dict) else {}
    mandate_breakdown = nupay_mandate_breakdown(client, coach, existing_mandate.get("drrMonths") or 3)
    stored_amount = money_to_float(existing_mandate.get("amount"), 0)
    # If an older saved mandate only had the reduced payment amount, upgrade it to include the DRR fee monthly portion.
    amount = stored_amount if stored_amount > 0 else mandate_breakdown["amount"]
    if mandate_breakdown["includesDrrFee"] and stored_amount <= mandate_breakdown["components"]["reducedPayment"] + 0.01:
        amount = mandate_breakdown["amount"]
    components = existing_mandate.get("components") if isinstance(existing_mandate.get("components"), dict) else mandate_breakdown["components"]
    if mandate_breakdown["includesDrrFee"]:
        components = mandate_breakdown["components"]
    nupay = {
        "status": existing_mandate.get("status", "Not Sent"),
        "mandateId": existing_mandate.get("mandateId", ""),
        "link": existing_mandate.get("link", ""),
        "amount": amount,
        "debitDay": existing_mandate.get("debitDay", client.get("bank", {}).get("debitDay", "25")),
        "drrMonths": mandate_breakdown["drrMonths"],
        "includesDrrFee": mandate_breakdown["includesDrrFee"],
        "components": components,
        "sentAt": existing_mandate.get("sentAt", ""),
        "cancelledAt": existing_mandate.get("cancelledAt", ""),
        "history": existing_mandate.get("history", []),
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
    temp_client = {**client, "documents": documents, "signature": signature, "nupayMandate": nupay, "adminHandover": admin, "pdaInfo": pda}
    admin_workflow = merge_admin_workflow(temp_client, coach)
    return {"documents": documents, "signature": signature, "nupayMandate": nupay, "adminHandover": admin, "pdaInfo": pda, "adminWorkflow": admin_workflow, "serviceTypes": admin_workflow.get("services", [service])}


def ensure_client_workflow(client: Dict[str, Any]) -> Dict[str, Any]:
    client.setdefault("bank", default_bank())
    client.setdefault("budget", default_living_budget())
    if isinstance(client.get("budget"), dict):
        for key, value in default_living_budget().items():
            client["budget"].setdefault(key, value)
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
    base.setdefault("budget", default_living_budget())
    if isinstance(base.get("budget"), dict):
        for key, value in default_living_budget().items():
            base["budget"].setdefault(key, value)
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



def extract_xds_basic_details(text: str) -> Dict[str, Any]:
    """Extract XDS personal details from the Personal Details Summary block.

    XDS PDF text is column-based and often interleaves the left/right columns.
    This parser uses line anchors instead of wide greedy regex so values like
    Gender/Marital Status/Employer do not swallow the whole report.
    """
    lines = [clean_spaces(line.replace("\xa0", " ")) for line in (text or "").splitlines() if clean_spaces(line)]
    flat = clean_spaces((text or "").replace("\xa0", " "))

    def line_value(label: str, stop_labels: List[str] | None = None) -> str:
        stop_labels = stop_labels or []
        for line in lines:
            # XDS labels are at the start of the extracted row. Avoid matching labels
            # mentioned in descriptions, for example "Name, Gender, Marital Status".
            if not re.match(rf"^{re.escape(label)}\b", line, re.I):
                continue
            value = re.sub(rf"^{re.escape(label)}\s*[:\-]?\s*", "", line, flags=re.I).strip()
            for stop in stop_labels:
                value = re.split(rf"{re.escape(stop)}", value, flags=re.I)[0].strip()
            return clean_spaces(value)
        return ""

    id_number = regex_first([r"\bID\s*No\.\s*(\d{13})", r"Enquiry\s+Input\s+(\d{13})"], flat) or ""
    surname = line_value("Surname", ["Residential Address"])
    first_name = line_value("First Name", ["Postal Address"])
    second_name = line_value("Second Name", ["Telephone No.", "Title", "Gender"])
    gender = line_value("Gender", ["Cellular/Mobile", "Cellular", "Mobile"])
    dob = line_value("Date of Birth", ["E-mail Address", "Email Address"])
    marital = line_value("Marital Status", ["Current Employer"])
    email = regex_first([r"E-?mail\s+Address\s+([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"], flat)
    phone = regex_first([r"Cellular/Mobile\s+(\d{7,15})", r"Cellular\s+(\d{7,15})", r"Mobile\s+(\d{7,15})"], flat)
    telephone_h = regex_first([r"Telephone\s+No\.\s*\(H\)\s+(\d{7,15})"], flat)
    telephone_w = regex_first([r"Telephone\s+No\.\s*\(W\)\s+(\d{7,15})"], flat)
    employer = ""
    for row in lines:
        if "Current Employer" in row:
            employer = clean_spaces(re.split(r"Potential Fraud|XDS Presage|ID No\.", re.sub(r"^.*?Current Employer\s*", "", row, flags=re.I), flags=re.I)[0])
            break

    # Residential address can appear as the line before/after the Surname row in extracted XDS text.
    residential = ""
    for i, line in enumerate(lines):
        if "Residential Address" in line:
            before = lines[i - 1] if i > 0 else ""
            after = lines[i + 1] if i + 1 < len(lines) else ""
            candidates = []
            # Same-line value after Residential Address is sometimes present.
            same = re.sub(r"^.*?Residential Address\s*[:\-]?\s*", "", line, flags=re.I).strip()
            if same and same.lower() != line.lower():
                candidates.append(same)
            if before and not re.search(r"\b(ID No|Reference|Surname|First Name|Second Name|Title|Gender|Date of Birth|Marital Status)\b", before, re.I):
                candidates.append(before)
            if after and not re.search(r"\b(First Name|Second Name|Title|Gender|Date of Birth|Marital Status|Potential Fraud)\b", after, re.I):
                candidates.append(after)
            residential = clean_spaces(" ".join(candidates))
            break
    if not residential:
        residential = line_value("Residential Address", ["Postal Address", "Telephone No."])

    # Remove obvious email values from bureau header; prefer the consumer email near Date of Birth.
    if email and "xds.co.za" in email.lower():
        email = regex_first([r"E-?mail\s+Address\s+([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})"], flat)

    score = extract_score(text)
    debt_review_listed = bool(re.search(r"Debt\s+Review\s+Status\s+(?!\*?\s*Nothing\s+on\s+Record)(Consumer\s+is\s+under\s+Debt\s+Review|Listed|Active)", flat, re.I))
    return {
        "firstName": title_case_name(first_name),
        "secondName": title_case_name(second_name),
        "surname": title_case_name(surname),
        "fullName": clean_spaces(" ".join(x for x in [title_case_name(first_name), title_case_name(second_name), title_case_name(surname)] if x)),
        "idNumber": id_number,
        "dateOfBirth": dob,
        "gender": title_case_name(gender),
        "maritalStatus": title_case_name(marital),
        "email": email,
        "phone": re.sub(r"\D", "", phone or telephone_h or telephone_w),
        "whatsapp": re.sub(r"\D", "", phone or ""),
        "physicalAddress": residential,
        "employer": employer,
        "occupation": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
        "creditScore": score,
        "scoreFound": score is not None,
        "debtReviewListed": debt_review_listed,
    }

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
    low_flat = flat.lower()
    if "datanamix" in low_flat:
        return extract_datanamix_basic_details(text)
    if "xds" in low_flat or "xpert decision systems" in low_flat:
        return extract_xds_basic_details(text)
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
    ("mbd", "MBD"), ("dmc909", "DMC909"), ("dmc", "DMC"),
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

def is_identifier_like_creditor(name: str) -> bool:
    """True when the parsed creditor is really an account/reference number.

    Several bureau PDFs place account numbers or payment-profile identifiers in
    the first column. Those must not become creditor names.
    """
    value = clean_spaces(name or "")
    if not value:
        return True
    if known_creditor_name(value):
        return False
    letters = len(re.findall(r"[A-Za-z]", value))
    digits = len(re.findall(r"\d", value))
    # Pure numeric / reference-like values such as 61274-3803 or 73242240001.
    if letters == 0 and digits >= 4:
        return True
    # Mostly digits with a small suffix/prefix is usually an account number, not a creditor.
    if digits >= 5 and digits > letters * 2:
        return True
    # Single letter + long number / short code patterns from account type columns.
    if re.fullmatch(r"[A-Za-z]?\d[\d\- /]{4,}", value):
        return True
    return False


def is_plausible_creditor(name: str, require_meaningful: bool = True) -> bool:
    raw = clean_spaces(name)
    low = raw.lower()
    if not low or low == "unknown creditor":
        return False
    if is_identifier_like_creditor(raw):
        return False
    if any(bad in low for bad in ["total", "count", "friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday", "months", "payment profile", "payment history", "summary", "description", "consumer", "telephone", "address"]):
        return False
    words = [w for w in re.split(r"\W+", low) if w]
    meaningful = [w for w in words if w not in WEAK_ACCOUNT_WORDS and len(w) > 1 and not w.isdigit()]
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
                        # Reject rows where the detected creditor column is actually an account/reference number.
                        if is_identifier_like_creditor(creditor):
                            continue
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
    """Parse XDS CPA + NLR account status rows using line-aware rules.

    XDS report extraction commonly wraps account numbers and company names onto
    neighbouring lines. This parser uses the account table row order from XDS:
    Date Opened, Company, Account No, Open Balance/Credit Limit, Current Balance,
    Instalment Amount, Arrears Amount, Type Code, Status, Last Paid Date.
    """
    accounts: List[Dict[str, Any]] = []
    raw_lines = [clean_spaces(line.replace("\xa0", " ")) for line in (text or "").splitlines() if clean_spaces(line)]
    date_re = re.compile(r"^(\d{4}/\d{2}/\d{2})\b")
    amount_tail_re = re.compile(
        r"R\s*([\d ]+)\s+R\s*([\d ]+)\s+R\s*([\d ]+)\s+R\s*([\d ]+)\s+([A-Z0-9])\s+"
        r"(Active|Closed|Paid\s+Up|In\s+Arrears|Written\s+Off|Handed\s+Over|Current)"
        r"(?:\s+(\d{4}/\d{2}/\d{2}))?\b",
        re.I,
    )

    def section_lines(start_label: str, stop_labels: List[str]) -> List[str]:
        start_idx = -1
        for idx, line in enumerate(raw_lines):
            if start_label.lower() in line.lower():
                start_idx = idx + 1
                break
        if start_idx < 0:
            return []
        end_idx = len(raw_lines)
        for idx in range(start_idx, len(raw_lines)):
            low = raw_lines[idx].lower()
            if any(stop.lower() in low for stop in stop_labels):
                end_idx = idx
                break
        return raw_lines[start_idx:end_idx]

    def digits_only(value: str) -> str:
        return re.sub(r"\D", "", value or "")

    def previous_account_context(lines: List[str], idx: int) -> Tuple[str, str]:
        prev = lines[idx - 1] if idx > 0 else ""
        creditor = ""
        acc = ""
        if prev and not date_re.search(prev) and not re.search(r"\b(R\s*\d|Definitions|Indicators|Company|Opened|Amount|Account)\b", prev, re.I):
            # Ex: "Capitec Bank Access 0902221893130" or just "1010114349604"
            m = re.search(r"^(?:(?P<name>.*?)[ ]+)?(?P<acc>\d[\d ]{5,24})$", prev)
            if m:
                creditor = clean_spaces(m.group("name") or "")
                acc = digits_only(m.group("acc"))
        return creditor, acc

    def next_continuation(lines: List[str], idx: int) -> Tuple[str, str]:
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
        if not nxt or date_re.search(nxt):
            return "", ""
        if re.fullmatch(r"\d{1,4}", nxt):
            return "", nxt
        # Ex: "Facility 604" continuation for Capitec Bank Access Facility + account suffix.
        m = re.match(r"^(?P<name>[A-Za-z][A-Za-z&' .\-]{1,40})\s+(?P<suffix>\d{1,6})$", nxt)
        if m and not re.search(r"Definitions|Indicators|Company|Account|Amount", nxt, re.I):
            return clean_spaces(m.group("name")), m.group("suffix")
        return "", ""

    def add_from_date_line(lines: List[str], idx: int, source: str, nlr: bool = False) -> None:
        line = lines[idx]
        dm = date_re.match(line)
        if not dm:
            return
        open_date = dm.group(1)
        rest = line[dm.end():].strip()
        money = amount_tail_re.search(rest)
        if not money:
            return
        before_money = clean_spaces(rest[:money.start()])
        prev_creditor, prev_acc = previous_account_context(lines, idx)
        next_name, next_acc_suffix = next_continuation(lines, idx)

        creditor = ""
        acc = ""
        if before_money:
            # Normal rows contain "Creditor AccountNo" before the first money value.
            m = re.match(r"^(?P<name>.*?)(?:\s+(?P<acc>\d[\d ]{5,24}))?$", before_money)
            if m:
                creditor = clean_spaces(m.group("name") or "")
                acc = digits_only(m.group("acc") or "")
        if not acc and prev_acc:
            acc = prev_acc
        if not creditor and prev_creditor:
            creditor = prev_creditor
        if creditor and next_name and next_name.lower() not in creditor.lower():
            creditor = clean_spaces(f"{creditor} {next_name}")
        if next_acc_suffix and acc and not acc.endswith(next_acc_suffix):
            acc = f"{acc}{next_acc_suffix}"

        if not creditor or is_bad_account_line(creditor):
            return
        code = (money.group(5) or "").upper()
        account_type = ACCOUNT_TYPE_MAP.get(code, code)
        if nlr and code == "P":
            account_type = "Personal Loan"
        accounts.append(build_account_from_fields(
            creditor=creditor,
            account_number=acc,
            account_type=account_type,
            opening=parse_money_token(money.group(1)),
            current=parse_money_token(money.group(2)),
            monthly=parse_money_token(money.group(3)),
            arrears=parse_money_token(money.group(4)),
            status=money.group(6),
            open_date=open_date,
            last_paid=money.group(7) or "",
            raw_line=" | ".join([lines[idx - 1] if idx > 0 else "", line, lines[idx + 1] if idx + 1 < len(lines) else ""]),
            parser_source=source,
        ))

    cpa_lines = section_lines("Payment Profile: Credit Account Status", ["B B - Building Loan", "Monthly Payment Behaviour", "Payment Profile: National", "Public Domain Records"])
    for idx, line in enumerate(cpa_lines):
        if date_re.match(line):
            add_from_date_line(cpa_lines, idx, "xds-cpa-line", nlr=False)

    nlr_lines = section_lines("Payment Profile: National Loans Register", ["1 1 - Payday", "Monthly Payment Behaviour", "Public Domain Records", "Definitions Indicators"])
    for idx, line in enumerate(nlr_lines):
        if date_re.match(line):
            add_from_date_line(nlr_lines, idx, "xds-nlr-line", nlr=True)

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
        if is_identifier_like_creditor(creditor):
            continue
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
        warnings.append("Parser is now strict: identifier-like rows are rejected, but verify balances against the PDF and add any missing creditors manually before admin/PDA handover.")
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
    return jsonify({"success": True, "app": APP_NAME, "version": APP_VERSION, "isolation": "X-Tenant-ID scoped"})


@app.get("/health")
@app.get("/api/health")
def health():
    db = load_db()
    return jsonify({"success": True, "status": "ok", "version": APP_VERSION, "tenants": len(db.get("tenants", {}))})


@app.get("/api/tenants")
def tenants():
    db = load_db()
    return jsonify({"success": True, "tenants": public_tenant_summary(db)})


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


@app.get("/api/dashboard/consultants")
def consultant_dashboard_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    metrics = consultant_dashboard_metrics(tenant)
    return jsonify({"success": True, "tenantId": tenant_id, **metrics, "storedSnapshots": len(tenant.get("commissionSnapshots", []))})


@app.get("/api/manager/commission-stats")
def manager_commission_stats_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    denied = require_role(tenant, ["Manager"])
    if denied:
        return denied
    snapshot = manager_commission_snapshot(tenant, requested_user_id())
    save_db(db)
    return jsonify({
        "success": True,
        "tenantId": tenant_id,
        "snapshot": snapshot,
        "history": tenant.get("commissionSnapshots", [])[-12:],
    })


@app.get("/api/learning/product-knowledge")
def product_knowledge_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    latest_user_result = None
    user_id = requested_user_id()
    user_results = [r for r in tenant.get("knowledgeAssessments", []) if r.get("userId") == user_id]
    if user_results:
        latest_user_result = sorted(user_results, key=lambda r: r.get("submittedAt", ""), reverse=True)[0]
    return jsonify({"success": True, "tenantId": tenant_id, **public_product_knowledge(), "latestUserResult": latest_user_result, "leaderboard": knowledge_leaderboard(tenant)})


@app.post("/api/learning/assessment/submit")
def product_assessment_submit_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    user_id = requested_user_id()
    user = current_user(tenant)
    if not user:
        return jsonify({"success": False, "error": "User not found inside this tenant"}), 404
    payload = request_json()
    result = grade_product_assessment(tenant, user_id, payload.get("answers", {}))
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "result": result, "leaderboard": knowledge_leaderboard(tenant)})


@app.get("/api/learning/assessment/leaderboard")
def product_assessment_leaderboard_route():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    return jsonify({"success": True, "tenantId": tenant_id, "leaderboard": knowledge_leaderboard(tenant)})


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




# ---------------------------------------------------------------------------
# Public client portal helpers and pages
# ---------------------------------------------------------------------------

def html_escape(value: Any) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def make_secure_token() -> str:
    return secrets.token_urlsafe(24).replace("-", "")[:32]


def store_portal_token(client: Dict[str, Any], kind: str, token: str) -> None:
    client.setdefault("portalTokens", {})[kind] = {
        "token": token,
        "createdAt": now_iso(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }


def create_secure_link(kind: str, tenant_id: str, client_id: str, base_url: str, client: Dict[str, Any] | None = None) -> str:
    token = make_secure_token()
    if client is not None:
        store_portal_token(client, kind, token)
    return f"{base_url.rstrip('/')}/{tenant_id}/{kind}/{client_id}/{token}"


def validate_public_link(tenant_id: str, kind: str, client_id: str, token: str) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, str]:
    db = load_db()
    tenant = db.get("tenants", {}).get(tenant_id)
    if not tenant:
        return None, None, "Unknown tenant"
    client = find_client(tenant, client_id)
    if not client:
        return db, None, "Client not found"
    stored = (client.get("portalTokens") or {}).get(kind, {})
    if stored.get("token") != token:
        return db, None, "This link is invalid or has been replaced by a newer link."
    expires_at = stored.get("expiresAt")
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                return db, None, "This link has expired. Please ask your consultant for a new link."
        except Exception:
            pass
    return db, client, ""


def portal_page(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{html_escape(title)} · Fin-Tastic</title><style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#eef6f8;color:#0b1930}}.wrap{{max-width:840px;margin:30px auto;padding:18px}}.card{{background:#fff;border:1px solid #d8e4ec;border-radius:18px;padding:22px;box-shadow:0 20px 60px rgba(10,30,60,.08)}}h1{{margin:0 0 10px;font-size:28px}}p{{color:#52647b;line-height:1.5}}label{{display:block;margin:12px 0 6px;font-weight:700}}input,select,textarea{{width:100%;box-sizing:border-box;border:1px solid #cdddea;border-radius:10px;padding:11px;background:#f8fbfd}}button{{border:0;border-radius:12px;padding:12px 16px;background:#0e8c8c;color:#fff;font-weight:800;cursor:pointer}}.muted{{color:#68788d;font-size:13px}}.ok{{padding:12px;border-radius:12px;background:#e8fff4;border:1px solid #aee8cb;color:#095f37}}.bad{{padding:12px;border-radius:12px;background:#fff2f2;border:1px solid #f2b8b8;color:#8a1f1f}}.doc{{display:grid;grid-template-columns:1fr 170px;gap:10px;align-items:center;border:1px solid #e4edf4;border-radius:12px;padding:12px;margin:10px 0}}.doc small{{color:#607086}}.badge{{display:inline-block;border-radius:999px;padding:5px 9px;background:#edf4fb;font-weight:700;font-size:12px}}</style>
</head><body><main class='wrap'><section class='card'>{body}</section></main></body></html>"""


def portal_error(message: str, status: int = 400):
    return portal_page("Link problem", f"<h1>Link problem</h1><div class='bad'>{html_escape(message)}</div><p>Please contact your consultant and ask them to send a new link.</p>"), status, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/portal/<tenant_id>/documents/<client_id>/<token>")
def public_documents_page(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "documents", client_id, token)
    if error or not client:
        return portal_error(error or "Invalid link")
    ensure_client_workflow(client)
    items = client.get("documents", {}).get("items", [])
    doc_options = "".join(f"<option value='{html_escape(item.get('name'))}'>{html_escape(item.get('name'))} - {html_escape(item.get('status'))}</option>" for item in items)
    docs_html = "".join(f"<div class='doc'><div><strong>{html_escape(item.get('name'))}</strong><br><small>{html_escape(item.get('filename') or 'Awaiting upload')}</small></div><span class='badge'>{html_escape(item.get('status') or 'Missing')}</span></div>" for item in items)
    body = f"""<h1>Upload your documents</h1><p class='muted'>Client: {html_escape(client.get('fullName'))} · Tenant: {html_escape(tenant_id)}</p><p>Please choose the document type and upload the matching file. PDF, JPG and PNG files are accepted.</p><form method='post' enctype='multipart/form-data'><label>Document type</label><select name='docName'>{doc_options}</select><label>Choose file</label><input type='file' name='document' accept='.pdf,.jpg,.jpeg,.png' required><p><button type='submit'>Upload Document</button></p></form><h2>Required documents</h2>{docs_html}"""
    return portal_page("Upload documents", body), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/portal/<tenant_id>/documents/<client_id>/<token>")
def public_documents_upload(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "documents", client_id, token)
    if error or not db or not client:
        return portal_error(error or "Invalid link")
    ensure_client_workflow(client)
    doc_name = request.form.get("docName") or "Client document"
    file = request.files.get("document") or request.files.get("file")
    if not file or not file.filename:
        return portal_error("Please choose a file to upload.")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file.filename)
    doc_dir = UPLOAD_DIR / tenant_id / "client_docs" / client_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    stored = doc_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_name}"
    file.save(stored)
    matched = False
    for item in client["documents"].get("items", []):
        if item.get("name") == doc_name:
            item.update({"status": "Uploaded", "filename": file.filename, "uploadedAt": now_iso(), "source": "portal", "storedPath": str(stored)})
            matched = True
            break
    if not matched:
        client["documents"].setdefault("items", []).append({"name": doc_name, "status": "Uploaded", "filename": file.filename, "uploadedAt": now_iso(), "source": "portal", "storedPath": str(stored), "notes": ""})
    client["documents"]["requestStatus"] = "Partially Uploaded"
    if client["documents"].get("items") and all(item.get("status") == "Uploaded" for item in client["documents"].get("items", [])):
        client["documents"]["requestStatus"] = "Complete"
        client["status"] = "Docs Received"
    client["updatedAt"] = now_iso()
    save_db(db)
    return portal_page("Document uploaded", f"<h1>Document uploaded</h1><div class='ok'>{html_escape(doc_name)} was uploaded successfully.</div><p>You may go back and upload another document using the same link.</p>"), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/portal/<tenant_id>/signature/<client_id>/<token>")
def public_signature_page(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "signature", client_id, token)
    if error or not client:
        return portal_error(error or "Invalid link")
    body = f"""<h1>Confirm your signature authority</h1><p class='muted'>Client: {html_escape(client.get('fullName'))}</p><p>By clicking confirm, you acknowledge that you received the service documents/mandate and authorised the consultant/admin team to proceed with the selected service workflow.</p><form method='post'><label>Full name</label><input name='signerName' value='{html_escape(client.get('fullName'))}' required><label>South African ID number</label><input name='idNumber' value='{html_escape(client.get('idNumber'))}' required><label><input type='checkbox' name='accepted' value='yes' required style='width:auto'> I confirm and accept electronic signature/authority for this file.</label><p><button type='submit'>Confirm Signature</button></p></form>"""
    return portal_page("Signature", body), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/portal/<tenant_id>/signature/<client_id>/<token>")
def public_signature_submit(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "signature", client_id, token)
    if error or not db or not client:
        return portal_error(error or "Invalid link")
    signer = request.form.get("signerName") or client.get("fullName")
    client.setdefault("signature", {})
    client["signature"].update({"status": "Signed", "signedAt": now_iso(), "signedBy": signer, "signedIp": request.remote_addr or ""})
    client["updatedAt"] = now_iso()
    save_db(db)
    return portal_page("Signature confirmed", f"<h1>Signature confirmed</h1><div class='ok'>Thank you, {html_escape(signer)}. Your signature status is now saved.</div>"), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/portal/<tenant_id>/nupay/<client_id>/<token>")
def public_nupay_page(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "nupay", client_id, token)
    if error or not client:
        return portal_error(error or "Invalid link")
    mandate = client.get("nupayMandate", {})
    components = mandate.get("components", {}) if isinstance(mandate.get("components"), dict) else {}
    reduced = money_to_float(components.get("reducedPayment"))
    drr_total = money_to_float(components.get("drrServiceFeeTotal"))
    drr_monthly = money_to_float(components.get("drrServiceFeeMonthly"))
    drr_months = mandate.get("drrMonths", 0) or 0
    amount = money_to_float(mandate.get("amount"))
    if mandate.get("includesDrrFee"):
        breakdown_html = f"<ul><li>Debt Mediation / reduced creditor payment: <strong>R {reduced:,.2f}</strong> p/m ongoing</li><li>Debt Review Removal service fee: <strong>R {drr_total:,.2f}</strong> over <strong>{html_escape(drr_months)}</strong> month(s) = <strong>R {drr_monthly:,.2f}</strong> p/m</li><li>Total debit during DRR fee collection: <strong>R {amount:,.2f}</strong> p/m</li><li>After the DRR fee period: <strong>R {reduced:,.2f}</strong> p/m ongoing reduced payment</li></ul>"
        accept_text = "I accept this debit order mandate, including the Debt Review Removal service-fee collection shown above."
    else:
        breakdown_html = f"<ul><li>Debt Mediation / reduced creditor payment: <strong>R {reduced:,.2f}</strong> p/m ongoing</li><li>Debt Review Removal service fee: <strong>Not applicable for this selected service</strong></li></ul>"
        accept_text = "I accept this ongoing monthly NuPay DebiCheck mandate for the reduced payment shown above."
    body = f"""<h1>NuPay DebiCheck mandate confirmation</h1><p class='muted'>Client: {html_escape(client.get('fullName'))}</p>{breakdown_html}<p>Total NuPay DebiCheck amount now being mandated: <strong>R {amount:,.2f}</strong><br>Debit day: <strong>{html_escape(mandate.get('debitDay'))}</strong></p><form method='post'><label>Account holder</label><input name='accountHolder' value='{html_escape(client.get('bank', {}).get('accountHolder') or client.get('fullName'))}' required><label><input type='checkbox' name='accepted' value='yes' required style='width:auto'> {html_escape(accept_text)}</label><p><button type='submit'>Accept Mandate</button></p></form>"""
    return portal_page("NuPay mandate", body), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.post("/portal/<tenant_id>/nupay/<client_id>/<token>")
def public_nupay_submit(tenant_id: str, client_id: str, token: str):
    db, client, error = validate_public_link(tenant_id, "nupay", client_id, token)
    if error or not db or not client:
        return portal_error(error or "Invalid link")
    client.setdefault("nupayMandate", {})
    event = {"at": now_iso(), "action": "NuPay DebiCheck accepted by client", "amount": money_to_float(client["nupayMandate"].get("amount")), "debitDay": client["nupayMandate"].get("debitDay", ""), "drrMonths": client["nupayMandate"].get("drrMonths"), "includesDrrFee": client["nupayMandate"].get("includesDrrFee", False)}
    client["nupayMandate"].setdefault("history", []).append(event)
    client["nupayMandate"].update({"status": "Accepted", "acceptedAt": now_iso(), "acceptedBy": request.form.get("accountHolder") or client.get("fullName"), "acceptedIp": request.remote_addr or ""})
    client["updatedAt"] = now_iso()
    save_db(db)
    return portal_page("Mandate accepted", "<h1>Mandate accepted</h1><div class='ok'>Your mandate acceptance was saved successfully.</div>"), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/api/compliance/nca-minimums")
def nca_minimums_route():
    return jsonify({
        "success": True,
        "note": "Operational minimum controls for workflow configuration. Confirm legal wording with the registered debt counsellor / compliance officer.",
        "debtReviewMinimums": [
            {"step": 1, "control": "Consultant handover received and selected service locked", "evidence": "Handover snapshot"},
            {"step": 2, "control": "Signed Form 16 before statutory debt-review notices", "evidence": "Signed Form 16 + ID copy + latest payslip + 3 months bank statements"},
            {"step": 3, "control": "Form 17.1 notice to all included credit providers and registered credit bureaus", "evidence": "17.1 copy + dispatch proof per party"},
            {"step": 4, "control": "COB request, follow-up, capture and reconciliation per included creditor", "evidence": "COB or follow-up proof per creditor"},
            {"step": 5, "control": "Income, living budget and over-indebtedness assessment", "evidence": "Affordability assessment + decision"},
            {"step": 6, "control": "Form 17.2 outcome after assessment", "evidence": "17.2 copy + proof of dispatch"},
            {"step": 7, "control": "Restructuring proposal and creditor response tracking", "evidence": "Proposal + acceptance/rejection/counter-offer register"},
            {"step": 8, "control": "Consent order, court or NCT preparation where applicable", "evidence": "Legal pack/reference/submission proof"},
            {"step": 9, "control": "PDA/payment setup and active aftercare", "evidence": "PDA reference, first-payment plan and monitoring notes"},
            {"step": 10, "control": "Form 19 only when clearance requirements are met", "evidence": "Paid-up/settlement/legal confirmation + Form 19"},
            {"step": 11, "control": "Bureau update and final closure", "evidence": "Bureau update proof + final client notice"},
        ],
    })

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
    signature_link = create_secure_link("signature", tenant_id, client_id, base_url, client)
    upload_link = create_secure_link("documents", tenant_id, client_id, base_url, client)
    links = {
        "signatureLink": signature_link,
        "uploadLink": upload_link,
        "createdAt": now_iso(),
    }
    client.setdefault("signature", {}).update({"link": signature_link, "status": "Sent", "sentAt": now_iso()})
    client.setdefault("documents", {}).update({"uploadLink": upload_link, "requestStatus": "Sent", "sentAt": now_iso()})
    client["portalLinks"] = links
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "clientId": client_id, **links})




def admin_snapshot(client: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
    coach = client.get("coach") or evaluate_sales(client, client.get("accounts", []))
    return {
        "tenantId": tenant_id,
        "submittedBy": user_id,
        "clientId": client.get("id"),
        "clientName": client.get("fullName"),
        "serviceType": coach.get("service"),
        "serviceTypes": client.get("serviceTypes") or admin_services_for(client, coach),
        "status": client.get("status"),
        "fees": {
            "drrFee": DRR_SERVICE_FEE if "Debt Review Removal" in admin_services_for(client, coach) else 0,
            "drrFeeMonthly": client.get("nupayMandate", {}).get("components", {}).get("drrServiceFeeMonthly", 0),
            "reducedPayment": client.get("nupayMandate", {}).get("components", {}).get("reducedPayment", coach.get("totals", {}).get("reducedInstalment", 0)),
            "nupayAmount": client.get("nupayMandate", {}).get("amount", 0),
            "reducedInstalment": coach.get("totals", {}).get("reducedInstalment", 0),
            "originalInstalment": coach.get("totals", {}).get("originalInstalment", 0),
            "estimatedRelief": coach.get("totals", {}).get("estimatedRelief", 0),
        },
        "creditorsIncluded": [a for a in client.get("accounts", []) if a.get("included", True)],
        "documents": client.get("documents", {}),
        "budget": client.get("budget", default_living_budget()),
        "livingExpenseTotal": living_expense_total(client.get("budget")),
        "signature": client.get("signature", {}),
        "nupayMandate": client.get("nupayMandate", {}),
        "pdaInfo": client.get("pdaInfo", {}),
        "adminWorkflow": client.get("adminWorkflow", {}),
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
    client["documents"]["uploadLink"] = create_secure_link("documents", tenant_id, client_id, base_url, client)
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
    client["signature"].update({"status": "Sent", "link": create_secure_link("signature", tenant_id, client_id, base_url, client), "sentAt": now_iso()})
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
    breakdown = nupay_mandate_breakdown(client, coach, payload.get("drrMonths") or client.get("nupayMandate", {}).get("drrMonths") or 3)
    # Default rule: Debt Mediation reduced payments are ongoing monthly collections.
    # Only DRR/DRR+Mediation clients add the DRR service-fee portion for the selected 1-3 month split.
    # Only allow a manual override when the caller explicitly sends useCustomAmount=true.
    amount = money_to_float(payload.get("amount"), breakdown["amount"]) if payload.get("useCustomAmount") is True else breakdown["amount"]
    components = payload.get("components") if isinstance(payload.get("components"), dict) else breakdown["components"]
    components["totalMonthlyCollection"] = amount
    debit_day = str(payload.get("debitDay") or client.get("bank", {}).get("debitDay") or "25")
    mandate_id = new_id("nupay")
    base_url = (payload.get("baseUrl") or request.host_url.rstrip("/") + "/portal").rstrip("/")
    event = {"at": now_iso(), "action": "NuPay DebiCheck sent", "amount": amount, "debitDay": debit_day, "drrMonths": breakdown["drrMonths"], "includesDrrFee": breakdown["includesDrrFee"]}
    history = client.get("nupayMandate", {}).get("history", []) + [event]
    client["nupayMandate"] = {"status": "Pending Acceptance", "mandateId": mandate_id, "link": create_secure_link("nupay", tenant_id, client_id, base_url, client), "amount": amount, "debitDay": debit_day, "drrMonths": breakdown["drrMonths"], "includesDrrFee": breakdown["includesDrrFee"], "components": components, "sentAt": now_iso(), "cancelledAt": "", "history": history}
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
    history = client.get("nupayMandate", {}).get("history", []) + [{"at": now_iso(), "action": "NuPay DebiCheck cancelled"}]
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
            client.setdefault("nupayMandate", {}).setdefault("history", []).append({"at": now_iso(), "action": "NuPay DebiCheck resent", "reason": cancel_reason})
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


def get_admin_client_or_error(client_id: str):
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return db, tenant_id, tenant, None, tenant_error(tenant_id)
    role_error = require_role(tenant, ["Admin", "Manager"])
    if role_error:
        return db, tenant_id, tenant, None, role_error
    client = find_client(tenant, client_id)
    if not client:
        return db, tenant_id, tenant, None, (jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404)
    ensure_client_workflow(client)
    return db, tenant_id, tenant, client, None


@app.get("/api/clients/<client_id>/admin-workflow")
def get_admin_workflow(client_id: str):
    db, tenant_id, tenant, client, error = get_admin_client_or_error(client_id)
    if error:
        return error
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "adminWorkflow": client.get("adminWorkflow", {})})


@app.get("/api/clients/<client_id>/admin-workflow/status")
def get_admin_workflow_status(client_id: str):
    # Read-only status is safe for any user in the same tenant. Updating the
    # workflow remains restricted to Admin/Manager below. This prevents the
    # consultant UI from hitting a missing/blocked status endpoint.
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    client = find_client(tenant, client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found in this tenant", "tenantId": tenant_id}), 404
    ensure_client_workflow(client)
    save_db(db)
    workflow = client.get("adminWorkflow", {})
    return jsonify({
        "success": True,
        "tenantId": tenant_id,
        "clientId": client_id,
        "overallStatus": workflow.get("overallStatus", "Not Started"),
        "activeService": workflow.get("activeService"),
        "adminWorkflow": workflow,
    })


@app.patch("/api/clients/<client_id>/admin-workflow/status")
def update_admin_workflow_status(client_id: str):
    db, tenant_id, tenant, client, error = get_admin_client_or_error(client_id)
    if error:
        return error
    payload = request_json()
    workflow = client.setdefault("adminWorkflow", merge_admin_workflow(client, client.get("coach", {})))
    if payload.get("overallStatus"):
        workflow["overallStatus"] = payload.get("overallStatus")
    if payload.get("activeService") in workflow.get("services", []):
        workflow["activeService"] = payload.get("activeService")
    workflow["lastUpdatedAt"] = now_iso()
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "adminWorkflow": workflow})


@app.patch("/api/clients/<client_id>/admin-workflow/task")
def update_admin_task(client_id: str):
    db, tenant_id, tenant, client, error = get_admin_client_or_error(client_id)
    if error:
        return error
    payload = request_json()
    task_id = payload.get("taskId") or payload.get("id")
    workflow = client.setdefault("adminWorkflow", merge_admin_workflow(client, client.get("coach", {})))
    found = False
    for task in workflow.get("tasks", []):
        if task.get("id") == task_id:
            found = True
            for key in ["status", "notes", "ownerRole"]:
                if key in payload:
                    task[key] = payload[key]
            task["updatedAt"] = now_iso()
            if task.get("status") in ["Done", "Completed"]:
                task["completedAt"] = task.get("completedAt") or now_iso()
            elif "completedAt" in task:
                task["completedAt"] = ""
            break
    if not found:
        return jsonify({"success": False, "error": "Admin task not found", "taskId": task_id}), 404
    workflow["lastUpdatedAt"] = now_iso()
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "adminWorkflow": workflow})


@app.patch("/api/clients/<client_id>/admin-workflow/creditor")
def update_admin_creditor_action(client_id: str):
    db, tenant_id, tenant, client, error = get_admin_client_or_error(client_id)
    if error:
        return error
    payload = request_json()
    action_id = payload.get("actionId") or payload.get("id")
    workflow = client.setdefault("adminWorkflow", merge_admin_workflow(client, client.get("coach", {})))
    found = False
    for action in workflow.get("creditorActions", []):
        if action.get("id") == action_id:
            found = True
            for key in ["status", "response", "notes", "proposedAmount", "service"]:
                if key in payload:
                    action[key] = money_to_float(payload[key]) if key == "proposedAmount" else payload[key]
            action["updatedAt"] = now_iso()
            break
    if not found:
        return jsonify({"success": False, "error": "Creditor action not found", "actionId": action_id}), 404
    workflow["lastUpdatedAt"] = now_iso()
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "adminWorkflow": workflow})


@app.patch("/api/clients/<client_id>/admin-workflow/fees")
def update_admin_fee_item(client_id: str):
    db, tenant_id, tenant, client, error = get_admin_client_or_error(client_id)
    if error:
        return error
    payload = request_json()
    fee_id = payload.get("feeId") or payload.get("id")
    workflow = client.setdefault("adminWorkflow", merge_admin_workflow(client, client.get("coach", {})))
    found = False
    for fee in workflow.get("feeItems", []):
        if fee.get("id") == fee_id:
            found = True
            for key in ["status", "amount", "dueDate", "paidAt", "notes"]:
                if key in payload:
                    fee[key] = money_to_float(payload[key]) if key == "amount" else payload[key]
            if fee.get("status") == "Paid" and not fee.get("paidAt"):
                fee["paidAt"] = now_iso()
            break
    if not found:
        return jsonify({"success": False, "error": "Fee item not found", "feeId": fee_id}), 404
    workflow["lastUpdatedAt"] = now_iso()
    client["updatedAt"] = now_iso()
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "client": client, "adminWorkflow": workflow})


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


@app.get("/api/debug/routes")
def debug_routes():
    routes = sorted(str(rule) for rule in app.url_map.iter_rules())
    return jsonify({"success": True, "routes": routes, "note": "All client, document, mandate, admin and PDA routes are tenant-scoped using X-Tenant-ID."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
