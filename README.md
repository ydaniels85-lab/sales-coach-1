# Fin-Tastic Render — Sales Coach and client capture update

This is the complete open-access Render build for **Khusela Debt Management**. It keeps the encrypted Datanamix PDF parser and adds the client information and Sales Coach workflow that consultants need after a report is parsed.

## What is included

- React/Vite frontend built into the Flask Docker image.
- Render Postgres client storage.
- Manual **New client** creation.
- Editable client records after parsing.
- Single or joint application selector.
- Primary applicant and spouse/co-applicant capture.
- Personal, contact and physical-address details.
- Employer, occupation, date employed and salary frequency.
- Gross salary, nett salary and monthly household budget/living expenses.
- Banking capture for the primary and joint applicant:
  - Account holder
  - Bank name
  - Account type
  - Branch code
  - Account number
  - Preferred debit-order day
- Capture-completion percentage.
- Captured information is preserved when the same client's credit report is uploaded again.
- Duplicate ID prevention inside the tenant.
- Password-protected PDF prompt and secure server-side default password option.
- Datanamix identity, score, debt-review status, CPA/NLR accounts, balances, arrears and instalments.
- Expanded Sales Coach with a suggested opening, reasons, qualifying questions, next steps and responsible objection handling.

## Credit Profile Investigation opportunity rule

The Sales Opportunity Engine now routes to **Credit Profile Investigation** when:

1. The report does **not** confirm that the client is under debt review; and
2. The total monthly instalments of included active accounts are greater than R0 but **less than R1,000 per month**.

The opportunity displays:

- Service: Credit Profile Investigation
- Headline: Potential Credit Profile Investigation sale
- Total fee: **R3,000**
- Once-off: R3,000
- 2 months: R1,500 per month
- 3 months: R1,000 per month
- 4 months: R750 per month

Confirmed debt-review status still takes priority and routes to Debt Review Removal. A credit score of zero alone does not trigger Removal.

## Existing service routing

- Confirmed debt-review listing → Debt Review Removal.
- Not under debt review + instalments below R1,000 → Credit Profile Investigation.
- Not under debt review + home-loan/vehicle-finance asset trigger → Debt Review.
- Not under debt review + active balances → Debt Mediation.
- No safe automatic route → Manual Review.

## Deploy to the current Render service

1. Extract this ZIP.
2. Replace all files in your private Git repository.
3. Commit and push.
4. In Render, confirm the secret environment variable:

   `DEFAULT_CREDIT_REPORT_PDF_PASSWORD=DN13084`

5. Select **Manual Deploy → Clear build cache & deploy**.
6. Open `https://YOUR-RENDER-URL/api/health`.
7. Confirm `databaseReady` is `true` and `authenticationRequired` is `false`.

No database schema migration is required for this update because the new client fields are stored in the existing JSON client payload.

## Important open-access warning

Logins are still disabled as requested. Anyone who knows the Render URL can view or change stored client information. This is temporary and should not be exposed publicly with real consumer records.

## Local development

Backend:

```powershell
$env:DATABASE_URL="sqlite:///C:/absolute/path/fintastic.db"
$env:DEFAULT_CREDIT_REPORT_PDF_PASSWORD="DN13084"
python -m backend.scripts.init_db
python -m backend.app
```

Frontend in another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

## Validation

The package was validated with:

- `npm ci`
- TypeScript compile validation
- Vite production build
- Python compilation
- Manual client creation
- Single/joint application save
- Primary and spouse banking save
- Duplicate ID protection
- Re-upload preservation of captured details
- Credit Profile Investigation rule and all four payment options
- `REF2788037.pdf` with password `DN13084`: 5 accounts
- `REF2788225.pdf` with password `DN13084`: 9 accounts
