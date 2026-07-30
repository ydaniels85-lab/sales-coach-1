from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, UniqueConstraint, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .parser import PdfPasswordRequired, UnsupportedReport, build_sales_coach, parse_credit_report

APP_NAME = "Fin-Tastic Render API"
APP_VERSION = "2026.07.render-open-access-sales-coach-2"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "ydaniels85@gmail.com").strip().lower()
DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "khusela-debt-management").strip().lower()
DEFAULT_TENANT_NAME = os.getenv("DEFAULT_TENANT_NAME", "Khusela Debt Management").strip()
REPORT_STORAGE_DIR = os.getenv("REPORT_STORAGE_DIR", "").strip()
OPEN_ACCESS_OPERATOR_ID = os.getenv("OPEN_ACCESS_OPERATOR_ID", "open-access").strip() or "open-access"


def _database_uri() -> str:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured.startswith("postgres://"):
        configured = "postgresql://" + configured[len("postgres://"):]
    if configured:
        return configured
    return f"sqlite:///{(DATA_DIR / 'fintastic.db').as_posix()}"


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Tenant(db.Model):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(db.String(80), primary_key=True)
    name: Mapped[str] = mapped_column(db.String(160), nullable=False)
    owner_email: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Client(db.Model):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("tenant_id", "id_number", name="uq_client_tenant_id_number"),)

    id: Mapped[str] = mapped_column(db.String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(db.String(80), nullable=False, index=True)
    id_number: Mapped[Optional[str]] = mapped_column(db.String(30), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(db.String(80), nullable=False)
    assigned_user_id: Mapped[str] = mapped_column(db.String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )


app = Flask(__name__, static_folder=None)
app.config.update(
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,
    SQLALCHEMY_DATABASE_URI=_database_uri(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
    JSON_SORT_KEYS=False,
)
db.init_app(app)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: Optional[datetime]) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def initialize_database() -> None:
    with app.app_context():
        db.create_all()
        tenant = db.session.get(Tenant, DEFAULT_TENANT_ID)
        if not tenant:
            db.session.add(
                Tenant(
                    id=DEFAULT_TENANT_ID,
                    name=DEFAULT_TENANT_NAME,
                    owner_email=OWNER_EMAIL,
                )
            )
            db.session.commit()


def client_payload(record: Client) -> Dict[str, Any]:
    payload = normalize_client_payload(dict(record.payload or {}))
    payload.update(
        {
            "id": record.id,
            "tenantId": record.tenant_id,
            "createdAt": iso(record.created_at),
            "updatedAt": iso(record.updated_at),
            "createdBy": record.created_by,
            "assignedUserId": record.assigned_user_id,
        }
    )
    return payload


def blank_bank() -> Dict[str, Any]:
    return {
        "accountHolder": "",
        "bankName": "",
        "accountType": "",
        "branchCode": "",
        "accountNumber": "",
        "debitOrderDay": "",
    }


def blank_spouse() -> Dict[str, Any]:
    return {
        "firstName": "",
        "secondName": "",
        "surname": "",
        "fullName": "",
        "idNumber": "",
        "dateOfBirth": "",
        "gender": "",
        "maritalStatus": "",
        "phone": "",
        "alternativePhone": "",
        "whatsapp": "",
        "email": "",
        "physicalAddress": "",
        "suburb": "",
        "city": "",
        "province": "",
        "postalCode": "",
        "employer": "",
        "occupation": "",
        "dateEmployed": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
        "monthlyLivingExpenses": 0,
        "bank": blank_bank(),
    }


def default_client_payload() -> Dict[str, Any]:
    coach = build_sales_coach({}, None, False, False, [])
    return {
        "applicationType": "Single",
        "firstName": "",
        "secondName": "",
        "surname": "",
        "fullName": "",
        "idNumber": "",
        "dateOfBirth": "",
        "gender": "",
        "maritalStatus": "",
        "phone": "",
        "alternativePhone": "",
        "whatsapp": "",
        "email": "",
        "physicalAddress": "",
        "suburb": "",
        "city": "",
        "province": "",
        "postalCode": "",
        "employer": "",
        "occupation": "",
        "dateEmployed": "",
        "salaryFrequency": "Monthly",
        "grossSalary": 0,
        "nettSalary": 0,
        "monthlyLivingExpenses": 0,
        "bank": blank_bank(),
        "spouse": blank_spouse(),
        "creditScore": None,
        "scoreFound": False,
        "riskCategory": "",
        "debtReviewListed": False,
        "debtReviewDetail": "",
        "status": "Client Details Captured",
        "serviceType": coach["service"],
        "accounts": [],
        "coach": coach,
        "report": {
            "filename": "",
            "bureau": "",
            "reportReference": "",
            "clientReference": "",
            "searchDate": "",
            "summary": {},
        },
        "detailsCompletion": 0,
        "detailsComplete": False,
    }


def _as_float(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _full_name(payload: Dict[str, Any]) -> str:
    return " ".join(
        str(payload.get(key) or "").strip()
        for key in ("firstName", "secondName", "surname")
        if str(payload.get(key) or "").strip()
    )


def _details_completion(payload: Dict[str, Any]) -> tuple[int, bool]:
    bank = payload.get("bank") if isinstance(payload.get("bank"), dict) else {}
    primary_values = [
        payload.get("firstName"), payload.get("surname"), payload.get("idNumber"),
        payload.get("phone"), payload.get("email"), payload.get("physicalAddress"),
        payload.get("employer"), payload.get("nettSalary"), bank.get("accountHolder"),
        bank.get("bankName"), bank.get("accountType"), bank.get("accountNumber"),
    ]
    values = list(primary_values)
    if payload.get("applicationType") == "Joint":
        spouse = payload.get("spouse") if isinstance(payload.get("spouse"), dict) else {}
        spouse_bank = spouse.get("bank") if isinstance(spouse.get("bank"), dict) else {}
        values.extend([
            spouse.get("firstName"), spouse.get("surname"), spouse.get("idNumber"),
            spouse.get("phone"), spouse.get("email"), spouse.get("employer"),
            spouse.get("nettSalary"), spouse_bank.get("accountHolder"),
            spouse_bank.get("bankName"), spouse_bank.get("accountNumber"),
        ])
    completed = sum(1 for value in values if value not in (None, "", 0, 0.0))
    percentage = round((completed / len(values)) * 100) if values else 0
    return percentage, completed == len(values)


def normalize_client_payload(incoming: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = default_client_payload()
    if isinstance(existing, dict):
        payload.update(existing)
    if isinstance(incoming, dict):
        payload.update(incoming)

    existing_bank = existing.get("bank", {}) if isinstance(existing, dict) and isinstance(existing.get("bank"), dict) else {}
    incoming_bank = incoming.get("bank", {}) if isinstance(incoming, dict) and isinstance(incoming.get("bank"), dict) else {}
    bank = blank_bank()
    bank.update(existing_bank)
    bank.update(incoming_bank)
    payload["bank"] = bank

    existing_spouse = existing.get("spouse", {}) if isinstance(existing, dict) and isinstance(existing.get("spouse"), dict) else {}
    incoming_spouse = incoming.get("spouse", {}) if isinstance(incoming, dict) and isinstance(incoming.get("spouse"), dict) else {}
    spouse = blank_spouse()
    spouse.update(existing_spouse)
    spouse.update(incoming_spouse)
    spouse_bank = blank_bank()
    if isinstance(existing_spouse.get("bank"), dict):
        spouse_bank.update(existing_spouse["bank"])
    if isinstance(incoming_spouse.get("bank"), dict):
        spouse_bank.update(incoming_spouse["bank"])
    spouse["bank"] = spouse_bank
    spouse["fullName"] = _full_name(spouse)
    payload["spouse"] = spouse

    payload["applicationType"] = "Joint" if payload.get("applicationType") == "Joint" else "Single"
    payload["fullName"] = _full_name(payload) or str(payload.get("fullName") or "").strip()
    payload["idNumber"] = str(payload.get("idNumber") or "").strip()
    for field in ("grossSalary", "nettSalary", "monthlyLivingExpenses"):
        payload[field] = _as_float(payload.get(field))
        spouse[field] = _as_float(spouse.get(field))

    accounts = payload.get("accounts")
    payload["accounts"] = accounts if isinstance(accounts, list) else []
    coach = build_sales_coach(
        payload,
        payload.get("creditScore"),
        bool(payload.get("scoreFound")),
        bool(payload.get("debtReviewListed")),
        payload["accounts"],
    )
    payload["coach"] = coach
    payload["serviceType"] = coach["service"]
    completion, complete = _details_completion(payload)
    payload["detailsCompletion"] = completion
    payload["detailsComplete"] = complete
    return payload


def merge_report_with_existing(existing: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(parsed)
    preserve_fields = (
        "applicationType", "firstName", "secondName", "surname", "fullName", "idNumber",
        "dateOfBirth", "gender", "maritalStatus", "phone", "alternativePhone", "whatsapp",
        "email", "physicalAddress", "suburb", "city", "province", "postalCode", "employer",
        "occupation", "dateEmployed", "salaryFrequency", "grossSalary", "nettSalary",
        "monthlyLivingExpenses",
    )
    for field in preserve_fields:
        value = existing.get(field)
        if value not in (None, "", {}, []):
            merged[field] = value
    if isinstance(existing.get("bank"), dict):
        merged["bank"] = dict(existing["bank"])
    if isinstance(existing.get("spouse"), dict):
        merged["spouse"] = dict(existing["spouse"])
    return merged


def list_clients(tenant_id: str) -> list[Dict[str, Any]]:
    records = db.session.execute(
        db.select(Client).where(Client.tenant_id == tenant_id).order_by(Client.updated_at.desc())
    ).scalars().all()
    return [client_payload(record) for record in records]


def store_report_if_enabled(tenant_id: str, client_id: str, filename: str, data: bytes) -> str:
    if not REPORT_STORAGE_DIR:
        return ""
    root = Path(REPORT_STORAGE_DIR).resolve()
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    target_dir = root / tenant_id / client_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    target.write_bytes(data)
    return str(target.relative_to(root))


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self' http://localhost:8080 http://localhost:5173",
    )
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api")
def api_root():
    return jsonify(
        {
            "app": APP_NAME,
            "version": APP_VERSION,
            "status": "running",
            "authenticationRequired": False,
            "accessMode": "open",
            "tenantId": DEFAULT_TENANT_ID,
        }
    )


@app.get("/api/health")
def health():
    database_ready = False
    detail = ""
    try:
        db.session.execute(text("SELECT 1"))
        database_ready = True
    except Exception as exc:
        detail = str(exc)
    return (
        jsonify(
            {
                "success": database_ready,
                "app": APP_NAME,
                "version": APP_VERSION,
                "databaseReady": database_ready,
                "authenticationRequired": False,
                "accessMode": "open",
                "tenantId": DEFAULT_TENANT_ID,
                "defaultPdfPasswordConfigured": bool(
                    os.getenv("DEFAULT_CREDIT_REPORT_PDF_PASSWORD")
                ),
                "detail": detail,
            }
        ),
        200 if database_ready else 503,
    )


@app.get("/api/clients")
def clients_get():
    return jsonify({"success": True, "clients": list_clients(DEFAULT_TENANT_ID)})


@app.get("/api/clients/<client_id>")
def client_get(client_id: str):
    record = db.session.get(Client, client_id)
    if not record or record.tenant_id != DEFAULT_TENANT_ID:
        return jsonify({"success": False, "error": "Client not found."}), 404
    return jsonify({"success": True, "client": client_payload(record)})


@app.post("/api/clients")
def client_create():
    incoming = request.get_json(silent=True) or {}
    if not isinstance(incoming, dict):
        return jsonify({"success": False, "error": "Client payload must be a JSON object."}), 400
    payload = normalize_client_payload(incoming)
    id_number = payload.get("idNumber") or None
    if id_number:
        duplicate = db.session.execute(
            db.select(Client).where(
                Client.tenant_id == DEFAULT_TENANT_ID,
                Client.id_number == id_number,
            )
        ).scalar_one_or_none()
        if duplicate:
            return jsonify({"success": False, "error": "A client with this ID number already exists in this tenant."}), 409
    record = Client(
        id=f"client-{secrets.token_hex(6)}",
        tenant_id=DEFAULT_TENANT_ID,
        id_number=id_number,
        payload=payload,
        created_by=OPEN_ACCESS_OPERATOR_ID,
        assigned_user_id=OPEN_ACCESS_OPERATOR_ID,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"success": True, "client": client_payload(record)}), 201


@app.patch("/api/clients/<client_id>")
def client_update(client_id: str):
    record = db.session.get(Client, client_id)
    if not record or record.tenant_id != DEFAULT_TENANT_ID:
        return jsonify({"success": False, "error": "Client not found."}), 404
    incoming = request.get_json(silent=True) or {}
    if not isinstance(incoming, dict):
        return jsonify({"success": False, "error": "Client payload must be a JSON object."}), 400
    payload = normalize_client_payload(incoming, existing=dict(record.payload or {}))
    id_number = payload.get("idNumber") or None
    if id_number:
        duplicate = db.session.execute(
            db.select(Client).where(
                Client.tenant_id == DEFAULT_TENANT_ID,
                Client.id_number == id_number,
                Client.id != record.id,
            )
        ).scalar_one_or_none()
        if duplicate:
            return jsonify({"success": False, "error": "A client with this ID number already exists in this tenant."}), 409
    record.payload = payload
    record.id_number = id_number
    record.updated_at = now_utc()
    db.session.commit()
    return jsonify({"success": True, "client": client_payload(record)})


@app.post("/api/upload/credit-report")
def upload_credit_report():
    file = request.files.get("file") or request.files.get("creditReport") or request.files.get("pdf")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Choose a PDF credit report first."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Only PDF credit reports are supported."}), 400

    data = file.read()
    if not data.startswith(b"%PDF"):
        return jsonify({"success": False, "error": "The selected file is not a valid PDF."}), 400

    pdf_password = request.form.get("pdfPassword") or None
    use_default = (request.form.get("useDefaultPassword") or "false").lower() == "true"
    try:
        parsed = parse_credit_report(
            data,
            file.filename,
            supplied_password=pdf_password,
            use_default_password=use_default,
        )
    except PdfPasswordRequired as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "code": "PDF_PASSWORD_REQUIRED",
                    "error": "This credit report is password protected.",
                    "passwordRequired": True,
                    "invalidPassword": exc.invalid_password,
                    "companyDefaultAvailable": bool(
                        os.getenv("DEFAULT_CREDIT_REPORT_PDF_PASSWORD")
                    ),
                }
            ),
            423,
        )
    except UnsupportedReport as exc:
        return jsonify({"success": False, "code": "UNSUPPORTED_REPORT", "error": str(exc)}), 422
    except Exception as exc:
        app.logger.exception("Credit report parsing failed")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "The PDF could not be parsed safely.",
                    "detail": str(exc),
                }
            ),
            500,
        )

    parsed_client = parsed["client"]
    id_number = str(parsed_client.get("idNumber") or "").strip() or None
    existing = None
    if id_number:
        existing = db.session.execute(
            db.select(Client).where(
                Client.tenant_id == DEFAULT_TENANT_ID,
                Client.id_number == id_number,
            )
        ).scalar_one_or_none()

    duplicate_prevented = existing is not None
    if existing:
        record = existing
        parsed_client = merge_report_with_existing(dict(record.payload or {}), parsed_client)
    else:
        record = Client(
            id=f"client-{secrets.token_hex(6)}",
            tenant_id=DEFAULT_TENANT_ID,
            id_number=id_number,
            payload={},
            created_by=OPEN_ACCESS_OPERATOR_ID,
            assigned_user_id=OPEN_ACCESS_OPERATOR_ID,
        )
        db.session.add(record)

    report = dict(parsed_client.get("report") or {})
    report["sha256"] = hashlib.sha256(data).hexdigest()
    report["sourceStored"] = bool(REPORT_STORAGE_DIR)
    report["storagePath"] = store_report_if_enabled(
        DEFAULT_TENANT_ID,
        record.id,
        file.filename,
        data,
    )
    parsed_client["report"] = report
    parsed_client = normalize_client_payload(parsed_client)
    record.payload = parsed_client
    record.id_number = parsed_client.get("idNumber") or None
    record.updated_at = now_utc()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "A client with this ID number already exists in this tenant.",
                }
            ),
            409,
        )

    parsed["clientId"] = record.id
    parsed["tenantId"] = DEFAULT_TENANT_ID
    parsed["client"] = client_payload(record)
    parsed["accounts"] = record.payload.get("accounts", [])
    parsed["coach"] = record.payload.get("coach", {})
    parsed["duplicatePrevented"] = duplicate_prevented
    if duplicate_prevented:
        parsed["message"] = (
            "An existing client with this ID number was updated instead of creating a duplicate."
        )
    return jsonify(parsed), 200 if duplicate_prevented else 201


@app.errorhandler(413)
def too_large(_):
    return jsonify({"success": False, "error": "The PDF is larger than 25 MB."}), 413


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "API route not found.", "path": request.path}), 404
    return serve_spa(request.path)


def serve_spa(path: str = ""):
    if not FRONTEND_DIST.exists():
        return (
            jsonify(
                {
                    "app": APP_NAME,
                    "version": APP_VERSION,
                    "status": "frontend-not-built",
                    "hint": "Run npm ci --prefix frontend && npm run build --prefix frontend",
                }
            ),
            200,
        )
    requested = FRONTEND_DIST / path
    if path and requested.is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


@app.get("/")
def frontend_index():
    return serve_spa("")


@app.get("/<path:path>")
def frontend_assets(path: str):
    if path.startswith("api/"):
        return jsonify({"success": False, "error": "API route not found.", "path": f"/{path}"}), 404
    return serve_spa(path)


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
