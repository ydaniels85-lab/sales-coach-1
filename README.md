# Fin-Tastic Sales Coach — Refined Sales-to-Admin Workflow

This is a complete local development build for **fin-tastic-sales-coach**.

## What is included

- Tenant-isolated database: each tenant has its own users, clients, uploads, documents, mandates, admin queue and PDA records.
- Users inside the same tenant see the same tenant client list and database.
- Sales consultant flow:
  - Added top workflow tabs under the header: Client Info, Credit Report, Sales Coach, Accounts/Fees, Docs/Signature, NuPay Mandate and Admin/PDA.
  - Added a global **Save Client** button and visible save status so captured client info is saved from any screen.
  1. Upload credit report.
  2. Sales Opportunity Engine determines the best route:
     - Debt Review Sales Coach
     - Debt Review Removal
     - Debt Mediation
     - Manual Review
  3. Sales Coach gives selling points, next steps and objection handling.
  4. Reduced amount is calculated and compared to original instalments.
  5. Consultant sends upload-documents link, signature link and NuPay mandate.
  6. Consultant views mandate status, cancels mandate, or sends a new mandate.
  7. Consultant submits the client to admin.
- Admin flow:
  - View submitted clients.
  - See uploaded documents, signature status, fees, reduced amounts, included creditors, NuPay mandate and PDA info.
  - Cancel mandate and send a new one if details change.
  - Capture PDA reference, proposal amount, payment start date and PDA status.

## Run the app

From this folder:

```bat
START_ALL.bat
```

Then open:

```text
http://localhost:5173
```

Manual start:

```bat
RUN_BACKEND.bat
RUN_FRONTEND.bat
```

## Backend

The Flask backend runs on:

```text
http://localhost:5000
```

Important API rule:

```text
X-Tenant-ID: liberty-credit-specialists
X-User-ID: lib-agent-1
```

Every client/document/mandate/admin/PDA route is scoped by `X-Tenant-ID`.

## Main backend routes

```text
GET    /api/tenants
GET    /api/users
GET    /api/clients
POST   /api/clients
PUT    /api/clients/<client_id>
POST   /api/upload/credit-report
POST   /api/clients/<client_id>/documents/request
POST   /api/clients/<client_id>/documents/upload
POST   /api/clients/<client_id>/signature/send
POST   /api/clients/<client_id>/signature/mark-signed
POST   /api/clients/<client_id>/mandate/send
GET    /api/clients/<client_id>/mandate/status
POST   /api/clients/<client_id>/mandate/cancel
POST   /api/clients/<client_id>/mandate/resend
PUT    /api/clients/<client_id>/pda
POST   /api/clients/<client_id>/admin-submit
GET    /api/admin/clients
GET    /api/debug/routes
```

## Local database

```text
backend/data/sales_coach_db.json
```

Uploads are saved under:

```text
backend/uploads/<tenant_id>/
backend/uploads/<tenant_id>/client_docs/<client_id>/
```

## Notes

- NuPay and PDA are implemented as API-ready workflow placeholders. They store mandate status, reference, amount and handover data locally now. When you receive live API credentials/specs, replace the placeholder send/cancel actions with the real API calls.
- Parser cleanup update: the backend now ignores common summary/header/noise rows such as "Total No. of accounts", enquiry rows, payment-profile rows, date rows, and weak non-creditor fragments. It also tries PDF table extraction before line-by-line fallback parsing.
- Accounts screen cleanup update: the accounts table now has a sticky header, sticky include/creditor columns, better column widths, and a **Clean Bad Rows** button for quickly removing obvious parser noise.
- The parser is still a safe baseline. Bureau-specific Datanamix/XDS/TransUnion/Experian/Compuscan parsing rules can still be improved once you test more reports.

## Parser fix in this version

- Added XDS-style name extraction for reports where fields are displayed as `First Name`, `Second Name`, `Surname`, `ID No.`, `Residential Address`, `Current Employer`, etc.
- Added separate first name, second name and surname fields to the client profile screen.
- Fixed the XDS account money-column order: `Open Balance`, `Current Balance`, `Instalment Amount`, `Arrears Amount`.
- Fixed false Debt Review detection where a report only says `Debt Review Status * Nothing on Record`.
- Added stricter XDS account row parsing for rows that wrap across lines.

