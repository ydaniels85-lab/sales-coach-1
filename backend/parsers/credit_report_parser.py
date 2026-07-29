from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MONEY_RE = re.compile(r"(?:R\s*)?(-?\d{1,3}(?:[\s,]\d{3})*(?:\.\d{2})|-?\d+\.\d{2})")
ID_RE = re.compile(r"\b([0-9]{13})\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+27|0)(?:\s?\d){9}\b")
DATE_RE = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")

DEBT_REVIEW_PATTERNS = [
    r"under\s+debt\s+review",
    r"debt\s+review\s+listed",
    r"debt\s+review\s+indicator",
    r"consumer\s+is\s+under\s+debt\s+review",
    r"debt\s+review\s+flag",
]

BUREAU_MARKERS = {
    "Datanamix": ["datanamix", "data namix"],
    "XDS": ["xds", "xpert decision systems"],
    "TransUnion": ["transunion", "trans union"],
    "Experian": ["experian"],
    "Compuscan": ["compuscan", "cpa credit profile"],
}

FURNITURE_WORDS = [
    "beares", "bradlows", "fair price", "russells", "lewis", "ok furniture", "house & home",
    "house and home", "dial-a-bed", "rochester", "furniture city", "sleepmasters", "pep home"
]


def _read_pdf_text(path: Path) -> str:
    chunks: list[str] = []
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                if text.strip():
                    chunks.append(text)
    except Exception:
        pass

    if not "\n".join(chunks).strip():
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(str(path))
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append(text)
        except Exception:
            pass

    return "\n".join(chunks).replace("\x00", " ")


