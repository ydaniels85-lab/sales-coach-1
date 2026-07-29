from __future__ import annotations

import io
import json
import re
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None

try:
    import PyPDF2
except Exception:  # pragma: no cover
    PyPDF2 = None

try:
    import fitz  # PyMuPDF: renders scanned PDF pages to images for OCR
except Exception:  # pragma: no cover
    fitz = None

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None

# Common Windows install locations for Tesseract. This helps when tesseract.exe
# is installed but not added to PATH yet.
if pytesseract is not None:
    for _tess_path in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if Path(_tess_path).exists():
            pytesseract.pytesseract.tesseract_cmd = _tess_path
            break

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

CLIENTS: List[dict] = []
CASES: List[dict] = []
LAST_PARSE: Dict[str, Any] = {}

AMOUNT_RE = re.compile(r"(?<!\d)(?:R\s*)?-?\d{1,3}(?:[ ,]\d{3})*(?:\.\d{2})?|-?\d+(?:\.\d{2})?(?!\d)")
ID_RE = re.compile(r"\b\d{13}\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+27|0)\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
DATE_RE = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")

HEADER_SYNONYMS = {
    "creditor": ["creditor", "supplier", "subscriber", "institution", "account name", "credit provider", "provider"],
    "accountNo": ["account no", "account number", "acc no", "account", "loan no", "reference"],
    "type": ["type", "account type", "loan type", "product"],
    "openingBalance": ["opening balance", "open balance", "original amount", "opening bal", "open bal"],
    "currentBalance": ["current balance", "balance", "outstanding balance", "cur balance", "current bal", "outstanding"],
    "arrears": ["arrears", "amount overdue", "overdue", "past due", "arrear"],
    "monthlyInstallment": ["instalment", "installment", "monthly", "monthly instalment", "monthly installment", "repayment"],
    "lastPaid": ["last payment", "last paid", "last pay date", "last payment date"],
    "openDate": ["open date", "opened", "date opened", "start date"],
    "status": ["status", "account status", "state"],
}


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def to_number(value: Any) -> float:
    if value is None:
        return 0.0
    value = str(value).strip()
    if not value or value in {"-", "--", "N/A", "n/a"}:
        return 0.0
    value = value.replace("R", "").replace("r", "").replace(" ", "").replace(",", "")
    value = re.sub(r"[^0-9.\-]", "", value)
    try:
        return float(value)
    except Exception:
        return 0.0


def normalise_date(value: str) -> str:
    return (value or "").strip()


def detect_bureau(text: str) -> str:
    upper = text.upper()
    if "DATANAMIX" in upper:
        return "Datanamix"
    if "XDS" in upper or "XPERT DECISION SYSTEM" in upper:
        return "XDS"
    if "TRANSUNION" in upper:
        return "TransUnion"
    if "EXPERIAN" in upper:
        return "Experian"
    if "COMPUSCAN" in upper or "CREDIT CHECK" in upper:
        return "Compuscan"
    return "Unknown"


def find_label(text: str, labels: List[str], max_len: int = 90) -> str:
    for label in labels:
        patterns = [
            rf"(?im)^\s*{re.escape(label)}\s*[:\-]?\s*(.+)$",
            rf"(?i){re.escape(label)}\s*[:\-]\s*([^\n]{{1,{max_len}}})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                value = m.group(1).strip()
                value = re.split(r"\s{3,}|\t|\|", value)[0].strip()
                value = re.sub(r"\s+(ID|Identity|Date|DOB|Gender|Cell|Phone|Tel|Email)\b.*$", "", value, flags=re.I).strip()
                if 1 <= len(value) <= max_len:
                    return value
    return ""


def parse_client(text: str) -> Dict[str, Any]:
    client: Dict[str, Any] = {}

    id_match = ID_RE.search(text)
    client["idNumber"] = id_match.group(0) if id_match else ""

    email_match = EMAIL_RE.search(text)
    client["email"] = email_match.group(0) if email_match else ""

    phone_match = PHONE_RE.search(text)
    client["phone"] = phone_match.group(0) if phone_match else ""
    client["whatsapp"] = client["phone"]

    full_name = find_label(text, [
        "Full Name", "Consumer Name", "Client Name", "Name", "Names", "First Names", "Forenames"
    ])
    surname = find_label(text, ["Surname", "Last Name"])
    initials = find_label(text, ["Initials"])

    if surname and full_name and surname.lower() not in full_name.lower():
        client["fullName"] = f"{full_name} {surname}".strip()
    elif full_name:
        client["fullName"] = full_name
    elif surname and initials:
        client["fullName"] = f"{initials} {surname}".strip()
    else:
        client["fullName"] = ""

    client["address"] = find_label(text, ["Physical Address", "Residential Address", "Address", "Consumer Address"], max_len=160)
    client["employer"] = find_label(text, ["Employer", "Employer Name", "Company Name", "Occupation Employer"], max_len=100)
    client["occupation"] = find_label(text, ["Occupation", "Job Title", "Employment Type"], max_len=80)
    client["dateEmployed"] = find_label(text, ["Date Employed", "Employment Date", "Employed Since"], max_len=40)
    client["salaryFrequency"] = find_label(text, ["Salary Frequency", "Pay Frequency"], max_len=40) or "Monthly"
    client["bankName"] = find_label(text, ["Bank Name", "Bank"], max_len=80)
    client["accountHolder"] = find_label(text, ["Account Holder", "Account Holder Name"], max_len=100)
    client["accountType"] = find_label(text, ["Account Type", "Bank Account Type"], max_len=80)
    client["branchCode"] = find_label(text, ["Branch Code", "Universal Branch Code"], max_len=40)
    client["accountNumber"] = find_label(text, ["Account Number", "Bank Account Number"], max_len=50)

    score = find_label(text, ["Credit Score", "Score", "Risk Score", "Bureau Score"], max_len=20)
    score_match = re.search(r"\b\d{1,4}\b", score or "")
    if not score_match:
        score_match = re.search(r"(?i)(?:credit\s*)?score\D{0,20}(\d{1,4})", text)
    client["creditScore"] = int(score_match.group(1) if score_match and score_match.lastindex else score_match.group(0)) if score_match else 0

    upper = text.upper()
    client["confirmedDebtReview"] = any(phrase in upper for phrase in [
        "UNDER DEBT REVIEW",
        "DEBT REVIEW LISTED",
        "DEBT REVIEW FLAG",
        "DEBT REVIEW STATUS",
        "CONSUMER IS UNDER DEBT REVIEW",
        "DEBT REVIEW LISTED AGAINST CONSUMER",
    ])
    if client["creditScore"] == 0 and "DEBT REVIEW" in upper:
        client["confirmedDebtReview"] = True

    client["homeLoan"] = bool(re.search(r"(?i)home\s*loan|mortgage|bond", text))
    client["vehicleFinance"] = bool(re.search(r"(?i)vehicle\s*finance|instalment\s*sale|wesbank|mfc|toyota financial|vw financial", text))

    return client


def ocr_pdf_pages(data: bytes, max_pages: int = 12, dpi: int = 220) -> Tuple[str, List[str]]:
    """OCR scanned/image PDFs using PyMuPDF + pytesseract.

    This is intentionally conservative: if OCR tools are missing, it returns a
    clear warning instead of fake data. It never creates demo accounts.
    """
    warnings: List[str] = []
    if fitz is None:
        return "", ["OCR fallback unavailable: PyMuPDF is not installed. Run: pip install pymupdf"]
    if pytesseract is None:
        return "", ["OCR fallback unavailable: pytesseract is not installed. Run: pip install pytesseract"]

    try:
        # This raises if tesseract.exe is not installed or not on PATH.
        pytesseract.get_tesseract_version()
    except Exception as exc:
        return "", [
            "OCR fallback unavailable: Tesseract OCR is not installed or not on PATH.",
            "Install it with winget or the UB-Mannheim Windows installer, then restart CMD.",
            f"Tesseract check error: {exc}",
        ]

    text_parts: List[str] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return "", [f"OCR could not open PDF with PyMuPDF: {exc}"]

    page_count = min(len(doc), max_pages)
    if len(doc) > max_pages:
        warnings.append(f"OCR limited to first {max_pages} pages out of {len(doc)} pages for speed.")

    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page_index in range(page_count):
        try:
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_bytes = pix.tobytes("png")
            # psm 6 works better for credit report tables than the default in many cases.
            page_text = pytesseract.image_to_string(
                image_bytes,
                lang="eng",
                config="--oem 3 --psm 6",
            )
            if page_text.strip():
                text_parts.append(f"\n--- OCR PAGE {page_index + 1} ---\n{page_text}")
        except Exception as exc:
            warnings.append(f"OCR warning on page {page_index + 1}: {exc}")

    text = clean_text("\n".join(text_parts))
    if not text:
        warnings.append("OCR ran but did not extract readable text. The scan quality may be too low or the PDF may be protected.")
    return text, warnings


def extract_pdf_text_and_tables(data: bytes) -> Tuple[str, List[List[List[str]]], List[str]]:
    warnings: List[str] = []
    tables: List[List[List[str]]] = []
    text_parts: List[str] = []

    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page_index, page in enumerate(pdf.pages, start=1):
                    try:
                        txt = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                        if txt:
                            text_parts.append(f"\n--- PAGE {page_index} ---\n{txt}")
                    except Exception as exc:
                        warnings.append(f"Text extraction warning on page {page_index}: {exc}")
                    try:
                        page_tables = page.extract_tables() or []
                        for table in page_tables:
                            cleaned_table = [[str(cell or "").strip() for cell in row] for row in table if row]
                            if cleaned_table:
                                tables.append(cleaned_table)
                    except Exception as exc:
                        warnings.append(f"Table extraction warning on page {page_index}: {exc}")
        except Exception as exc:
            warnings.append(f"pdfplumber failed: {exc}")

    if not "\n".join(text_parts).strip() and PyPDF2 is not None:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            for i, page in enumerate(reader.pages, start=1):
                try:
                    txt = page.extract_text() or ""
                    if txt:
                        text_parts.append(f"\n--- PAGE {i} ---\n{txt}")
                except Exception as exc:
                    warnings.append(f"PyPDF2 page {i} warning: {exc}")
        except Exception as exc:
            warnings.append(f"PyPDF2 failed: {exc}")

    text = clean_text("\n".join(text_parts))

    # If the PDF is scanned, normal text extraction returns almost nothing.
    # Do OCR before returning a failure. We still keep pdfplumber tables if any.
    if len(text) < 80:
        warnings.append("PDF text layer is missing or too small. Running OCR fallback.")
        ocr_text, ocr_warnings = ocr_pdf_pages(data)
        warnings.extend(ocr_warnings)
        if len(ocr_text) > len(text):
            text = ocr_text

    if not text:
        warnings.append("No extractable text found in PDF after normal extraction and OCR. Check OCR installation or upload a clearer/text-based PDF.")
    return text, tables, warnings

def header_index(header: List[str]) -> Dict[str, int]:
    normalised = [re.sub(r"\s+", " ", str(h or "").strip().lower()) for h in header]
    mapping: Dict[str, int] = {}
    for field, synonyms in HEADER_SYNONYMS.items():
        for i, value in enumerate(normalised):
            if not value:
                continue
            if any(syn in value for syn in synonyms):
                if field == "currentBalance" and "opening" in value:
                    continue
                mapping.setdefault(field, i)
                break
    return mapping


def row_to_account(row: List[str], mapping: Dict[str, int], source: str) -> Optional[Dict[str, Any]]:
    def get(field: str) -> str:
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ""
        return str(row[idx] or "").strip()

    creditor = get("creditor")
    account_no = get("accountNo")
    if not creditor and not account_no:
        joined = " ".join(row)
        if not re.search(r"\d", joined):
            return None

    account = {
        "id": f"acc-{uuid4().hex[:8]}",
        "creditor": creditor,
        "accountNo": account_no,
        "type": get("type"),
        "openingBalance": to_number(get("openingBalance")),
        "currentBalance": to_number(get("currentBalance")),
        "arrears": to_number(get("arrears")),
        "monthlyInstallment": to_number(get("monthlyInstallment")),
        "reducedInstallment": 0,
        "monthsInArrears": 0,
        "lastPaid": normalise_date(get("lastPaid")),
        "openDate": normalise_date(get("openDate")),
        "status": get("status"),
        "include": True,
        "furniture": False,
        "source": source,
    }
    account["reducedInstallment"] = round(account["monthlyInstallment"] * 0.5, 2) if account["monthlyInstallment"] else 0
    account["furniture"] = bool(re.search(r"(?i)furniture|bradlows|russells|beares|lewis|ok furniture|fair price", f"{account['creditor']} {account['type']}"))

    has_money = any(account[field] for field in ["openingBalance", "currentBalance", "arrears", "monthlyInstallment"])
    if not (account["creditor"] or account["accountNo"]) or not has_money:
        return None
    return account


def parse_accounts_from_tables(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        if len(table) < 2:
            continue
        # Try each of the first 4 rows as a header because PDF tables often split headers.
        for header_row_index in range(min(4, len(table) - 1)):
            header = table[header_row_index]
            mapping = header_index(header)
            if len(mapping) < 3 or not ("creditor" in mapping or "accountNo" in mapping):
                continue
            for row in table[header_row_index + 1:]:
                if len([c for c in row if c]) < 3:
                    continue
                account = row_to_account(row, mapping, f"table-{table_index + 1}")
                if account:
                    accounts.append(account)
            if accounts:
                break
    return dedupe_accounts(accounts)


def parse_accounts_from_text(text: str) -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    lines = [re.sub(r"\s{2,}", " | ", line.strip()) for line in text.splitlines() if line.strip()]

    for line in lines:
        raw = line.strip()
        if len(raw) < 20:
            continue
        upper = raw.upper()
        if any(skip in upper for skip in ["TOTAL", "SUMMARY", "HEADER", "PAGE ", "ENQUIRY", "DISCLAIMER", "SCORE"]):
            continue
        amount_matches = list(AMOUNT_RE.finditer(raw))
        if len(amount_matches) < 2:
            continue
        if not re.search(r"(?i)account|loan|card|bank|finance|retail|store|home|vehicle|fnb|absa|nedbank|standard|capitec|wesbank|mfc|edgars|vodacom|mtn|telkom|furniture|lewis|russells|bradlows", raw):
            continue

        amounts = [to_number(m.group(0)) for m in amount_matches]
        # Avoid treating ID numbers/phone numbers as money by removing very large 13 digit tokens.
        amounts = [a for a in amounts if abs(a) < 10_000_000]
        if len(amounts) < 2:
            continue

        first_amount_pos = amount_matches[0].start()
        left = raw[:first_amount_pos].strip(" |:-")
        tokens = [t.strip() for t in re.split(r"\||\s{2,}", left) if t.strip()]
        creditor = tokens[0] if tokens else left[:60]
        account_no_match = re.search(r"\b[A-Z0-9][A-Z0-9\-/]{4,}\b", left)
        account_no = account_no_match.group(0) if account_no_match else ""

        dates = DATE_RE.findall(raw)
        account = {
            "id": f"acc-{uuid4().hex[:8]}",
            "creditor": creditor[:80],
            "accountNo": account_no,
            "type": "",
            "openingBalance": amounts[0] if len(amounts) > 3 else 0,
            "currentBalance": amounts[-3] if len(amounts) >= 3 else amounts[0],
            "arrears": amounts[-2] if len(amounts) >= 2 else 0,
            "monthlyInstallment": amounts[-1] if len(amounts) >= 1 else 0,
            "reducedInstallment": round((amounts[-1] if amounts else 0) * 0.5, 2),
            "monthsInArrears": 0,
            "lastPaid": dates[-1] if dates else "",
            "openDate": dates[0] if len(dates) > 1 else "",
            "status": "Open" if re.search(r"(?i)open|active|current", raw) else "",
            "include": True,
            "furniture": bool(re.search(r"(?i)furniture|bradlows|russells|beares|lewis|ok furniture|fair price", raw)),
            "source": "text-line",
        }
        if account["creditor"] and (account["currentBalance"] or account["monthlyInstallment"]):
            accounts.append(account)

    return dedupe_accounts(accounts)


def dedupe_accounts(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for account in accounts:
        key = (
            re.sub(r"\W+", "", str(account.get("creditor", "")).lower()),
            re.sub(r"\W+", "", str(account.get("accountNo", "")).lower()),
            round(float(account.get("currentBalance") or 0), 2),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(account)
    return out


def parse_report(filename: str, data: bytes) -> Dict[str, Any]:
    warnings: List[str] = []
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        text = clean_text(data.decode("utf-8", errors="ignore"))
        tables = []
    elif ext == ".json":
        try:
            payload = json.loads(data.decode("utf-8", errors="ignore"))
            return {
                "bureau": payload.get("bureau", "JSON"),
                "confidence": 0.95,
                "warnings": [],
                "client": payload.get("client", {}),
                "accounts": payload.get("accounts", []),
                "debug": {"source": "json-upload"},
            }
        except Exception as exc:
            text = clean_text(data.decode("utf-8", errors="ignore"))
            tables = []
            warnings.append(f"JSON decode failed, reading as text: {exc}")
    else:
        text, tables, extract_warnings = extract_pdf_text_and_tables(data)
        warnings.extend(extract_warnings)

    bureau = detect_bureau(text)
    client = parse_client(text)
    table_accounts = parse_accounts_from_tables(tables)
    text_accounts = parse_accounts_from_text(text)
    accounts = table_accounts if len(table_accounts) >= len(text_accounts) else text_accounts

    if not accounts and table_accounts:
        accounts = table_accounts
    if not accounts and text_accounts:
        accounts = text_accounts

    if not client.get("fullName"):
        warnings.append("Client full name was not confidently detected.")
    if not client.get("idNumber"):
        warnings.append("Client ID number was not confidently detected.")
    if not accounts:
        warnings.append("No account rows were confidently detected. The report layout may need a bureau-specific rule or OCR.")
    if bureau == "Unknown":
        warnings.append("Bureau type was not detected.")

    confidence = 0.25
    if text:
        confidence += 0.15
    if bureau != "Unknown":
        confidence += 0.15
    if client.get("idNumber"):
        confidence += 0.15
    if client.get("fullName"):
        confidence += 0.1
    if accounts:
        confidence += min(0.25, 0.08 * len(accounts))
    confidence = max(0.0, min(confidence, 0.98))

    return {
        "bureau": bureau,
        "confidence": round(confidence, 2),
        "warnings": warnings,
        "client": client,
        "accounts": accounts,
        "debug": {
            "charsExtracted": len(text),
            "tablesExtracted": len(tables),
            "tableAccounts": len(table_accounts),
            "textAccounts": len(text_accounts),
            "textPreview": text[:6000],
        },
    }


@app.get("/")
def root():
    return jsonify({"success": True, "app": "Fin-Tastic Sales Coach v6 OCR Parser", "health": "/api/health"})


@app.get("/api/health")
@app.get("/health")
def health():
    return jsonify({"success": True, "status": "ok", "time": now_iso(), "parser": "pdfplumber + PyPDF2 + OCR fallback"})


@app.post("/api/upload/credit-report")
def upload_credit_report():
    global LAST_PARSE
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    data = uploaded.read()
    if not data:
        return jsonify({"success": False, "error": "Uploaded file is empty"}), 400

    parsed = parse_report(uploaded.filename or "credit-report.pdf", data)
    LAST_PARSE = {
        "filename": uploaded.filename,
        "uploadedAt": now_iso(),
        "parsed": parsed,
    }
    return jsonify({"success": True, "filename": uploaded.filename, "parsed": parsed})


@app.get("/api/debug/last-parse")
def debug_last_parse():
    return jsonify({"success": True, "lastParse": LAST_PARSE})


@app.post("/api/nupay/send-mandate")
def nupay_send_mandate():
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "success": True,
        "status": "sent",
        "provider": "nupay",
        "apiReference": f"NUPAY-{uuid4().hex[:10].upper()}",
        "clientId": payload.get("id"),
    })


@app.post("/api/client-link/send")
def send_client_link():
    payload = request.get_json(silent=True) or {}
    client_id = payload.get("clientId") or payload.get("id") or f"client-{uuid4().hex[:8]}"
    return jsonify({
        "success": True,
        "url": f"https://portal.fin-tastic.local/client/{client_id}?token={uuid4().hex[:10]}",
        "signatureRequired": True,
        "documentsRequired": True,
    })


@app.post("/api/admin-workflow/pass-sale")
def pass_sale():
    payload = request.get_json(silent=True) or {}
    CASES.insert(0, payload)
    return jsonify({"success": True, "case": payload})


@app.post("/api/documents/generate")
def generate_document():
    payload = request.get_json(silent=True) or {}
    return jsonify({"success": True, "documentType": payload.get("documentType"), "status": "generated_placeholder"})


@app.post("/api/pda/submit")
def pda_submit():
    payload = request.get_json(silent=True) or {}
    return jsonify({"success": True, "reference": f"PDA-{uuid4().hex[:10].upper()}", "clientId": payload.get("clientId")})



@app.get("/api/debug/ocr-status")
def ocr_status():
    status = {
        "pymupdfInstalled": fitz is not None,
        "pytesseractInstalled": pytesseract is not None,
        "tesseractAvailable": False,
        "tesseractVersion": "",
        "tesseractCommand": "",
    }
    if pytesseract is not None:
        status["tesseractCommand"] = str(getattr(pytesseract.pytesseract, "tesseract_cmd", ""))
        try:
            status["tesseractVersion"] = str(pytesseract.get_tesseract_version())
            status["tesseractAvailable"] = True
        except Exception as exc:
            status["tesseractError"] = str(exc)
    return jsonify({"success": True, "ocr": status})

@app.get("/api/debug/routes")
def routes():
    return jsonify({"success": True, "routes": [{"rule": str(rule), "methods": sorted(rule.methods)} for rule in app.url_map.iter_rules()]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
