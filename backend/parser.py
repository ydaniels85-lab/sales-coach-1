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


def _score_section(text: str) -> str:
    """Return the narrowest likely score block without including debt totals."""
    for start in (
        "Consumer Score Information",
        "Credit Score Information",
        "Consumer Credit Score",
        "Score Date",
    ):
        section = _section(
            text,
            start,
            [
                "Debt Summary",
                "Consumer Account Status",
                "Account Summary",
                "Adverse Information",
            ],
        )
        if section:
            return section
    return text


def _looks_like_score_scale(line: str) -> bool:
    values = [int(value) for value in re.findall(r"(?<!\d)(\d{2,4})(?!\d)", line)]
    plausible = [value for value in values if 300 <= value <= 1000]
    return len(plausible) >= 4 and plausible == sorted(plausible)


def _parse_score(text: str) -> Dict[str, Any]:
    """
    Extract a credit score using labelled candidates instead of accepting the first
    three-digit number in the score area. This avoids confusing score-band markers,
    dates, account counts and balances with the client's final score.
    """
    section = _score_section(text)
    candidates: List[Dict[str, Any]] = []
    seen: set[Tuple[int, str, str]] = set()

    def add(value: Any, confidence: int, source: str, context: str) -> None:
        try:
            score = int(str(value).strip())
        except (TypeError, ValueError):
            return
        if not 0 <= score <= 999:
            return
        context_clean = clean_spaces(context)[:240]
        if _looks_like_score_scale(context_clean):
            return
        key = (score, source, context_clean)
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            {
                "score": score,
                "confidence": max(0, min(100, int(confidence))),
                "source": source,
                "context": context_clean,
            }
        )

    direct_patterns = [
        (
            r"(?im)\bFinal\s+Score\b[ \t]*(?:is|:|=|-)?[ \t]*(\d{1,3})\b",
            100,
            "Final Score label",
        ),
        (
            r"(?im)\b(?:Credit|Consumer|Bureau|Risk|TransUnion|Experian|XDS|Compuscan)\s+Score\b"
            r"[ \t]*(?:is|:|=|-)?[ \t]*(\d{1,3})\b",
            98,
            "Credit Score label",
        ),
        (
            r"(?im)\bYour\s+(?:credit\s+)?score\s+is\s+(\d{1,3})\b",
            98,
            "Score statement",
        ),
        (
            r"(?im)(\d{1,3})[ \t]*\b(?:Final|Credit|Consumer)\s+Score\b",
            94,
            "Value before score label",
        ),
    ]
    for pattern, confidence, source in direct_patterns:
        for match in re.finditer(pattern, section):
            add(match.group(1), confidence, source, match.group(0))

    lines = [clean_spaces(line) for line in section.splitlines() if clean_spaces(line)]
    for index, line in enumerate(lines):
        if not re.search(r"\bFinal\s+Score\b", line, re.I):
            continue

        window = lines[index + 1:index + 8]
        usable_window: List[str] = []
        for row in window:
            if re.search(r"\bDebt\s+Summary\b", row, re.I):
                break
            if _looks_like_score_scale(row):
                continue
            usable_window.append(row)

        # Prefer a row that contains both the risk category and its final value.
        for row in usable_window:
            match = re.search(
                r"\b(?:Potential\s+)?(?:Very\s+)?(?:High|Medium|Low)\s+Risk\s+(\d{1,3})\b",
                row,
                re.I,
            )
            if match:
                add(match.group(1), 99, "Final Score table row", f"{line} | {row}")

        # Some PDF extractors place the risk category and score on separate lines.
        for row_index, row in enumerate(usable_window[:-1]):
            if not re.search(r"\b(?:Potential\s+)?(?:Very\s+)?(?:High|Medium|Low)\s+Risk\b", row, re.I):
                continue
            next_row = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", usable_window[row_index + 1])
            numbers = [
                int(value)
                for value in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", next_row)
                if 0 <= int(value) <= 999
            ]
            if len(numbers) == 1:
                add(numbers[0], 98, "Final Score table split row", f"{line} | {row} | {usable_window[row_index + 1]}")

        # Last-resort table candidate: use the last plausible value in the table
        # window, not the first. This avoids treating an exception code as the score.
        table_values: List[Tuple[int, str]] = []
        for row in usable_window:
            if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", row):
                continue
            row_without_dates = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", row)
            numbers = [
                int(value)
                for value in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", row_without_dates)
                if 0 <= int(value) <= 999
            ]
            for number in numbers:
                table_values.append((number, row))
        if table_values:
            value, source_row = table_values[-1]
            add(value, 86, "Final Score table fallback", f"{line} | {source_row}")

    dated_risk_pattern = re.compile(
        r"(?im)^\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+"
        r"(?P<risk>.*?\bRisk)\s+(?P<score>\d{1,3})\s*$"
    )
    for match in dated_risk_pattern.finditer(section):
        add(match.group("score"), 97, "Dated risk row", match.group(0))

    for match in re.finditer(
        r"(?im)\b(?:Potential\s+)?(?:Very\s+)?(?:High|Medium|Low)\s+Risk\s+(\d{1,3})\b",
        section,
    ):
        add(match.group(1), 94, "Risk category row", match.group(0))

    for line in lines:
        if not re.search(r"\b(score|risk)\b", line, re.I) or _looks_like_score_scale(line):
            continue
        line_without_dates = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", line)
        numbers = [
            int(value)
            for value in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", line_without_dates)
            if 0 <= int(value) <= 999
        ]
        if len(numbers) == 1:
            add(numbers[0], 78, "Score-section fallback", line)

    candidates.sort(key=lambda item: -item["confidence"])
    winner = candidates[0] if candidates else None

    risk = _first(
        [
            r"Risk\s+Category\s*(?:is|:|=|-)\s*([^\n]+)",
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+(.*?\bRisk)\s+\d{1,3}\s*$",
            r"\b((?:Potential\s+)?(?:Very\s+)?(?:High|Medium|Low)\s+Risk)\b",
        ],
        section,
    )
    if not risk and winner:
        risk_match = re.search(
            r"\b((?:Potential\s+)?(?:Very\s+)?(?:High|Medium|Low)\s+Risk)\b",
            winner["context"],
            re.I,
        )
        if risk_match:
            risk = clean_spaces(risk_match.group(1))

    conflicting = False
    if winner:
        competing = [
            item
            for item in candidates[1:]
            if item["score"] != winner["score"]
            and item["confidence"] >= winner["confidence"] - 5
        ]
        conflicting = bool(competing)

    return {
        "value": winner["score"] if winner else None,
        "found": winner is not None,
        "riskCategory": risk,
        "confidence": winner["confidence"] if winner else 0,
        "source": winner["source"] if winner else "",
        "context": winner["context"] if winner else "",
        "candidates": candidates[:8],
        "needsReview": bool(not winner or winner["confidence"] < 85 or conflicting),
    }


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

    score_zero_rule = bool(score_found and score == 0)
    removal_candidate = bool(debt_review or score_zero_rule)
    has_balances = outstanding > 0
    score_in_cpi_range = bool(
        not debt_review
        and score_found
        and score is not None
        and 100 <= score <= 600
    )
    cpi_candidate = bool(score_in_cpi_range and not has_balances)
    pricing: Optional[Dict[str, Any]] = None
    additional_services: List[str] = []

    golden_questions = [
        {
            "question": "Are you 18 years or older and a South African citizen?",
            "whyItMatters": "Confirms basic identity and service eligibility before documents are requested.",
        },
        {
            "question": "Do you bank with one of South Africa's major banks?",
            "whyItMatters": "Helps confirm bank-verification, mandate and debit-order compatibility.",
        },
        {
            "question": "Is your cellphone number linked to your bank account?",
            "whyItMatters": "Important for DebiCheck or other bank-linked verification and authentication.",
        },
        {
            "question": "Is a Debt Counsellor or creditor currently debiting your bank account?",
            "whyItMatters": "Identifies active collections, debt-review payments and possible debit-date conflicts.",
        },
        {
            "question": "Are you employed or receiving a regular income into your bank account?",
            "whyItMatters": "Confirms affordability and whether the selected payment arrangement can be sustained.",
        },
    ]

    if removal_candidate:
        service = "Debt Review Removal"
        urgency = "High"
        if debt_review:
            headline = "Debt-review listing detected"
            reasons = [
                "The report contains a confirmed debt-review indicator. Verify the legal stage before offering removal."
            ]
            opening_script = (
                "Your credit report confirms a debt-review indicator. Before discussing removal, let us verify the legal stage, "
                "the outstanding balances and the documents required for a compliant assessment."
            )
        else:
            headline = "Credit score 0 — Debt Review Removal opportunity"
            reasons = [
                "The client credit score is exactly 0. Fin-Tastic routes an exact zero score to Debt Review Removal for verification of a possible debt-review status or related bureau restriction."
            ]
            opening_script = (
                "Your credit report shows a credit score of exactly 0. This creates a Debt Review Removal opportunity, but we must first verify the debt-review status, legal stage, balances and supporting documents before proceeding."
            )
        qualifying_questions = [
            "Do you know whether Form 17.2 was issued?",
            "Are all debt-review accounts paid up or do balances remain?",
            "Have you received a clearance certificate or court order?",
            "Which Debt Counsellor is currently handling the matter?",
            "Are any creditors or the Debt Counsellor still collecting monthly payments?",
        ]
        objection_handlers = [
            {
                "objection": "I was told that I can never leave debt review.",
                "response": "The available route depends on the verified legal stage, balances and documents. We first check the report, Form 17.2 status, court/NCT position and whether clearance requirements have been met.",
            },
            {
                "objection": "I have already paid all my accounts.",
                "response": "That is helpful, but paid-up letters, settlement evidence and the correct clearance or legal process still need to be verified before the listing can be addressed.",
            },
            {
                "objection": "Can you guarantee that the flag will be removed?",
                "response": "No responsible provider can guarantee an outcome before verifying the legal facts and supporting records. Explain the process, scope and possible routes without promising a result.",
            },
            {
                "objection": "Why does the process take time?",
                "response": "Timing depends on document availability and responses from the Debt Counsellor, creditors, bureaus, NCR, NCT or court. Give updates, but do not promise an unsupported completion date.",
            },
            {
                "objection": "I cannot afford another debit order.",
                "response": "Complete affordability first, explain all fees and payment dates clearly, and never create a mandate that the client cannot sustain.",
            },
        ]
        if has_balances:
            additional_services.append("Debt Mediation")
            reasons.append(
                f"Active balances of R{outstanding:,.2f} remain, so recommend Debt Mediation as an additional service alongside Debt Review Removal."
            )
    elif cpi_candidate:
        service = "Credit Profile Investigation"
        urgency = "Medium"
        headline = "Potential Credit Profile Investigation sale"
        reasons = [
            f"The client is not confirmed under debt review, the credit score is {score} (within the 100–600 CPI range), and there are no active outstanding balances.",
            "Investigate adverse listings, enquiries, account statuses, addresses and possible inaccurate or outdated bureau information before selecting a larger debt service.",
        ]
        opening_script = (
            f"Your report does not confirm debt review, the credit score is {score}, and no active balances were detected. "
            "A Credit Profile Investigation may be the best first step to identify inaccurate, outdated or unfamiliar information and determine what can legitimately be challenged or corrected."
        )
        qualifying_questions = [
            "Have you recently been declined for credit, housing or employment screening?",
            "Do you recognise every account, enquiry, address and employer shown on the report?",
            "Are any paid-up, settled or closed accounts still reflecting incorrectly?",
            "Have you received notices about fraud, identity theft or accounts you did not open?",
            "Have you previously lodged a bureau dispute or asked the creditor for supporting records?",
        ]
        objection_handlers = [
            {
                "objection": "I can download my own credit report for free.",
                "response": "The service is not only a report download. It is an account-by-account investigation of listings, enquiries, statuses and supporting records, followed by evidence-based dispute or correction steps where appropriate.",
            },
            {
                "objection": "Why must I pay R3,000?",
                "response": "Explain the complete scope before payment: profile analysis, exception identification, evidence gathering, creditor/bureau follow-up and progress feedback. Do not describe it as a guaranteed score increase.",
            },
            {
                "objection": "Can you guarantee that my score will increase?",
                "response": "No. Accurate negative information cannot simply be removed. Only information that is inaccurate, outdated, duplicated, unsupported or incorrectly reported can be challenged through the proper process.",
            },
            {
                "objection": "I cannot pay R3,000 once-off.",
                "response": "Offer the approved payment choices clearly: R1,500 for 2 months, R1,000 for 3 months or R750 for 4 months, subject to affordability and consent.",
            },
            {
                "objection": "I need credit immediately.",
                "response": "Do not promise an immediate approval. Bureau and creditor response times vary, and the client should avoid repeated new applications while the profile is being investigated.",
            },
            {
                "objection": "Just remove everything negative from my report.",
                "response": "Explain that legitimate and accurate information must remain. The investigation focuses on verifiable errors, outdated records, duplicates, unfamiliar entries and reporting exceptions.",
            },
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
            "Are you married, and should this be assessed as a joint application?",
            "Which debit orders must continue to protect essential services and assets?",
        ]
        objection_handlers = [
            {
                "objection": "I do not want to be blacklisted.",
                "response": "Explain the actual debt-review status and credit restrictions accurately. Do not use the word blacklist as a threat, and confirm that the client understands both the protections and limitations.",
            },
            {
                "objection": "Will Debt Review definitely save my car or house?",
                "response": "It may assist with an appropriate restructuring process, but protection is not unconditional. Legal stage, affordability, continued payments and creditor/court processes must be assessed.",
            },
            {
                "objection": "Can you guarantee a specific reduced instalment?",
                "response": "No. Use the current figures for an estimate only. The final proposal depends on verified income, expenses, account data and creditor or court approval.",
            },
            {
                "objection": "I do not want my creditors contacted.",
                "response": "A formal debt-review process requires prescribed notices and engagement. Explain this before the client signs so consent is informed.",
            },
            {
                "objection": "How quickly can this start?",
                "response": "The application can only progress once the required identity, income, banking and account documents are complete and the compliance checks have been done.",
            },
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
            "What monthly amount can the client consistently afford after essential expenses?",
            "Has the client previously made or broken a payment arrangement?",
        ]
        objection_handlers = [
            {
                "objection": "Why can I not negotiate with the creditors myself?",
                "response": "The client may negotiate directly. Explain that mediation offers a structured affordability assessment, documented proposals and coordinated follow-up, but participation remains voluntary.",
            },
            {
                "objection": "Will every creditor accept the proposal?",
                "response": "Acceptance cannot be guaranteed. Proposals must be realistic, supported by affordability and negotiated account by account.",
            },
            {
                "objection": "Will legal action stop immediately?",
                "response": "No automatic legal protection should be promised. Check each account's legal stage and obtain written confirmation of any arrangement.",
            },
            {
                "objection": "Is this the same as Debt Review?",
                "response": "No. Explain the product differences, legal status, credit implications and available protections clearly before the client chooses a service.",
            },
            {
                "objection": "I cannot afford the proposed amount this month.",
                "response": "Do not force an unaffordable arrangement. Rework the budget, choose a sustainable start date and record the client's consent to the final amount.",
            },
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
            "Are there debts or monthly commitments missing from the report?",
            "Does the client believe any information on the report is incorrect?",
        ]
        objection_handlers = [
            {
                "objection": "Why can you not recommend a service immediately?",
                "response": "The available report data is incomplete or does not safely match a product rule. Obtain the missing facts and documents rather than forcing a sale.",
            },
            {
                "objection": "Another company gave me an instant answer.",
                "response": "Explain that Fin-Tastic bases recommendations on verified data, affordability and legal status. A careful assessment reduces the risk of selling the wrong service.",
            },
            {
                "objection": "Can you just tell me what will fix my score?",
                "response": "Review the complete profile first. Scores can be affected by many factors, and no specific improvement should be promised without evidence.",
            },
        ]

    if arrears > 0:
        reasons.append(f"The included accounts show R{arrears:,.2f} in arrears.")
    if has_furniture:
        reasons.append("Furniture debt is present and should be clearly tagged during the client discussion.")

    next_steps = [
        "Complete all five Golden Questions and record any answer that requires verification.",
        "Confirm the client's contact details, application type, employment, income and household budget.",
        "Capture and verify banking details before sending any mandate or debit-order instruction.",
        "Review every included account and correct any source-data exceptions.",
        "Collect ID, proof of address, payslip and bank statements before handover.",
    ]
    if service == "Credit Profile Investigation":
        next_steps = [
            "Complete all five Golden Questions and verify identity, bank-linked cellphone and current debit orders.",
            "Confirm that the report does not contain a debt-review indicator.",
            "Review adverse listings, enquiries, addresses, paid-up accounts and unfamiliar information with the client.",
            "Explain the R3,000 fee and select once-off, 2-, 3- or 4-month payment terms.",
            "Obtain the client's consent and supporting documents before starting the investigation.",
        ]

    return {
        "service": service,
        "additionalServices": additional_services,
        "urgency": urgency,
        "headline": headline,
        "reasons": reasons,
        "openingScript": opening_script,
        "goldenQuestions": golden_questions,
        "qualifyingQuestions": qualifying_questions,
        "nextSteps": next_steps,
        "objectionHandlers": objection_handlers,
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
            "scoreZeroRule": score_zero_rule,
            "scoreInCpiRange": score_in_cpi_range,
            "hasOutstandingBalances": has_balances,
            "doubleSaleCandidate": bool(removal_candidate and has_balances),
            "creditProfileInvestigationCandidate": cpi_candidate,
        },
    }

def parse_datanamix(text: str, filename: str = "") -> Dict[str, Any]:
    if "DATANAMIX" not in text.upper() and "Datanamix Consumer Credit Report" not in text:
        raise UnsupportedReport("This parser build currently recognises the supplied Datanamix report layout.")

    identity = _parse_identity(text)
    score_result = _parse_score(text)
    score = score_result["value"]
    score_found = bool(score_result["found"])
    risk = str(score_result["riskCategory"] or "")
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
    if not score_found:
        warnings.append("The client credit score was not found. Capture and verify it manually before relying on the Sales Coach.")
    elif score_result["needsReview"]:
        warnings.append("More than one possible score was detected or the score label was unclear. Verify the displayed score against the PDF.")
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
        "scoreConfidence": score_result["confidence"],
        "scoreSource": score_result["source"],
        "scoreRawContext": score_result["context"],
        "scoreCandidates": score_result["candidates"],
        "scoreNeedsReview": score_result["needsReview"],
        "scoreManuallyVerified": False,
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
