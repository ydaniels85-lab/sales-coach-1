"""
Fin-Tastic Sales Coach - Multi-Tenant Refined Backend

Run:
  python -m venv venv
  venv\\Scripts\\activate
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
import shutil
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request, send_from_directory, g, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

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
APP_VERSION = "2026.07.3-secure-auth-tenant-dedup"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("FINTASTIC_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = Path(os.environ.get("FINTASTIC_UPLOAD_DIR", str(DATA_DIR / "uploads")))
FRONTEND_DIST = BASE_DIR / "frontend_dist"
DB_PATH = DATA_DIR / "sales_coach_db.json"
OWNER_EMAIL = os.environ.get("FINTASTIC_OWNER_EMAIL", "ydaniels85@gmail.com").strip().lower()
OWNER_PASSWORD = os.environ.get("FINTASTIC_OWNER_PASSWORD", "")
SESSION_COOKIE_NAME = "fintastic_session"
SESSION_HOURS = max(1, int(os.environ.get("FINTASTIC_SESSION_HOURS", "12")))
COOKIE_SECURE = os.environ.get(
    "FINTASTIC_COOKIE_SECURE",
    "1" if os.environ.get("RAILWAY_ENVIRONMENT") else "0",
).strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FINTASTIC_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
for folder in (DATA_DIR, UPLOAD_DIR):
    folder.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Tenant-ID", "x-tenant-id", "Accept", "Origin"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

DEFAULT_TENANTS = [
    {
        "id": "liberty-credit-specialists",
        "name": "Liberty Credit Specialists",
        "ncr": "NCRDC-1829",
        "users": [
            {"id": "platform-owner", "name": "Yunoos Daniels", "role": "PlatformOwner", "email": "ydaniels85@gmail.com", "isPlatformOwner": True, "isActive": False},
            {"id": "lib-agent-1", "name": "Sales Agent 1", "role": "Consultant", "email": "agent1@liberty.local", "isActive": False},
            {"id": "lib-manager", "name": "Manager", "role": "Manager", "email": "manager@liberty.local", "isActive": False},
        ],
    },
    {
        "id": "apex-debt-solutions",
        "name": "Apex Debt Solutions",
        "ncr": "NCRDC-2491",
        "users": [
            {"id": "apex-admin", "name": "Apex Admin", "role": "Admin", "email": "admin@apex.local", "isActive": False},
            {"id": "apex-agent-1", "name": "Apex Consultant", "role": "Consultant", "email": "consultant@apex.local", "isActive": False},
        ],
    },
    {
        "id": "pretoria-debt-administrators",
        "name": "Pretoria Debt Administrators",
        "ncr": "NCRDC-0083",
        "users": [
            {"id": "pta-admin", "name": "Pretoria Admin", "role": "Admin", "email": "admin@pta.local", "isActive": False},
            {"id": "pta-agent-1", "name": "Pretoria Consultant", "role": "Consultant", "email": "consultant@pta.local", "isActive": False},
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
    relief = max(0.0, original_instalment - reduced)
    has_asset = any(a.get("isAsset") or any(k in str(a.get("creditorName", "")).lower() for k in ASSET_KEYWORDS) for a in included)
    has_furniture = any(a.get("isFurniture") or any(k in str(a.get("creditorName", "")).lower() for k in FURNITURE_KEYWORDS) for a in included)
    first_name = clean_spaces(str(client.get("firstName") or client.get("fullName") or "the client")).split(" ")[0]

    service = "Debt Mediation"
    urgency = "Medium"
    headline = "Debt mediation opportunity detected"
    reasons: List[str] = []
    next_steps: List[str] = []

    if debt_review:
        service = "Debt Review Removal"
        urgency = "High"
        headline = "Debt Review Removal lead"
        reasons.append("The report indicates a confirmed debt-review flag or a genuinely detected score of zero, so removal must be assessed first.")
        if outstanding > 0:
            reasons.append("Balances are still showing, creating a possible second sale for mediation after the removal assessment.")
    elif has_asset:
        service = "Debt Review Sales Coach"
        urgency = "High"
        headline = "Asset-protection opportunity"
        reasons.append("Vehicle finance, a home loan, or another asset-style account was detected. Lead with affordability and protecting the asset, subject to eligibility.")
    elif score_found and score is not None and 400 <= score <= 650 and arrears > 0:
        service = "Debt Mediation"
        urgency = "High"
        headline = "Mediation lead with arrears pressure"
        reasons.append("The score and arrears pattern indicate immediate affordability pressure that may benefit from negotiated relief.")
    elif outstanding > 0:
        service = "Debt Mediation"
        urgency = "Medium"
        headline = "Debt mediation lead"
        reasons.append("Outstanding balances are present and can be assessed for a coordinated, affordable repayment proposal.")
    else:
        service = "Needs Manual Review"
        urgency = "Low"
        headline = "Manual assessment needed"
        reasons.append("The available report data is not sufficient to recommend a product safely.")

    if has_furniture:
        reasons.append("Furniture accounts were detected. Confirm the status of the goods and explain the account clearly to the client.")
    if original_instalment > 0:
        reasons.append(f"The working proposal shows estimated monthly relief of R{relief:,.2f}, subject to a complete affordability assessment and creditor acceptance.")

    if service == "Debt Review Removal":
        next_steps = [
            "Confirm whether the client is actively under debt review or only remains listed at the bureau.",
            "Ask for the debt counsellor details, Form 17 documents, court/NCT order, PDA statement and paid-up evidence where available.",
            "Explain the R7,000 removal service fee and the available 1-3 month payment arrangement without promising a guaranteed outcome.",
            "Where active balances remain, assess a separate mediation solution after explaining that removal and repayment restructuring are different services.",
        ]
        call_opening = f"Good day {first_name}. My name is [consultant name] from [company]. I have reviewed the credit report information available to us, and it appears that a debt-review indicator may still be affecting the profile. I would like to ask a few questions to establish whether the listing is still active and what the correct removal process would be. Is this a good time to continue?"
        permission_question = "Before I explain the process, may I confirm what happened with the previous debt-review matter and what result you are hoping to achieve now?"
        discovery_questions = [
            "Are you still paying through a debt counsellor or PDA?",
            "Did you receive a court order, NCT order, Form 17.2 or clearance certificate?",
            "Are all accounts paid up, or do some balances still remain?",
            "When did you last speak to the debt counsellor?",
            "Have you previously tried to remove the debt-review indicator?",
            "What is the main reason you need the listing addressed now?",
        ]
        conversation_guide = [
            {"stage": "1. Confirm the problem", "objective": "Establish whether this is an active debt-review matter or a lingering bureau listing.", "script": "I want to separate the bureau listing from any active balances, because each issue may require a different solution."},
            {"stage": "2. Explain the route", "objective": "Give a simple, honest explanation of the assessment and legal/document process.", "script": "We first verify the status and documents, then determine the appropriate removal route. No outcome can be guaranteed before the evidence is assessed."},
            {"stage": "3. Present the service", "objective": "Connect the service to the client's stated goal.", "script": "Based on what you have told me, the next practical step is a formal removal assessment and document collection."},
            {"stage": "4. Confirm affordability", "objective": "Discuss the service fee and payment option clearly.", "script": "The service fee is R7,000, payable once off or over up to three months. Which payment structure is realistic for you?"},
            {"stage": "5. Secure the next action", "objective": "Obtain consent, documents and mandate.", "script": "I can send one secure link for the required documents and signature so we can start the assessment."},
        ]
        value_points = [
            "A structured assessment of the current debt-review status.",
            "Document guidance for bureau, debt counsellor, PDA, NCT or court requirements.",
            "A clear distinction between removing the indicator and resolving remaining balances.",
            "Progress tracking through the admin workflow.",
        ]
        objections = [
            {"objection": "I already paid my debt counsellor.", "response": "That may support the matter, but payment alone does not confirm that the bureau indicator was lawfully removed. We still need to verify the status and supporting documents.", "followUp": "Do you have a clearance certificate, paid-up letters or the final PDA statement?"},
            {"objection": "I only want my name cleared.", "response": "That is the objective of the removal assessment. I also need to point out any active balances because removing an indicator does not erase valid debt.", "followUp": "May I explain which accounts still show balances and which issue belongs to the removal process?"},
            {"objection": "Why does it cost R7,000?", "response": "The fee covers the status investigation, document preparation, communication and the applicable removal workflow. It is not a payment to guarantee a result.", "followUp": "Would the once-off option or a two- or three-month arrangement suit you better?"},
            {"objection": "Another company said they can do it immediately.", "response": "A responsible provider should first verify the legal and bureau status. Immediate removal cannot be promised without reviewing the facts and documents.", "followUp": "Would you like me to show you exactly what must be verified in your case?"},
            {"objection": "I need to think about it.", "response": "That is understandable. Let us first make sure you know the status, required documents, fee and possible route so that your decision is informed.", "followUp": "Which part would you like clarity on before deciding?"},
            {"objection": "I cannot afford the fee now.", "response": "We can discuss a payment arrangement of up to three months, provided it is affordable and clearly agreed.", "followUp": "What monthly amount would be realistic without placing you under more pressure?"},
        ]
        closing_script = "From what we have confirmed, the appropriate next step is the removal assessment. I will send the secure signature and document link, and we will only proceed once you understand the service, fee and required evidence. Shall we complete that now?"
    elif service == "Debt Review Sales Coach":
        next_steps = [
            "Confirm income, living expenses, arrears and the current status of the home or vehicle account.",
            "Explain debt review as an affordability and asset-protection process, subject to statutory eligibility.",
            "Complete the budget and obtain consent before preparing Form 16, notices and COB requests.",
        ]
        call_opening = f"Good day {first_name}. My name is [consultant name] from [company]. The report shows a home-loan or vehicle-finance type account, so I would like to understand whether the current repayments are placing the asset under pressure. My role is to assess the affordability problem and explain the available regulated options. Is this a good time to ask a few questions?"
        permission_question = "May I first understand what changed in your finances and which payment is causing the most pressure?"
        discovery_questions = [
            "Are the home or vehicle payments currently up to date?",
            "Have you received a demand, cancellation, summons or repossession warning?",
            "What is your current nett household income?",
            "What essential living expenses must be protected every month?",
            "Which creditor payment is most difficult to maintain?",
            "Have you previously applied for debt review or another repayment arrangement?",
        ]
        conversation_guide = [
            {"stage": "1. Identify the pressure", "objective": "Understand the trigger and urgency.", "script": "Let us identify the payment that is no longer sustainable and whether the asset is already at risk."},
            {"stage": "2. Complete affordability", "objective": "Use verified income and expenses instead of assumptions.", "script": "I need the full household budget so that any recommendation is based on what you can genuinely afford."},
            {"stage": "3. Explain debt review", "objective": "Explain the regulated process without fear-based selling.", "script": "Debt review can restructure qualifying credit obligations and may help protect assets while the consumer complies with the plan, but eligibility and legal timelines must be assessed."},
            {"stage": "4. Show the proposed relief", "objective": "Compare contractual and working reduced payments.", "script": f"The current included instalments total about R{original_instalment:,.2f}; the working proposal is about R{reduced:,.2f}, subject to the formal assessment and creditor process."},
            {"stage": "5. Obtain informed consent", "objective": "Confirm understanding and secure the next action.", "script": "If the option is suitable, the next step is consent, documents and the full affordability application."},
        ]
        value_points = [
            "One affordability assessment across included credit agreements.",
            "A regulated process with notices, creditor balances and a formal proposal.",
            "A focus on sustainable living expenses and qualifying asset protection.",
            "A documented admin and PDA handover.",
        ]
        objections = [
            {"objection": "I do not want debt review.", "response": "I understand. My role is not to force the option; it is to assess whether your current payments are sustainable and explain the consequences and alternatives accurately.", "followUp": "What concerns you most about debt review?"},
            {"objection": "I can catch up next month.", "response": "That may be possible, but we should compare the arrears and contractual instalments with your actual disposable income before relying on that plan.", "followUp": "After essential expenses, how much is genuinely available for all creditors next month?"},
            {"objection": "Will I lose my car or house?", "response": "No honest adviser can give a blanket guarantee. The risk depends on the account status, legal action and your compliance. The purpose is to assess the situation early and follow the correct process.", "followUp": "Have you received any formal enforcement or cancellation notice?"},
            {"objection": "Will I be blacklisted?", "response": "Debt review is reflected at credit bureaus while the process is active, and access to new credit is restricted. The aim is rehabilitation through an affordable plan, not new borrowing.", "followUp": "Is your priority new credit now, or stabilising the existing obligations and protecting essential assets?"},
            {"objection": "I need another loan instead.", "response": "Additional borrowing may increase the pressure and may not be available. We should first establish whether the current debt is already unaffordable.", "followUp": "Would you be comfortable reviewing the budget before taking on another repayment?"},
            {"objection": "I need to speak to my spouse.", "response": "That is appropriate, particularly for a joint household or marriage in community of property. We can explain the process to both of you before any decision.", "followUp": "When can we arrange a call with both applicants?"},
        ]
        closing_script = "The information suggests that a full affordability assessment is the responsible next step. I will send the consent and document link so that we can verify the figures before any formal recommendation. Shall we start with that assessment?"
    elif service == "Debt Mediation":
        next_steps = [
            "Confirm all income, living expenses, debit orders and creditor payments.",
            "Agree which accounts are included and adjust proposed reduced amounts to a realistic budget.",
            "Explain that creditor acceptance is required and send the mediation mandate and document link.",
        ]
        call_opening = f"Good day {first_name}. My name is [consultant name] from [company]. The report shows active balances that may be placing the monthly budget under pressure. I would like to understand the affordability gap and explain how a coordinated creditor proposal could work. Is this a good time to continue?"
        permission_question = "May I ask what you are currently paying, what you can realistically afford, and what has caused the pressure?"
        discovery_questions = [
            "Which accounts are in arrears or likely to fall into arrears?",
            "What is your verified nett income and salary date?",
            "What are your essential monthly living expenses?",
            "Are there debit orders or deductions not shown on the report?",
            "Have any creditors offered arrangements already?",
            "What total monthly debt payment can you maintain consistently?",
        ]
        conversation_guide = [
            {"stage": "1. Understand the shortfall", "objective": "Identify why contractual payments are not sustainable.", "script": "Let us compare the full monthly creditor commitment with the amount left after essential expenses."},
            {"stage": "2. Prioritise accounts", "objective": "Confirm which accounts need negotiation and any legal urgency.", "script": "We will review every included creditor, arrears status and any enforcement communication."},
            {"stage": "3. Build the proposal", "objective": "Create a realistic working amount.", "script": f"The current instalments total about R{original_instalment:,.2f}; the working reduced total is R{reduced:,.2f}, which still needs affordability confirmation and creditor acceptance."},
            {"stage": "4. Explain expectations", "objective": "Avoid implying guaranteed creditor acceptance.", "script": "We submit and manage proposals, but creditors decide whether to accept, counter or decline. You must maintain the agreed payment and keep us informed."},
            {"stage": "5. Secure the mandate", "objective": "Obtain informed authority and documents.", "script": "Once the mandate and supporting documents are complete, the admin team can begin the creditor process."},
        ]
        value_points = [
            "One coordinated view of included creditor payments.",
            "A proposal based on verified affordability rather than repeated promises to individual creditors.",
            "Centralised documents, communication and progress tracking.",
            "Clear payment and mandate records.",
        ]
        objections = [
            {"objection": "I can pay the creditors myself.", "response": "You may do so. Mediation is useful where separate arrangements are difficult to coordinate or the total remains unaffordable.", "followUp": "Have the existing arrangements reduced the total to an amount you can maintain every month?"},
            {"objection": "I am not in arrears yet.", "response": "That is a good reason to act early if the budget already shows a shortfall. The assessment should prevent missed promises rather than wait for deeper arrears.", "followUp": "After essential expenses, is there enough to pay every contractual instalment this month?"},
            {"objection": "Can you guarantee lower payments?", "response": "No. We can prepare and motivate a proposal, but each creditor must consider it. The working figures are not final until agreed.", "followUp": "Would you like to review the proposed amount and the assumptions behind it?"},
            {"objection": "I do not want anyone contacting my creditors.", "response": "No contact should occur without your informed mandate. We explain the authority and scope before you sign.", "followUp": "Which part of creditor communication concerns you?"},
            {"objection": "I need more time.", "response": "That is fair. The risk is that arrears, fees or legal action may continue, so it helps to set a specific follow-up date.", "followUp": "What information do you need, and when should we speak again?"},
            {"objection": "The proposed payment is still too high.", "response": "Then we should not proceed with an unrealistic figure. We need to recheck the budget, included accounts and essential expenses.", "followUp": "Which verified expense or income item has not yet been captured correctly?"},
        ]
        closing_script = "The next step is to confirm the budget and obtain your mandate so the proposal can be prepared accurately. This does not guarantee creditor acceptance, but it gives us authority to begin the structured process. Shall I send the secure link now?"
    else:
        next_steps = [
            "Verify the report quality and capture missing client, income and account details.",
            "Do not recommend a service until debt-review status, balances and affordability are confirmed.",
        ]
        call_opening = f"Good day {first_name}. My name is [consultant name] from [company]. I do not yet have enough reliable information to recommend a service, so I would like to verify a few details before discussing any option. Is this a good time?"
        permission_question = "May I confirm your current debts, income, arrears and whether you have ever been under debt review?"
        discovery_questions = [
            "Have you ever applied for debt review?",
            "Which credit accounts are currently active?",
            "Are any accounts in arrears or legal collections?",
            "What is your current nett income and essential expenditure?",
            "Do you have a financed home or vehicle?",
        ]
        conversation_guide = [
            {"stage": "1. Verify", "objective": "Correct missing or unreliable data.", "script": "I first need to verify the report and affordability information."},
            {"stage": "2. Classify", "objective": "Identify DR status, assets, balances and arrears.", "script": "Once those facts are confirmed, I can explain which service, if any, is appropriate."},
            {"stage": "3. Recommend", "objective": "Only recommend a product supported by the facts.", "script": "I will not recommend or price a service until the assessment is complete."},
        ]
        value_points = ["A fact-based recommendation instead of a generic sale.", "Protection against selecting the wrong service."]
        objections = [
            {"objection": "Just tell me what I qualify for.", "response": "I need reliable debt-review, balance and affordability information to avoid recommending the wrong process.", "followUp": "Can we complete the missing questions first?"}
        ]
        closing_script = "Let us complete the missing information first. Once it is verified, I can give you a clear and responsible recommendation."

    objection_handlers = [f"{item['objection']}: {item['response']}" for item in objections]
    compliance_reminders = [
        "Do not guarantee debt-review removal, creditor acceptance, asset protection, clearance or a credit-score outcome.",
        "Use only verified report and affordability information; correct parser errors before presenting figures.",
        "Obtain informed consent before collecting documents, sending mandates or contacting creditors.",
        "Explain fees, exclusions, timelines and the distinction between different services clearly.",
    ]

    return {
        "service": service,
        "urgency": urgency,
        "headline": headline,
        "reasons": reasons,
        "nextSteps": next_steps,
        "objectionHandlers": objection_handlers,
        "callOpening": call_opening,
        "permissionQuestion": permission_question,
        "discoveryQuestions": discovery_questions,
        "conversationGuide": conversation_guide,
        "valuePoints": value_points,
        "objections": objections,
        "closingScript": closing_script,
        "complianceReminders": compliance_reminders,
        "totals": {
            "outstanding": round(outstanding, 2),
            "arrears": round(arrears, 2),
            "originalInstalment": round(original_instalment, 2),
            "reducedInstalment": round(reduced, 2),
            "estimatedRelief": round(relief, 2),
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
    ensure_security_schema(db)
    return db



def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Return a user without password hashes or other authentication secrets."""
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "role": user.get("role"),
        "email": user.get("email"),
        "isActive": bool(user.get("isActive", False)),
        "isPlatformOwner": bool(user.get("isPlatformOwner", False)),
        "createdAt": user.get("createdAt", ""),
        "lastLoginAt": user.get("lastLoginAt", ""),
    }


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", (value or "").strip().lower()))


