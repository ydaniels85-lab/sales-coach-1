from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pdfplumber
from pypdf import PdfReader

try:
    import pypdfium2 as pdfium
except Exception:  # pragma: no cover
    pdfium = None

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None


class PdfPasswordRequired(Exception):
    """Raised when an encrypted PDF needs a password."""

    def __init__(self, invalid_password: bool = False):
        super().__init__("The PDF is password protected.")
        self.invalid_password = invalid_password


class UnsupportedReport(Exception):
    pass


@dataclass
class PdfTextResult:
    text: str
    page_texts: List[str]
    encrypted: bool
    used_default_password: bool
    used_ocr: bool


def clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def money(value: Any) -> float:
    if value is None:
        return 0.0
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    try:
        return float(cleaned) if cleaned not in {"", ".", "-"} else 0.0
    except ValueError:
        return 0.0


def suggested_reduced_amount(balance: float, installment: float) -> float:
    if balance <= 0 and installment <= 0:
        return 0.0
    candidate = max(100.0, balance * 0.015, installment * 0.65 if installment > 0 else 0.0)
    if installment > 0:
        candidate = min(candidate, installment)
    return round(candidate / 10.0) * 10.0


def _decrypt_check(data: bytes, supplied_password: Optional[str], use_default_password: bool) -> Tuple[bool, Optional[str], bool]:
    reader = PdfReader(io.BytesIO(data))
    if not reader.is_encrypted:
        return False, None, False

    candidates: List[Tuple[str, bool]] = []
    if supplied_password:
        candidates.append((supplied_password, False))
    if use_default_password:
        default_password = os.getenv("DEFAULT_CREDIT_REPORT_PDF_PASSWORD", "")
        if default_password and default_password != supplied_password:
            candidates.append((default_password, True))

    if not candidates:
        raise PdfPasswordRequired(invalid_password=False)

    for candidate, is_default in candidates:
        try:
            test_reader = PdfReader(io.BytesIO(data))
            result = test_reader.decrypt(candidate)
            if result:
                _ = len(test_reader.pages)
                return True, candidate, is_default
        except Exception:
            continue
    raise PdfPasswordRequired(invalid_password=True)


def _ocr_pages(data: bytes, password: Optional[str]) -> List[str]:
    if pdfium is None or pytesseract is None:
        return []
    try:
        document = pdfium.PdfDocument(data, password=password or None)
    except Exception:
        return []
    pages: List[str] = []
    for index in range(len(document)):
        try:
            bitmap = document[index].render(scale=2.2)
            image = bitmap.to_pil()
            pages.append(pytesseract.image_to_string(image, config="--psm 6"))
        except Exception:
            pages.append("")
    return pages


def extract_pdf_text(data: bytes, supplied_password: Optional[str] = None, use_default_password: bool = False) -> PdfTextResult:
    encrypted, actual_password, used_default = _decrypt_check(data, supplied_password, use_default_password)
    page_texts: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data), password=actual_password) as pdf:
            for page in pdf.pages:
                page_texts.append(page.extract_text(x_tolerance=2, y_tolerance=3) or "")
    except Exception as exc:
        if encrypted:
            raise PdfPasswordRequired(invalid_password=True) from exc
        raise

    text = "\n".join(page_texts)
    used_ocr = False
    if len(re.sub(r"\s+", "", text)) < 80:
        ocr_pages = _ocr_pages(data, actual_password)
        ocr_text = "\n".join(ocr_pages)
        if len(re.sub(r"\s+", "", ocr_text)) > len(re.sub(r"\s+", "", text)):
            page_texts = ocr_pages
            text = ocr_text
            used_ocr = True

    return PdfTextResult(text=text, page_texts=page_texts, encrypted=encrypted, used_default_password=used_default, used_ocr=used_ocr)


def _first(patterns: Iterable[str], text: str, flags: int = re.I | re.M, default: str = "") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return clean_spaces(match.group(1))
    return default


def _section(text: str, start: str, end_markers: Iterable[str]) -> str:
    match = re.search(re.escape(start), text, re.I)
    if not match:
        return ""
    rest = text[match.end():]
    positions = []
    for marker in end_markers:
        found = re.search(re.escape(marker), rest, re.I)
        if found:
            positions.append(found.start())
    return rest[: min(positions)] if positions else rest