If old bad figures are still showing after replacing files, reset or clean the local database:

```bat
backend\data\sales_coach_db.json
```

Delete that file only if you want to remove existing local test clients and start fresh.


## Save-client fix in this version

- New local clients are saved with `POST /api/clients`; existing clients update with `PUT /api/clients/<client_id>`.
- The frontend now replaces the temporary `local-*` ID with the saved backend client ID immediately after saving.
- The backend now preserves first name, second name, surname, DOB, gender, marital status, spouse details and banking fields.
- Portal links, document links and NuPay actions now first save the client and then use the real saved client ID.
- A top **Save Client** button is available on every workflow tab.

## Login, upload and data-integrity fix in this version

This build fixes the issues where the app appeared to switch between admin/consultant and where uploading a new credit report could overwrite or show the previous selected client.

Changes made:

- Added a login/session screen. The tenant and user are selected once when entering the workspace.
- Removed the live tenant/user dropdowns from the top bar so the role does not change while working.
- Added a **Switch / Logout** button for intentionally changing tenant/user.
- Client list refresh and search no longer changes the active client. A client changes only when you click it, create a new one, or upload a report.
- Credit report upload now has two clear modes:
  - **Upload as NEW client** — safe default and always creates a new client.
  - **Replace credit report for selected saved client** — only updates the selected saved client.
- Backend safety rule: `POST /api/upload/credit-report` always creates a new client, even if a stale `clientId` is sent by mistake.
- Existing-client report replacement must use `POST /api/clients/<client_id>/credit-report/upload`.
- Admin queue is protected by role. Only Admin and Manager users can open `/api/admin/clients`.
- Unknown/missing credit score is no longer treated as score `0`. Score-zero DRR routing only applies when the parser actually found a score of `0`.
- `Debt Review Status: Nothing on Record` no longer triggers a debt-review sale by itself.
- Uploaded/manual document records are preserved even when the service route changes.

Recommended after replacing files:

```bat
rmdir /s /q backend\data
rmdir /s /q backend\uploads
START_ALL.bat
```

Only delete `backend\data` if you want a clean local test database.

## Parser strictness update in this version

This build tightens the parser because the previous version was still importing payment-profile and history rows as accounts.

Changes made:

- The generic line parser no longer imports unknown creditor rows. It only uses generic line fallback when a known creditor name is found.
- The table parser now rejects payment-profile/history tables and requires clearer balance columns.
- `Current Status` is no longer mistaken for `Current Balance`.
- Unknown table creditor names must contain a finance/store/service-style signal before they are imported.
- XDS reports prefer the XDS text parser over pdfplumber table rows when XDS rows are detected.
- Name extraction has been improved for `Consumer Name`, `Client Name`, `Full Names`, `First Name`, `Second Name`, and `Surname` layouts.
- The accounts screen now displays a warning that parsed accounts must be verified before admin/PDA handover.

Important: after replacing files, reset your local test database or old wrong rows will still show:

```bat
rmdir /s /q backend\data
rmdir /s /q backend\uploads
START_ALL.bat
```

Do this only for local testing because it deletes saved local test clients and uploads.

## Datanamix scanned-PDF OCR fix in this version

This build fixes Datanamix reports that contain page images instead of embedded PDF text.

- Added OCR fallback for scanned/image-only PDFs using Tesseract + pypdfium2.
- Added a Datanamix-specific parser for:
  - First name, surname, ID number, birth date, gender, marital status, phone, address and employer.
  - Final score and debt-review flag.
  - Debt counsellor name, telephone number, NCR registration number and debt-review status date.
  - Consumer account status blocks: subscriber name, account number, current balance, instalment, arrears, opening balance/credit limit, account type, last paid date, open date and account status.
- Datanamix payment-history grids are ignored so they are not imported as creditor accounts.
- Scanned Datanamix reports skip pdf table extraction because it is slow and unreliable on image-only pages.

For OCR to work on Windows, Tesseract OCR must be installed. If needed, install it with:

```bat
winget install UB-Mannheim.TesseractOCR
```

If Windows does not detect it after installation, restart CMD/PowerShell or add this folder to PATH:

```text
C:\Program Files\Tesseract-OCR
```