def validate_password(password: str) -> str | None:
    if len(password or "") < 12:
        return "Password must be at least 12 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


def all_users(db: Dict[str, Any]):
    for tenant_id, tenant in db.get("tenants", {}).items():
        for user in tenant.get("users", []):
            yield tenant_id, tenant, user


def find_user_by_email(db: Dict[str, Any], email: str):
    wanted = clean_spaces(email).lower()
    for tenant_id, tenant, user in all_users(db):
        if clean_spaces(user.get("email", "")).lower() == wanted:
            return tenant_id, tenant, user
    return None, None, None


def email_in_use(db: Dict[str, Any], email: str, exclude_user_id: str = "") -> bool:
    wanted = clean_spaces(email).lower()
    return any(
        clean_spaces(user.get("email", "")).lower() == wanted
        and str(user.get("id")) != str(exclude_user_id)
        for _tenant_id, _tenant, user in all_users(db)
    )


def ensure_security_schema(db: Dict[str, Any]) -> bool:
    """Migrate old demo users safely without creating default passwords."""
    changed = False
    db.setdefault("sessions", {})
    for _tenant_id, _tenant, user in all_users(db):
        normalized_email = clean_spaces(user.get("email", "")).lower()
        if user.get("email") != normalized_email:
            user["email"] = normalized_email
            changed = True
        for unsafe_key in ("password", "plainPassword", "temporaryPassword"):
            if unsafe_key in user:
                user.pop(unsafe_key, None)
                changed = True
        if "isActive" not in user:
            user["isActive"] = bool(user.get("passwordHash"))
            changed = True

    owner_tenant = db.get("tenants", {}).get("liberty-credit-specialists")
    if owner_tenant is None and db.get("tenants"):
        owner_tenant = next(iter(db["tenants"].values()))
    if owner_tenant is not None:
        owner = next(
            (
                user
                for user in owner_tenant.setdefault("users", [])
                if clean_spaces(user.get("email", "")).lower() == OWNER_EMAIL
            ),
            None,
        )
        if owner is None:
            owner = {
                "id": "platform-owner",
                "name": "Yunoos Daniels",
                "role": "PlatformOwner",
                "email": OWNER_EMAIL,
                "isPlatformOwner": True,
                "isActive": False,
                "createdAt": now_iso(),
            }
            owner_tenant["users"].append(owner)
            changed = True
        expected = {
            "name": "Yunoos Daniels",
            "role": "PlatformOwner",
            "email": OWNER_EMAIL,
            "isPlatformOwner": True,
        }
        for key, value in expected.items():
            if owner.get(key) != value:
                owner[key] = value
                changed = True
        if OWNER_PASSWORD and not owner.get("passwordHash"):
            password_error = validate_password(OWNER_PASSWORD)
            if password_error is None:
                owner["passwordHash"] = generate_password_hash(OWNER_PASSWORD)
                owner["isActive"] = True
                owner["passwordSetAt"] = now_iso()
                changed = True
        if not owner.get("passwordHash") and owner.get("isActive"):
            owner["isActive"] = False
            changed = True
    return changed

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
    changed = ensure_security_schema(db)
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
    requested = (
        request.headers.get("X-Tenant-ID")
        or request.headers.get("x-tenant-id")
        or request.args.get("tenant_id")
        or request.form.get("tenantId")
        or payload.get("tenantId")
        or ""
    )
    auth_user = getattr(g, "current_user", None)
    if auth_user:
        if bool(auth_user.get("isPlatformOwner")):
            return requested or str(getattr(g, "current_tenant_id", "liberty-credit-specialists"))
        return str(getattr(g, "current_tenant_id", ""))
    return requested or "liberty-credit-specialists"


