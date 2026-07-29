# Fin-Tastic Sales Coach v5 — Reviewed + Fixed

This version fixes the issues reported in v4:

## Fixed

- Consultant view now has a clear **Sales Coach Recommendation** panel.
- If parser misses client name, the UI shows **Name not parsed — capture manually** instead of a blank name.
- Consultant can manually capture the client name and all important client details.
- Admin view has a better layout with tabs:
  - Overview
  - Docs
  - Forms
  - Generated documents
  - Creditors
  - PDA
  - Court
- Admin can generate and view document previews for:
  - Form 17.1
  - Form 17.2
  - Form 17.3
  - Form 19
  - Court / removal pack
  - NuPay mandate record
  - Client one-link record
- The one signature + document link now works locally.
  - It creates a link like `http://localhost:5173/portal/<client-id>?token=...`
  - Opening the link shows a client portal page.
  - Client can submit signature and upload/mark documents.
  - Admin can see those statuses in the back office.
- Consultant can still:
  - upload credit report
  - view accounts
  - include/exclude accounts
  - edit reduced installment
  - select service
  - send NuPay mandate
  - send one sig/docs link
  - pass sale to admin

## Run

Frontend:

```bat
cd C:\Users\user\fin-tastic-sales-coach
npm install
npm run dev
```

Backend parser:

```bat
cd C:\Users\user\fin-tastic-sales-coach\backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python app.py
```

Open:

```txt
http://localhost:5173
```

## Important parser note

The parser is safer now because the frontend does **not** invent fake accounts. If the parser cannot confidently find the client name or accounts, it shows warnings and lets the consultant capture the missing fields manually.

To debug parser output:

```txt
http://localhost:5000/api/debug/last-parse
```