def _parse_identity(text: str) -> Dict[str, Any]:
    first_name = _first([r"First Name:\s*([^\n]*?)(?=Residential Address:|\s+Residential Address:|$)"], text)
    second_name = _first([r"Second Name:\s*([^\n]*?)(?=Postal Address:|\s+Postal Address:|$)"], text)
    surname = _first([r"Surname:\s*([^\n]*?)(?=Home Telephone No:|\s+Home Telephone No:|$)"], text)
    full_name = clean_spaces(" ".join(part for part in [first_name, second_name, surname] if part))
    address = _first([
        r"Residential Address:\s*(.*?)(?=\nSecond Name:)",
        r"Residential Address:\s*(.*?)(?=\nPostal Address:)",
    ], text, flags=re.I | re.S)
    return {
        "firstName": first_name.title(),
        "secondName": second_name.title(),
        "surname": surname.title(),
        "fullName": full_name.title(),
        "idNumber": _first([r"ID Number:\s*(\d{13})", r"Client Reference:\s*(\d{13})"], text),
        "dateOfBirth": _first([r"Birth Date:\s*(\d{4}-\d{2}-\d{2})"], text),
        "gender": _first([r"Gender:\s*([^\n]+?)(?=\s+Email Address:|$)"], text),
        "maritalStatus": _first([r"Marital Status:\s*([^\n]+)"], text),
        "email": _first([r"Email Address:\s*([^\s\n]+@[^\s\n]+)"], text),
        "phone": _first([r"Cellular No:\s*([0-9 +()-]{7,})", r"Home Telephone No:\s*([0-9 +()-]{7,})"], text),
        "whatsapp": _first([r"Cellular No:\s*([0-9 +()-]{7,})"], text),
        "physicalAddress": address,
        "employer": _first([r"Employer Details:\s*([^\n]+)"], text),
        "occupation": "",
        "dateEmployed": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
    }


def _parse_score(text: str) -> Tuple[Optional[int], bool, str]:
    score_section = _section(text, "Score Date", ["Debt Summary"])
    match = re.search(r"\b(\d{3})\s*$", score_section, re.M)
    if not match:
        match = re.search(r"Potential\s+(?:High|Medium|Low)\s+Risk\s+(\d{3})", score_section, re.I)
    score = int(match.group(1)) if match else None
    risk = _first([r"\d{4}-\d{2}-\d{2}\s+([^\n]+?)\s+\d{3}\s*$"], score_section)
    return score, score is not None, risk


def _parse_summary(text: str) -> Dict[str, Any]:
    summary = _section(text, "Debt Summary", ["Consumer Account Status"])

    def total(label: str) -> float:
        line = _first([rf"{re.escape(label)}\s+([^\n]+)"], summary)
        values = re.findall(r"R?\s*([0-9][0-9,]*(?:\.\d+)?)", line)
        return money(values[-1]) if values else 0.0

    return {
        "activeAccounts": int(total("Total Number Of Active Accounts")),
        "accountsGoodStanding": int(total("Total Number Of Accounts In Good Standing")),
        "accountsInArrears": int(total("Total Number Of Accounts In Arrears")),
        "paidOrClosed": int(total("Total Number Of Paid Up or Closed Accounts (last 24 months)")),
        "monthlyInstallments": total("Total Monthly Instalments"),
        "outstandingDebt": total("Total Outstanding Debt"),
        "arrearsAmount": total("Total Arrears Amount"),
        "highestMonthsInArrears": int(total("Highest Months in Arrears (Last 24 Months)")),
    }