def requested_user_id() -> str:
    auth_user = getattr(g, "current_user", None)
    if auth_user:
        return str(auth_user.get("id") or "system")
    return "system"


def get_tenant(db: Dict[str, Any]) -> Tuple[str, Dict[str, Any] | None]:
    tenant_id = requested_tenant_id()
    return tenant_id, db.get("tenants", {}).get(tenant_id)


def tenant_error(tenant_id: str):
    return jsonify({"success": False, "error": "Tenant not found or access denied."}), 404


def find_client(tenant: Dict[str, Any], client_id: str) -> Dict[str, Any] | None:
    for client in tenant.get("clients", []):
        if client.get("id") == client_id:
            return client
    return None


def current_user(tenant: Dict[str, Any]) -> Dict[str, Any] | None:
    auth_user = getattr(g, "current_user", None)
    if auth_user:
        return auth_user
    return None


def require_role(tenant: Dict[str, Any], allowed_roles: List[str]):
    user = current_user(tenant)
    if user and user.get("isPlatformOwner"):
        return None
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


def configure_tesseract_command() -> str:
    """Locate the Tesseract binary on Railway/Linux or Windows."""
    if pytesseract is None:
        return ""
    candidates = [
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return str(candidate)
    return ""


def tesseract_is_available() -> bool:
    if pytesseract is None:
        return False
    command = configure_tesseract_command()
    if not command:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_pdf_text(path: Path, max_pages: int = 12) -> Tuple[str, List[str]]:
    """OCR scanned/image-only PDFs, with settings tuned for Datanamix reports."""
    warnings: List[str] = []
    if pytesseract is None or pdfium is None:
        warnings.append("OCR Python packages are unavailable. pytesseract, pypdfium2 and Pillow are required.")
        return "", warnings
    if not tesseract_is_available():
        warnings.append("The Tesseract OCR engine is not installed or not visible to the application.")
        return "", warnings
    parts: List[str] = []
    try:
        pdf = pdfium.PdfDocument(str(path))
        page_count = min(len(pdf), max_pages)
        for index in range(page_count):
            page = pdf[index]
            bitmap = page.render(scale=2.35)
            image = bitmap.to_pil().convert("L")
            try:
                from PIL import ImageOps  # type: ignore
                image = ImageOps.autocontrast(image)
            except Exception:
                pass
            text = pytesseract.image_to_string(image, config="--oem 3 --psm 6", timeout=35) or ""
            text = text.replace("\xa0", " ").strip()
            if len(text) < 80:
                retry = pytesseract.image_to_string(image, config="--oem 3 --psm 11", timeout=35) or ""
                if len(retry) > len(text):
                    text = retry.replace("\xa0", " ").strip()
            if text:
                parts.append(f"\n--- OCR PAGE {index + 1} ---\n{text}")
        if parts:
            warnings.append(f"OCR completed successfully. OCR pages read: {len(parts)} of {page_count}.")
        else:
            warnings.append("OCR ran, but no readable text was detected in the PDF pages.")
    except Exception as exc:
        warnings.append(f"OCR extraction failed: {exc}")
    return "\n".join(parts).strip(), warnings


def _datanamix_text_score(text: str) -> int:
    low = (text or "").lower()
    markers = [
        "datanamix", "consumer account status", "subscriber name", "current balance",
        "instalment amount", "open balance", "final score", "debt review",
    ]
    return sum(1 for marker in markers if marker in low)


def extract_pdf_text(path: Path, original_filename: str = "") -> Tuple[str, List[str]]:
    warnings: List[str] = []
    parts: List[str] = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                    if page_text.strip():
                        parts.append(page_text)
        except Exception as exc:
            warnings.append(f"pdfplumber extraction failed: {exc}")
    if not parts and PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
        except Exception as exc:
            warnings.append(f"PyPDF2 extraction failed: {exc}")

    embedded_text = "\n".join(parts).replace("\xa0", " ").strip()
    filename_low = (original_filename or path.name).lower()
    likely_datanamix = "datanamix" in filename_low or _datanamix_text_score(embedded_text) >= 2
    missing_account_markers = not any(marker in embedded_text.lower() for marker in ["subscriber name", "consumer account status", "instalment amount"])
    needs_ocr = len(embedded_text) < 600 or (likely_datanamix and missing_account_markers)

    final_text = embedded_text
    if needs_ocr:
        ocr_text, ocr_warnings = ocr_pdf_text(path)
        warnings.extend(ocr_warnings)
        if ocr_text:
            if likely_datanamix:
                if _datanamix_text_score(ocr_text) >= _datanamix_text_score(embedded_text):
                    final_text = ocr_text
                elif len(ocr_text) > len(embedded_text):
                    final_text = f"{embedded_text}\n{ocr_text}".strip()
            elif len(ocr_text) > len(embedded_text):
                final_text = ocr_text

    if not final_text:
        warnings.append("No extractable text was found after embedded-text extraction and OCR.")
    elif likely_datanamix and _datanamix_text_score(final_text) < 2:
        warnings.append("The file appears to be Datanamix, but OCR did not confidently recover the expected Datanamix headings.")
    return final_text, warnings


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
        "accountNumber": re.sub(r"\s+", "", clean_spaces(account_number or "")).strip("-:/"),
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
    value = re.sub(r"\bR\s*[Oo]\b", "R0", value, flags=re.I)
    value = re.sub(r"(?<=\d)[Oo](?=\d)", "0", value)
    value = re.sub(r"\b[Oo]\b", "0", value)
    return money_to_float(value, 0.0)


def datanamix_label_value(block: str, label: str, stops: List[str]) -> str:
    label_re = re.escape(label).replace(r"\ ", r"\s+").replace(r"\/", r"\s*/\s*")
    label_re = label_re.replace("Instalment", "Instal(?:l)?ment")
    stop_parts = []
    for stop in stops:
        part = re.escape(stop).replace(r"\ ", r"\s+").replace(r"\/", r"\s*/\s*")
        part = part.replace("Instalment", "Instal(?:l)?ment")
        stop_parts.append(part)
    stop_re = "|".join(stop_parts) or r"$^"
    m = re.search(rf"\b{label_re}\s*[:\-]?\s*(.*?)(?=\s+(?:{stop_re})\s*[:\-]?\s*|$)", block or "", re.I | re.S)
    return clean_spaces(m.group(1)).strip(" :-|") if m else ""


def clean_datanamix_creditor(name: str, continuation: str = "") -> str:
    text_value = clean_spaces(f"{name} {continuation}".replace("|", " ").replace("‘", " ").replace("’", " ").replace(chr(34), " "))
    text_value = re.sub(r"\bDMCc(?=\d)", "DMC", text_value, flags=re.I)
    text_value = re.sub(r"\b(?:Current\s+Balance|Instal(?:l)?ment\s+Amount|Arrears\s+Amount|Open\s+Balance|Credit\s+Limit|No\s+Of\s+Participants|Type\s+of\s+Account|Last\s+Paid\s+Date|Date\s+Account\s+Opened|Account\s+Status)\b.*", "", text_value, flags=re.I)
    text_value = re.sub(r"\bAccount\s+(?:No|N[o0]|Number)\.?\b.*", "", text_value, flags=re.I)
    text_value = re.sub(r"[^A-Za-z0-9&'()./\- ]", " ", text_value)
    return clean_spaces(text_value).strip(" -:.")


def parse_datanamix_accounts(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    if not text:
        return accounts
    flat = clean_spaces(text.replace("\xa0", " "))
    flat = re.sub(r"Subscr[i1l]ber\s+Nam[e€]\b", "Subscriber Name", flat, flags=re.I)
    flat = re.sub(r"Ba[i1l]ance", "Balance", flat, flags=re.I)
    flat = re.sub(r"Instal[l1]?ment", "Instalment", flat, flags=re.I)
    flat = re.sub(r"Account\s+N[0o°]\.?\b", "Account No", flat, flags=re.I)

    section_match = re.search(
        r"Consumer\s+Account\s+Status\s*[:\-]?(.*?)(?:Consumer\s+24\s+Monthly\s+Payment\s+History|Definition\s+Code\s+Descriptions|Consumer\s+NLR\s+Account\s+Status|Directorships|Defaults|Adverse\s+Information|Consumer\s+Address\s+History|Enquiry\s+History|General\s+Disclaimer|$)",
        flat,
        re.I | re.S,
    )
    section = section_match.group(1) if section_match else flat
    section = re.split(r"Definition\s+Code\s+Descriptions|Consumer\s+24\s+Monthly\s+Payment\s+History", section, maxsplit=1, flags=re.I)[0]

    block_pattern = re.compile(
        r"Subscriber\s+Name\s*[:\-]?\s*(?P<creditor>.*?)\s+Account\s+(?:No|Number)\.?\s*[:\-]?\s*(?P<acc>[A-Z0-9][A-Z0-9 /\-]{2,35}?)\s+(?P<body>Current\s+Balance.*?)(?=\s+Subscriber\s+Name\s*[:\-]?|Definition\s+Code\s+Descriptions|General\s+Disclaimer|$)",
        re.I | re.S,
    )

    for match in block_pattern.finditer(section):
        creditor = clean_datanamix_creditor(match.group("creditor"))
        body = clean_spaces(match.group("body") or "")
        # OCR can move the final word of a long company name after the account number.
        continuation_match = re.match(r"[,\s'‘’\"-]*(?P<cont>(?:Proprietary|Limited|Pty|Ltd|Bank|Finance)(?:\s+(?:Proprietary|Limited|Pty|Ltd))?)\s+Current\s+Balance\b", body, re.I)
        if continuation_match:
            creditor = clean_datanamix_creditor(creditor, continuation_match.group("cont"))
        if not is_plausible_creditor(creditor, require_meaningful=True):
            continue

        current = datanamix_money(datanamix_label_value(body, "Current Balance", ["Instalment Amount", "Arrears Amount", "Open Balance / Credit Limit"]))
        monthly = datanamix_money(datanamix_label_value(body, "Instalment Amount", ["Arrears Amount", "Open Balance / Credit Limit", "No Of Participants In Joint Loan"]))
        arrears = datanamix_money(datanamix_label_value(body, "Arrears Amount", ["Open Balance / Credit Limit", "No Of Participants In Joint Loan", "Type of Account"]))
        opening = datanamix_money(datanamix_label_value(body, "Open Balance / Credit Limit", ["No Of Participants In Joint Loan", "Type of Account", "Last Paid Date"]))
        account_type = datanamix_label_value(body, "Type of Account", ["Last Paid Date", "Date Account Opened", "Account Status"]) or account_type_from_text(creditor)
        last_paid = datanamix_label_value(body, "Last Paid Date", ["Date Account Opened", "Account Status"])
        open_date = datanamix_label_value(body, "Date Account Opened", ["Account Status", "Subscriber Name"])
        status = datanamix_label_value(body, "Account Status", ["Subscriber Name", "Definition Code Descriptions", "General Disclaimer"]) or "Active"
        raw_account_number = clean_spaces(match.group("acc") or "")
        tail = re.search(r"\s+(Proprietary(?:\s+Limited)?|Pty(?:\s+Ltd)?|Limited|Ltd)$", raw_account_number, re.I)
        if tail:
            creditor = clean_datanamix_creditor(creditor, tail.group(1))
            raw_account_number = raw_account_number[:tail.start()].strip()
        account_number = re.sub(r"\s+", "", raw_account_number).strip("-:/")

        accounts.append(build_account_from_fields(
            creditor=creditor,
            account_number=account_number,
            account_type=account_type,
            opening=opening,
            current=current,
            monthly=monthly,
            arrears=arrears,
            status=status,
            open_date=open_date,
            last_paid=last_paid,
            raw_line=match.group(0),
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
    text, warnings = extract_pdf_text(path, original_filename)
    bureau = detect_bureau(f"{original_filename}\n{text}")
    if text:
        basic = extract_datanamix_basic_details(text) if bureau.lower() == "datanamix" else extract_basic_details(text)
    else:
        basic = {"fullName": "New Parsed Client", "creditScore": None, "scoreFound": False, "debtReviewListed": False}

    used_ocr = any("OCR completed" in warning or "OCR pages read" in warning for warning in warnings)
    table_accounts = [] if used_ocr or bureau.lower() == "datanamix" else parse_accounts_from_tables(path)
    text_accounts = parse_accounts(text, bureau) if text else []
    if bureau.lower() == "xds" and text_accounts:
        accounts = dedupe_accounts(text_accounts)[:80]
        if table_accounts:
            warnings.append("Ignored PDF table rows because the XDS text parser found safer account rows.")
    else:
        accounts = dedupe_accounts(table_accounts + text_accounts)[:80]
    accounts = remove_consumer_name_accounts(accounts, basic)

    if bureau.lower() == "datanamix":
        block_count = len(re.findall(r"Subscriber\s+Name\s*[:\-]?", text or "", re.I))
        warnings.append(f"Datanamix parser detected {block_count} subscriber block(s) and imported {len(accounts)} account(s).")
        if not used_ocr and len(text or "") < 1500:
            warnings.append("Datanamix text was unusually short; verify that OCR is available in the deployed container.")
    if text and table_accounts:
        warnings.append(f"Strict table parser found {len(table_accounts)} account row(s).")
    if text and text_accounts:
        warnings.append(f"Strict text parser found {len(text_accounts)} account row(s).")
    if text and not basic.get("firstName") and not basic.get("surname"):
        warnings.append("Client first name/surname were not confidently detected. Check the PDF or capture them manually.")
    if text and not accounts:
        warnings.append("No account rows were confidently detected. Review the parser warning and OCR status.")
    if accounts:
        warnings.append("Verify all parsed balances against the original PDF before admin/PDA handover.")

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
            "bureau": bureau,
            "textLength": len(text or ""),
            "ocrAvailable": tesseract_is_available(),
            "ocrUsed": used_ocr,
            "datanamixSubscriberBlocks": len(re.findall(r"Subscriber\s+Name\s*[:\-]?", text or "", re.I)),
        },
    }



_LOGIN_ATTEMPTS: Dict[str, List[datetime]] = {}


def _iso_to_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _session_token_from_request() -> str:
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME, "")
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return ""


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def prune_sessions(db: Dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    sessions = db.setdefault("sessions", {})
    expired = [
        key
        for key, session in sessions.items()
        if (_iso_to_datetime(session.get("expiresAt", "")) or now) <= now
    ]
    for key in expired:
        sessions.pop(key, None)
    return bool(expired)


def create_auth_session(db: Dict[str, Any], tenant_id: str, user: Dict[str, Any]) -> str:
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    db.setdefault("sessions", {})[_session_hash(token)] = {
        "tenantId": tenant_id,
        "userId": user.get("id"),
        "createdAt": now.isoformat(),
        "expiresAt": (now + timedelta(hours=SESSION_HOURS)).isoformat(),
    }
    return token


def authenticated_session(db: Dict[str, Any]):
    token = _session_token_from_request()
    if not token:
        return None
    session = db.setdefault("sessions", {}).get(_session_hash(token))
    if not session:
        return None
    expires = _iso_to_datetime(session.get("expiresAt", ""))
    if not expires or expires <= datetime.now(timezone.utc):
        db["sessions"].pop(_session_hash(token), None)
        save_db(db)
        return None
    tenant = db.get("tenants", {}).get(session.get("tenantId"))
    if not tenant:
        return None
    user = next((item for item in tenant.get("users", []) if item.get("id") == session.get("userId")), None)
    if not user or not user.get("isActive") or not user.get("passwordHash"):
        return None
    return session, tenant, user


def client_identity_keys(client: Dict[str, Any]) -> Dict[str, str]:
    """Build identity keys for the primary applicant and spouse/co-applicant."""
    results: Dict[str, str] = {}
    persons = [("primary", client), ("spouse", client.get("spouse") or {})]
    for relation, person in persons:
        if not isinstance(person, dict):
            continue
        id_number = re.sub(r"\D", "", str(person.get("idNumber") or ""))
        if len(id_number) >= 8:
            results[f"id:{id_number}"] = f"{relation} ID number"
        email = clean_spaces(person.get("email") or "").lower()
        if email and valid_email(email):
            results[f"email:{email}"] = f"{relation} email address"
        phone = re.sub(r"\D", "", str(person.get("phone") or person.get("whatsapp") or ""))
        name = clean_spaces(person.get("fullName") or " ".join(
            str(person.get(key) or "") for key in ("firstName", "secondName", "surname")
        )).lower()
        if name in {"", "new client", "new parsed client"}:
            name = ""
        normalized_name = re.sub(r"[^a-z0-9]", "", name)
        if phone and normalized_name:
            results[f"phone-name:{phone[-10:]}:{normalized_name}"] = f"{relation} phone and name"
        dob = clean_spaces(person.get("dateOfBirth") or "")
        if normalized_name and dob:
            results[f"name-dob:{normalized_name}:{dob}"] = f"{relation} name and date of birth"
    return results


def find_duplicate_client(tenant: Dict[str, Any], candidate: Dict[str, Any], exclude_client_id: str = ""):
    candidate_keys = client_identity_keys(candidate)
    if not candidate_keys:
        return None
    for existing in tenant.get("clients", []):
        if str(existing.get("id")) == str(exclude_client_id):
            continue
        overlap = set(candidate_keys).intersection(client_identity_keys(existing))
        if overlap:
            key = sorted(overlap)[0]
            return {
                "clientId": existing.get("id"),
                "fullName": existing.get("fullName") or "Existing client",
                "match": candidate_keys.get(key, "identity details"),
            }
    return None


def duplicate_client_response(duplicate: Dict[str, Any], tenant_id: str):
    return jsonify({
        "success": False,
        "error": f"Duplicate client blocked in this tenant. A matching client already exists: {duplicate.get('fullName')}.",
        "code": "DUPLICATE_CLIENT_IN_TENANT",
        "tenantId": tenant_id,
        "duplicate": duplicate,
        "duplicatesAllowedAcrossTenants": True,
    }), 409


@app.before_request
def require_authenticated_api_session():
    if request.method == "OPTIONS":
        return None
    if not request.path.startswith("/api/"):
        return None
    if request.path in {"/api/health", "/api/auth/login"}:
        return None
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = (request.headers.get("Origin") or "").rstrip("/")
        if origin:
            origin_host = origin.split("://", 1)[-1].split("/", 1)[0].lower()
            allowed = {item.rstrip("/").lower() for item in ALLOWED_ORIGINS}
            same_host = origin_host == request.host.lower()
            if not same_host and origin.lower() not in allowed:
                return jsonify({"success": False, "error": "Request origin is not allowed."}), 403
    db = load_db()
    if prune_sessions(db):
        save_db(db)
    authenticated = authenticated_session(db)
    if not authenticated:
        return jsonify({"success": False, "error": "Authentication required. Sign in with your email address and password."}), 401
    session, tenant, user = authenticated
    g.current_session = session
    g.current_user = user
    g.current_tenant = tenant
    g.current_tenant_id = session.get("tenantId")
    return None

@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"success": True, "app": APP_NAME, "version": APP_VERSION, "isolation": "authenticated tenant session"})