def _money(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = value.replace("R", "").replace(" ", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _detect_bureau(text: str) -> str:
    low = text.lower()
    for bureau, markers in BUREAU_MARKERS.items():
        if any(marker in low for marker in markers):
            return bureau
    return "Unknown"


def _first_match(pattern: str, text: str, flags: int = re.I) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def _extract_client(text: str) -> dict[str, Any]:
    compact = re.sub(r"[ \t]+", " ", text)
    id_number = _first_match(r"(?:ID\s*(?:No|Number)?|Identity\s*(?:No|Number)?)[\s:.-]*([0-9]{13})", compact) or (ID_RE.search(compact).group(1) if ID_RE.search(compact) else "")
    email_match = EMAIL_RE.search(compact)
    phone_match = PHONE_RE.search(compact)

    name = (
        _first_match(r"(?:Consumer|Client|Customer|Name|Full\s*Names?)\s*(?:Name)?[\s:.-]+([A-Z][A-Za-z' -]{3,80})", compact)
        or _first_match(r"(?:Surname\s*and\s*Names|Names\s*and\s*Surname)[\s:.-]+([A-Z][A-Za-z' -]{3,80})", compact)
    )
    surname = _first_match(r"Surname[\s:.-]+([A-Z][A-Za-z' -]{1,40})", compact)
    first_names = _first_match(r"(?:First\s*Names?|Forenames?|Names)[\s:.-]+([A-Z][A-Za-z' -]{1,60})", compact)
    if not name and (first_names or surname):
        name = f"{first_names} {surname}".strip()

    employer = _first_match(r"Employer[\s:.-]+([^\n\r]{2,80})", text)
    address = _first_match(r"(?:Residential|Physical|Home)\s*Address[\s:.-]+([^\n\r]{5,160})", text)

    return {
        "full_name": name or "Unknown Client",
        "first_names": first_names,
        "surname": surname,
        "id_number": id_number,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "employer": employer,
        "address": address,
    }


def _extract_score(text: str) -> int | None:
    patterns = [
        r"Credit\s*Score\s*[:.-]?\s*(\d{1,4})",
        r"Score\s*[:.-]?\s*(\d{1,4})",
        r"Risk\s*Score\s*[:.-]?\s*(\d{1,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 9999:
                return value
    return None


def _line_has_account_signal(line: str) -> bool:
    low = line.lower()
    has_money = len(MONEY_RE.findall(line)) >= 1
    account_words = ["account", "loan", "bank", "retail", "credit", "balance", "arrears", "instal", "install", "opened", "status"]
    return has_money and any(word in low for word in account_words)


def _extract_accounts(text: str) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    for idx, line in enumerate(lines):
        if len(line) < 12 or not _line_has_account_signal(line):
            continue
        money_values = MONEY_RE.findall(line)
        if not money_values:
            continue
        name_part = re.split(r"(?:R\s*)?-?\d", line, maxsplit=1)[0]
        name_part = re.sub(r"\b(account|current|opening|balance|arrears|instalment|installment|monthly|amount)\b", "", name_part, flags=re.I).strip(" -:|.,")
        if len(name_part) < 2:
            prev = lines[idx - 1] if idx > 0 else ""
            name_part = prev[:60].strip(" -:|.,") or "Unknown Creditor"
        creditor = name_part[:80]
        values = [_money(v) for v in money_values]
        current_balance = max(values) if values else 0.0
        monthly_installment = values[-1] if len(values) >= 2 else 0.0
        arrears = values[-2] if len(values) >= 3 else 0.0
        dates = DATE_RE.findall(line)
        key = f"{creditor}|{current_balance}|{monthly_installment}|{arrears}"
        if key in seen:
            continue
        seen.add(key)
        low = creditor.lower() + " " + line.lower()
        accounts.append({
            "id": f"acc-{len(accounts)+1:03d}",
            "creditor": creditor or "Unknown Creditor",
            "account_number": _first_match(r"\b(?:Acc(?:ount)?\s*(?:No|Number)?)[\s:.-]*([A-Z0-9-]{4,30})", line),
            "opening_balance": values[0] if values else 0.0,
            "current_balance": current_balance,
            "arrears": arrears,
            "monthly_installment": monthly_installment,
            "reduced_amount": round(monthly_installment * 0.55, 2) if monthly_installment else round(current_balance * 0.015, 2),
            "last_paid_date": dates[-1] if dates else "",
            "open_date": dates[0] if dates else "",
            "status": "In arrears" if arrears > 0 or "arrear" in line.lower() else "Active",
            "include": current_balance > 0,
            "furniture_account": any(word in low for word in FURNITURE_WORDS),
            "source_line": line[:240],
        })

    # If the PDF layout prevents table extraction, still create a high-level debt row if total balance exists.
    if not accounts:
        total = _first_match(r"(?:Total\s*(?:Outstanding|Balance|Debt)|Outstanding\s*Balance)[\s:.-]*(?:R\s*)?([0-9,\s]+\.\d{2})", text)
        if total:
            amount = _money(total)
            accounts.append({
                "id": "acc-001",
                "creditor": "Total debt from report",
                "account_number": "",
                "opening_balance": 0.0,
                "current_balance": amount,
                "arrears": 0.0,
                "monthly_installment": 0.0,
                "reduced_amount": round(amount * 0.015, 2),
                "last_paid_date": "",
                "open_date": "",
                "status": "Review required",
                "include": amount > 0,
                "furniture_account": False,
                "source_line": "Fallback total balance extraction",
            })
    return accounts[:80]


def parse_credit_report(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    text = _read_pdf_text(path)
    score = _extract_score(text)
    bureau = _detect_bureau(text)
    client = _extract_client(text)
    accounts = _extract_accounts(text)
    low = text.lower()
    debt_review = any(re.search(pattern, low, re.I) for pattern in DEBT_REVIEW_PATTERNS)
    active_balance_total = round(sum(acc.get("current_balance", 0.0) for acc in accounts if acc.get("include", True)), 2)
    arrears_total = round(sum(acc.get("arrears", 0.0) for acc in accounts if acc.get("include", True)), 2)
    reduced_total = round(sum(acc.get("reduced_amount", 0.0) for acc in accounts if acc.get("include", True)), 2)

    return {
        "bureau": bureau,
        "client": client,
        "report": {
            "filename": path.name,
            "credit_score": score,
            "debt_review_flag": debt_review,
            "text_length": len(text),
            "parser_warning": "OCR may be required if this PDF is scanned/image-based." if len(text.strip()) < 80 else "",
        },
        "totals": {
            "active_balance_total": active_balance_total,
            "arrears_total": arrears_total,
            "reduced_total": reduced_total,
            "account_count": len(accounts),
            "furniture_account_count": sum(1 for account in accounts if account.get("furniture_account")),
        },
        "accounts": accounts,
        "flags": {
            "score_zero": score == 0,
            "has_active_balances": active_balance_total > 0,
            "has_arrears": arrears_total > 0,
            "needs_admin_review": len(accounts) == 0 or len(text.strip()) < 80,
        },
        "raw_preview": text[:1500],
    }