def _account_blocks(section_text: str) -> List[str]:
    starts = list(re.finditer(r"(?m)^Account:\s*\d+\s*$", section_text))
    blocks: List[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(section_text)
        blocks.append(section_text[start.start():end])
    return blocks


def _history_max(text: str, creditor_name: str) -> int:
    if not creditor_name:
        return 0
    occurrence = re.search(rf"(?mi)^{re.escape(creditor_name)}\s*$", text)
    if not occurrence:
        return 0
    tail = text[occurrence.end(): occurrence.end() + 1200]
    stop = re.search(r"(?m)^(?:Consumer|Account:|[A-Z][A-Za-z0-9 &.'()/-]{2,})\s*$", tail[50:])
    if stop:
        tail = tail[: 50 + stop.start()]
    numeric_codes = [int(value) for value in re.findall(r"(?<!\d)([1-9])(?!\d)", tail)]
    return max(numeric_codes, default=0)


def _parse_account(block: str, source: str, full_text: str, index: int) -> Optional[Dict[str, Any]]:
    creditor = _first([r"Subscriber Name:\s*(.*?)\s+Account No:"], block, flags=re.I | re.S)
    account_no = _first([r"Account No:\s*([^\n]+)"], block)
    if not creditor:
        return None
    current = money(_first([r"Current Balance:\s*R?\s*([0-9,.-]+)"], block))
    installment = money(_first([r"Instalment Amount:\s*R?\s*([0-9,.-]+)"], block))
    arrears = money(_first([r"Arrears Amount:\s*R?\s*([0-9,.-]+)"], block))
    opening = money(_first([r"Open Balance / Credit Limit:\s*R?\s*([0-9,.-]+)"], block))
    account_type = _first([r"Type of Account:\s*(.*?)(?=\nLast Paid Date:|\nAccount Status:|$)"], block, flags=re.I | re.S)
    last_paid = _first([r"Last Paid Date:\s*(\d{4}-\d{2}-\d{2})"], block)
    opened = _first([r"Date Account Opened:\s*(\d{4}-\d{2}-\d{2})"], block)
    status = _first([r"Account Status:\s*([^\n]+)"], block)
    if not status:
        status = "In Arrears" if arrears > 0 else "Active"
    haystack = f"{creditor} {account_type}".lower()
    furniture = any(word in haystack for word in ["lewis", "russells", "bradlows", "furniture", "beares", "rochester", "house & home"])
    asset = any(word in haystack for word in ["home loan", "mortgage", "bond", "vehicle finance", "motor finance", "wesbank", "mfc", "toyota financial", "vw financial"])
    return {
        "id": f"{source.lower()}-{index}",
        "creditorName": creditor,
        "accountNumber": account_no,
        "accountType": account_type,
        "openingBalance": opening,
        "currentBalance": current,
        "arrears": arrears,
        "monthlyInstallment": installment,
        "reducedAmount": suggested_reduced_amount(current, installment),
        "lastPaidDate": last_paid,
        "monthsInArrears": _history_max(full_text, creditor),
        "openDate": opened,
        "status": status,
        "included": status.lower() not in {"closed", "paid up"} and not (current == 0 and installment == 0),
        "isFurniture": furniture,
        "isAsset": asset,
        "parserSource": source,
    }


def _parse_accounts(text: str) -> List[Dict[str, Any]]:
    cpa = _section(text, "Consumer Account Status", ["Consumer 24 Monthly Payment History", "Consumer NLR Account Status"])
    nlr = _section(text, "Consumer NLR Account Status", ["Consumer NLR 24 Monthly Payment History", "Consumer Properties"])
    accounts: List[Dict[str, Any]] = []
    for source, section_text in [("CPA", cpa), ("NLR", nlr)]:
        for block in _account_blocks(section_text):
            account = _parse_account(block, source, text, len(accounts) + 1)
            if account:
                accounts.append(account)
    return accounts


def _debt_review_flag(text: str) -> Tuple[bool, str]:
    section = _section(text, "Debt Review", ["Adverse Information", "Judgements", "Admin Orders"])
    if not section:
        summary_section = _section(text, "Debt Review Status", ["Dispute Message", "Consumer Account Status"])
        section = summary_section
    normalized = clean_spaces(section)
    if not normalized or re.search(r"No Results Found", normalized, re.I):
        return False, normalized
    listed = bool(re.search(r"under debt review|debt review listed|17\.1|17\.2|NCRDC", normalized, re.I))
    return listed, normalized


def build_sales_coach(identity: Dict[str, Any], score: Optional[int], score_found: bool, debt_review: bool, accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    included = [account for account in accounts if account.get("included", True)]
    outstanding = sum(money(account.get("currentBalance")) for account in included)
    arrears = sum(money(account.get("arrears")) for account in included)
    original = sum(money(account.get("monthlyInstallment")) for account in included)
    reduced = sum(money(account.get("reducedAmount")) for account in included)
    has_asset = any(bool(account.get("isAsset")) for account in included)
    has_furniture = any(bool(account.get("isFurniture")) for account in included)
    low_installment_cpi = bool(not debt_review and original > 0 and original < 1000)
    pricing: Optional[Dict[str, Any]] = None

    if debt_review:
        service = "Debt Review Removal"
        urgency = "High"
        headline = "Debt-review listing detected"
        reasons = [
            "The report contains a confirmed debt-review indicator. Verify the legal stage before offering removal."
        ]
        opening_script = (
            "Your credit report confirms a debt-review indicator. Before discussing removal, let us verify the legal stage, "
            "the outstanding balances and the documents required for a compliant assessment."
        )
        qualifying_questions = [
            "Do you know whether Form 17.2 was issued?",
            "Are all debt-review accounts paid up or do balances remain?",
            "Have you received a clearance certificate or court order?",
        ]
        if outstanding > 0:
            reasons.append(
                "Active balances remain, so assess a second Debt Mediation service after the removal route is confirmed."
            )
    elif low_installment_cpi:
        service = "Credit Profile Investigation"
        urgency = "Medium"
        headline = "Potential Credit Profile Investigation sale"
        reasons = [
            f"The client is not confirmed under debt review and the total included monthly instalments are R{original:,.2f}, which is below R1,000 per month.",
            "A full debt-restructuring route may not be the best first fit; investigate the credit profile, listings, enquiries and possible reporting exceptions first.",
        ]
        opening_script = (
            "Your report does not confirm debt review and your listed monthly commitments are below R1,000. "
            "A Credit Profile Investigation may be a better first step to identify inaccurate, outdated or unfamiliar information before choosing a larger debt service."
        )
        qualifying_questions = [
            "Have you recently been declined for credit, housing or employment screening?",
            "Do you see any account, enquiry, address or status that you do not recognise?",
            "Are any paid-up or settled accounts still showing incorrectly?",
            "Have you previously lodged a bureau dispute or requested your supporting records?",
        ]
        pricing = {
            "currency": "ZAR",
            "onceOff": 3000,
            "description": "R3,000 once-off, payable immediately or split over 2, 3 or 4 months.",
            "paymentPlans": [
                {"months": 1, "label": "Once-off", "monthlyAmount": 3000},
                {"months": 2, "label": "2 months", "monthlyAmount": 1500},
                {"months": 3, "label": "3 months", "monthlyAmount": 1000},
                {"months": 4, "label": "4 months", "monthlyAmount": 750},
            ],
        }
    elif has_asset:
        service = "Debt Review"
        urgency = "High"
        headline = "Asset-protection opportunity"
        reasons = [
            "A home-loan or vehicle-finance account was detected. Lead with affordability and protection of the asset, subject to eligibility and compliance."
        ]
        opening_script = (
            "Your report shows a financed asset. Let us first complete an affordability assessment so we can determine whether Debt Review is appropriate and explain the process without making unsupported promises."
        )
        qualifying_questions = [
            "Are the home-loan or vehicle instalments currently up to date?",
            "Have you received a demand, summons, cancellation or repossession warning?",
            "What is your verified net income and essential monthly household budget?",
        ]
    elif outstanding > 0:
        service = "Debt Mediation"
        urgency = "High" if arrears > 0 else "Medium"
        headline = "Debt mediation opportunity"
        reasons = [
            "The report shows active outstanding debt that can be assessed for a sustainable repayment arrangement."
        ]
        opening_script = (
            "Your report shows active balances without a confirmed debt-review listing. Let us verify your affordability and account information to assess a realistic mediation proposal."
        )
        qualifying_questions = [
            "Which accounts are causing the most monthly pressure?",
            "What amounts are currently being paid and on which dates?",
            "Has any creditor started legal collection or handed the account over?",
        ]
    else:
        service = "Needs Manual Review"
        urgency = "Low"
        headline = "Manual review required"
        reasons = ["No safe automatic service route was identified from the available report data."]
        opening_script = (
            "The report does not provide enough information for a safe automatic recommendation. Let us verify the client's objective and supporting documents before selecting a service."
        )
        qualifying_questions = [
            "What result is the client trying to achieve?",
            "Has the client received any recent decline, legal or bureau notice?",
            "Which supporting documents are available?",
        ]

    if score_found and score == 0 and not debt_review:
        reasons.append(
            "A score of zero alone did not trigger Debt Review Removal because the report does not confirm a debt-review listing."
        )
    if arrears > 0:
        reasons.append(f"The included accounts show R{arrears:,.2f} in arrears.")
    if has_furniture:
        reasons.append("Furniture debt is present and should be clearly tagged during the client discussion.")

    next_steps = [
        "Confirm the client's contact details, application type, employment, income and household budget.",
        "Capture and verify banking details before sending any mandate or debit-order instruction.",
        "Review every included account and correct any source-data exceptions.",
        "Collect ID, proof of address, payslip and bank statements before handover.",
    ]
    if low_installment_cpi:
        next_steps = [
            "Confirm that the report does not contain a debt-review indicator.",
            "Review adverse listings, enquiries, addresses, paid-up accounts and unfamiliar information with the client.",
            "Explain the R3,000 fee and select once-off, 2-, 3- or 4-month payment terms.",
            "Obtain the client's consent and supporting documents before starting the investigation.",
        ]

    return {
        "service": service,
        "urgency": urgency,
        "headline": headline,
        "reasons": reasons,
        "openingScript": opening_script,
        "qualifyingQuestions": qualifying_questions,
        "nextSteps": next_steps,
        "objectionHandlers": [
            "Use the report figures to explain the current position instead of making unsupported promises.",
            "Confirm that final eligibility, outcomes and legal steps depend on verified documents and status checks.",
            "Explain the service scope and fee clearly before collecting a mandate or payment instruction.",
        ],
        "pricing": pricing,
        "totals": {
            "outstanding": round(outstanding, 2),
            "arrears": round(arrears, 2),
            "originalInstalment": round(original, 2),
            "reducedInstalment": round(reduced, 2),
            "estimatedRelief": round(max(0.0, original - reduced), 2),
        },
        "flags": {
            "debtReviewListed": debt_review,
            "hasAsset": has_asset,
            "hasFurniture": has_furniture,
            "scoreZeroRule": bool(score_found and score == 0),
            "doubleSaleCandidate": bool(debt_review and outstanding > 0),
            "creditProfileInvestigationCandidate": low_installment_cpi,
        },
    }


def parse_datanamix(text: str, filename: str = "") -> Dict[str, Any]:
    if "DATANAMIX" not in text.upper() and "Datanamix Consumer Credit Report" not in text:
        raise UnsupportedReport("This parser build currently recognises the supplied Datanamix report layout.")

    identity = _parse_identity(text)
    score, score_found, risk = _parse_score(text)
    accounts = _parse_accounts(text)
    debt_review, debt_review_detail = _debt_review_flag(text)
    summary = _parse_summary(text)
    report_reference = _first([r"Report Reference:\s*([^\n]+)"], text)
    client_reference = _first([r"Client Reference:\s*([^\n]+)"], text)
    search_date = _first([r"Search Date:\s*([^\n]+)"], text)

    warnings: List[str] = []
    if not identity["fullName"]:
        warnings.append("Client name was not confidently detected.")
    if not identity["idNumber"]:
        warnings.append("Client ID number was not confidently detected.")
    if not accounts:
        warnings.append("No account rows were detected.")
    if summary.get("activeAccounts") and len([a for a in accounts if a["included"]]) != summary["activeAccounts"]:
        warnings.append("The report summary and parsed active-account count differ. Review sold, closed and zero-balance accounts manually.")

    confidence_points = 20
    confidence_points += 20 if identity["fullName"] else 0
    confidence_points += 20 if identity["idNumber"] else 0
    confidence_points += 15 if score_found else 0
    confidence_points += min(25, len(accounts) * 4)
    confidence = min(100, confidence_points)

    coach = build_sales_coach(identity, score, score_found, debt_review, accounts)
    client = {
        **identity,
        "applicationType": "Single",
        "spouse": {},
        "bank": {},
        "creditScore": score,
        "scoreFound": score_found,
        "riskCategory": risk,
        "debtReviewListed": debt_review,
        "debtReviewDetail": debt_review_detail,
        "status": "Credit Report Parsed",
        "serviceType": coach["service"],
        "accounts": accounts,
        "coach": coach,
        "report": {
            "filename": filename,
            "bureau": "Datanamix",
            "reportReference": report_reference,
            "clientReference": client_reference,
            "searchDate": search_date,
            "summary": summary,
        },
    }
    return {
        "success": True,
        "bureau": "Datanamix",
        "confidence": confidence,
        "filename": filename,
        "warnings": warnings,
        "client": client,
        "accounts": accounts,
        "coach": coach,
    }


def parse_credit_report(data: bytes, filename: str, supplied_password: Optional[str] = None, use_default_password: bool = False) -> Dict[str, Any]:
    extracted = extract_pdf_text(data, supplied_password=supplied_password, use_default_password=use_default_password)
    parsed = parse_datanamix(extracted.text, filename=filename)
    parsed["pdf"] = {
        "encrypted": extracted.encrypted,
        "usedDefaultPassword": extracted.used_default_password,
        "usedOcr": extracted.used_ocr,
        "pageCount": len(extracted.page_texts),
    }
    return parsed