@app.get("/health")
@app.get("/api/health")
def health():
    db = load_db()
    return jsonify({"success": True, "status": "ok", "version": APP_VERSION, "ocrAvailable": tesseract_is_available(), "ownerPasswordConfigured": bool(OWNER_PASSWORD), "ownerPasswordValid": validate_password(OWNER_PASSWORD) is None if OWNER_PASSWORD else False, "secureAuthentication": True})




def require_platform_owner():
    user = getattr(g, "current_user", None)
    if not user or not user.get("isPlatformOwner") or clean_spaces(user.get("email", "")).lower() != OWNER_EMAIL:
        return jsonify({"success": False, "error": "Only Yunoos Daniels, the Fin-Tastic platform owner, may create tenants or users."}), 403
    return None


@app.route("/api/tenants", methods=["GET", "POST"])
def tenants():
    db = load_db()
    if request.method == "GET":
        if getattr(g, "current_user", {}).get("isPlatformOwner"):
            summaries = public_tenant_summary(db)
        else:
            own_tenant = db.get("tenants", {}).get(str(getattr(g, "current_tenant_id", "")))
            summaries = [] if own_tenant is None else [{
                "id": own_tenant.get("id"),
                "name": own_tenant.get("name"),
                "ncr": own_tenant.get("ncr"),
                "userCount": len(own_tenant.get("users", [])),
                "clientCount": len(own_tenant.get("clients", [])),
            }]
        return jsonify({"success": True, "tenants": summaries})

    owner_error = require_platform_owner()
    if owner_error:
        return owner_error

    payload = request_json()
    name = clean_spaces(payload.get("name") or payload.get("companyName") or "")
    ncr = clean_spaces(payload.get("ncr") or payload.get("ncrNumber") or "")
    admin_name = clean_spaces(payload.get("adminName") or "Tenant Admin")
    admin_email = clean_spaces(payload.get("adminEmail") or payload.get("email") or "").lower()
    admin_password = str(payload.get("adminPassword") or payload.get("password") or "")
    if not name or not admin_name or not admin_email:
        return jsonify({"success": False, "error": "Tenant name, administrator name and administrator email are required."}), 400
    if not valid_email(admin_email):
        return jsonify({"success": False, "error": "Enter a valid administrator email address."}), 400
    password_error = validate_password(admin_password)
    if password_error:
        return jsonify({"success": False, "error": password_error}), 400
    if email_in_use(db, admin_email):
        return jsonify({"success": False, "error": "That email address is already used by another Fin-Tastic login."}), 409

    base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tenant"
    tenant_id = base_slug
    counter = 2
    while tenant_id in db.setdefault("tenants", {}):
        tenant_id = f"{base_slug}-{counter}"
        counter += 1

    admin_user = {
        "id": new_id("user"),
        "name": admin_name,
        "role": "Admin",
        "email": admin_email,
        "passwordHash": generate_password_hash(admin_password),
        "isActive": True,
        "isPlatformOwner": False,
        "createdAt": now_iso(),
        "createdBy": getattr(g, "current_user", {}).get("id"),
    }
    db["tenants"][tenant_id] = {
        "id": tenant_id,
        "name": name,
        "ncr": ncr,
        "users": [admin_user],
        "clients": [],
        "uploads": [],
        "createdAt": now_iso(),
        "createdBy": getattr(g, "current_user", {}).get("id"),
    }
    save_db(db)
    return jsonify({
        "success": True,
        "tenant": {"id": tenant_id, "name": name, "ncr": ncr, "userCount": 1, "clientCount": 0},
        "user": public_user(admin_user),
        "tenants": public_tenant_summary(db),
    }), 201


