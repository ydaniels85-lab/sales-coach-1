# Fin-Tastic Sales Coach

A lighter consultant-facing app for opening and closing debt-service sales.

This app is intentionally separate from `fin-tastic-enterprise`.

## What it does

- Uploads and parses PDF credit reports
- Detects debt review flags, balances, arrears, score, dates and likely sales opportunities
- Gives the consultant a sales coach script for opening, objections and closing
- Sends/creates placeholder signature link
- Sends/creates placeholder document upload link
- Sends/creates placeholder NuPay mandate request
- Passes a closed sale to admin for workflow/PDA processing

## Important compliance note

The app avoids saying debt mediation will guarantee or influence a judge. The built-in compliant wording is:

> Debt mediation can support the debt review removal application by showing that the client has a realistic plan for remaining balances, improved affordability, and creditor engagement. The final decision remains with the court or relevant legal process.

## Run locally on Windows

### Backend

```bat
cd backend
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend will run on:

```text
http://localhost:5000
```

### Frontend

Open a second terminal:

```bat
cd frontend
npm install
npm run dev
```

Frontend will run on:

```text
http://localhost:5173
```

## Quick Windows start files

You can also use:

```bat
run_backend.bat
run_frontend.bat
```

## Backend endpoints

```text
GET  /api/health
GET  /api/debug/routes
POST /api/upload/credit-report
GET  /api/leads
GET  /api/leads/<lead_id>
POST /api/leads
POST /api/leads/<lead_id>/send-signature-link
POST /api/leads/<lead_id>/send-document-link
POST /api/leads/<lead_id>/send-nupay-mandate
POST /api/leads/<lead_id>/close-sale
POST /api/leads/<lead_id>/pass-to-admin
GET  /api/admin/handoffs
```

## NuPay integration

`backend/services/mandate_service.py` is a safe placeholder adapter. It does not call NuPay yet. Replace the mock method with your real NuPay/DebiCheck API once you have merchant credentials and documentation.

## Signature and document links

`backend/services/link_service.py` creates local demo portal links. Replace these with your real e-sign provider or client portal when ready.