@app.route("/api/users", methods=["GET", "POST"])
def users():
    db = load_db()
    tenant_id, tenant = get_tenant(db)
    if not tenant:
        return tenant_error(tenant_id)
    if request.method == "GET":
        return jsonify({"success": True, "tenantId": tenant_id, "users": [public_user(user) for user in tenant.get("users", [])]})

    owner_error = require_platform_owner()
    if owner_error:
        return owner_error
    payload = request_json()
    name = clean_spaces(payload.get("name") or "")
    email = clean_spaces(payload.get("email") or "").lower()
    password = str(payload.get("password") or "")
    role = clean_spaces(payload.get("role") or "Consultant")
    if role not in {"Admin", "Manager", "Consultant"}:
        return jsonify({"success": False, "error": "Role must be Admin, Manager or Consultant."}), 400
    if not name or not email:
        return jsonify({"success": False, "error": "User name and email are required."}), 400
    if not valid_email(email):
        return jsonify({"success": False, "error": "Enter a valid user email address."}), 400
    password_error = validate_password(password)
    if password_error:
        return jsonify({"success": False, "error": password_error}), 400
    existing_tenant_id, _existing_tenant, existing_user = find_user_by_email(db, email)
    if existing_user:
        legacy_inactive = existing_tenant_id == tenant_id and (not existing_user.get("isActive") or not existing_user.get("passwordHash"))
        if not legacy_inactive:
            return jsonify({"success": False, "error": "That email address is already used by another Fin-Tastic login."}), 409
        existing_user.update({
            "name": name,
            "role": role,
            "passwordHash": generate_password_hash(password),
            "isActive": True,
            "isPlatformOwner": False,
            "passwordSetAt": now_iso(),
            "updatedAt": now_iso(),
            "updatedBy": getattr(g, "current_user", {}).get("id"),
        })
        user = existing_user
        status_code = 200
        activated_legacy_user = True
    else:
        user = {
            "id": new_id("user"),
            "name": name,
            "role": role,
            "email": email,
            "passwordHash": generate_password_hash(password),
            "isActive": True,
            "isPlatformOwner": False,
            "createdAt": now_iso(),
            "createdBy": getattr(g, "current_user", {}).get("id"),
        }
        tenant.setdefault("users", []).append(user)
        status_code = 201
        activated_legacy_user = False
    save_db(db)
    return jsonify({"success": True, "tenantId": tenant_id, "user": public_user(user), "activatedLegacyUser": activated_legacy_user, "users": [public_user(item) for item in tenant.get("users", [])]}), status_code


@app.post("/api/auth/login")
def auth_login():
    db = load_db()
    payload = request_json()
    email = clean_spaces(payload.get("email") or "").lower()
    password = str(payload.get("password") or "")
    attempt_key = f"{request.remote_addr or 'unknown'}:{email}"
    now = datetime.now(timezone.utc)
    recent = [stamp for stamp in _LOGIN_ATTEMPTS.get(attempt_key, []) if stamp > now - timedelta(minutes=15)]
    _LOGIN_ATTEMPTS[attempt_key] = recent
    if len(recent) >= 5:
        return jsonify({"success": False, "error": "Too many failed sign-in attempts. Try again in 15 minutes."}), 429

    tenant_id, tenant, user = find_user_by_email(db, email)
    owner_login = bool(user and user.get("isPlatformOwner"))
    owner_password_valid = bool(
        owner_login
        and OWNER_PASSWORD
        and validate_password(OWNER_PASSWORD) is None
        and secrets.compare_digest(password, OWNER_PASSWORD)
    )
    stored_password_valid = bool(
        user
        and user.get("passwordHash")
        and check_password_hash(str(user.get("passwordHash")), password)
    )
    valid = bool(user and user.get("isActive") and (owner_password_valid or stored_password_valid))
    if not valid:
        recent.append(now)
        _LOGIN_ATTEMPTS[attempt_key] = recent
        return jsonify({"success": False, "error": "Incorrect email address or password."}), 401

    _LOGIN_ATTEMPTS.pop(attempt_key, None)
    if owner_password_valid:
        user["passwordHash"] = generate_password_hash(OWNER_PASSWORD)
        user["passwordSetAt"] = now_iso()
    prune_sessions(db)
    token = create_auth_session(db, tenant_id, user)
    user["lastLoginAt"] = now_iso()
    save_db(db)
    response = make_response(jsonify({
        "success": True,
        "tenant": {"id": tenant_id, "name": tenant.get("name"), "ncr": tenant.get("ncr")},
        "user": public_user(user),
        "session": {"tenantId": tenant_id, "role": user.get("role"), "expiresInHours": SESSION_HOURS},
    }))
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/auth/logout")
def auth_logout():
    db = load_db()
    token = _session_token_from_request()
    if token:
        db.setdefault("sessions", {}).pop(_session_hash(token), None)
        save_db(db)
    response = make_response(jsonify({"success": True}))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=COOKIE_SECURE, httponly=True, samesite="Lax")
    return response


@app.get("/api/me")
def me():
    tenant_id = str(getattr(g, "current_tenant_id", ""))
    tenant = getattr(g, "current_tenant", None)
    user = getattr(g, "current_user", None)
    return jsonify({
        "success": True,
        "tenant": {"id": tenant_id, "name": (tenant or {}).get("name"), "ncr": (tenant or {}).get("ncr")},
        "user": public_user(user or {}),
    })


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
    duplicate = find_duplicate_client(tenant, client)
    if duplicate:
        return duplicate_client_response(duplicate, tenant_id)
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
    duplicate = find_duplicate_client(tenant, updated, exclude_client_id=client_id)
    if duplicate:
        return duplicate_client_response(duplicate, tenant_id)
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
        candidate = deepcopy(existing)
        candidate.update(payload_client)
        candidate["accounts"] = accounts
        candidate["coach"] = evaluate_sales(candidate, accounts)
        candidate["serviceType"] = candidate["coach"]["service"]
        candidate["status"] = "Credit Report Uploaded"
        ensure_client_workflow(candidate)
        candidate["updatedAt"] = now_iso()
        duplicate = find_duplicate_client(tenant, candidate, exclude_client_id=existing.get("id", ""))
        if duplicate:
            saved_path.unlink(missing_ok=True)
            return duplicate_client_response(duplicate, tenant_id)
        existing.clear()
        existing.update(candidate)
        client = existing
    else:
        client = make_client(tenant_id, payload_client.get("fullName") or "New Parsed Client", user_id)
        client.update(payload_client)
        client["accounts"] = accounts
        client["coach"] = evaluate_sales(client, accounts)
        client["serviceType"] = client["coach"]["service"]
        client["status"] = "Credit Report Uploaded"
        ensure_client_workflow(client)
        duplicate = find_duplicate_client(tenant, client)
        if duplicate:
            saved_path.unlink(missing_ok=True)
            return duplicate_client_response(duplicate, tenant_id)
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
    owner_error = require_platform_owner()
    if owner_error:
        return owner_error
    routes = sorted(str(rule) for rule in app.url_map.iter_rules())
    return jsonify({"success": True, "routes": routes, "note": "Authenticated sessions enforce tenant isolation. Only the platform owner may create tenants or users."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
