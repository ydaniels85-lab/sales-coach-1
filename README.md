# Fin-Tastic Render — Credit Score Routing Repair

This complete open-access Render build for **Khusela Debt Management** keeps the encrypted Datanamix parser, client capture and banking workflow, and expands the Sales Coach into a guided consultant conversation tool.


## Credit score repair in this build

The credit-score parser no longer accepts the first three-digit number near the score area. It now ranks labelled candidates, prioritises the **Final Score** column, ignores score-band scales and dates, and exposes the matched text and confidence to the consultant.

The Client Capture screen includes a score-verification panel. A consultant can correct the score manually when a new bureau layout is unclear; saving the correction immediately recalculates the CPI and other Sales Coach rules.

Validated results:

- `REF2788037.pdf`: **553**, 99% confidence.
- `REF2788225.pdf`: **566**, 99% confidence.

## Included workflow

- React/Vite frontend built into the Flask Docker image.
- Render Postgres client storage.
- Manual **New client** creation and editable client records.
- Single or joint application selection.
- Primary and spouse/co-applicant personal, contact, address, employment, affordability and banking information.
- Capture-completion percentage.
- Captured details remain in place when the same client’s report is uploaded again.
- Duplicate ID prevention inside the tenant.
- Password-protected PDF prompt with the server-side default password option.
- Datanamix identity, labelled Final Score, score confidence/source, debt-review status, CPA/NLR accounts, balances, arrears and instalments.
- Manual score verification with immediate Sales Coach recalculation.

## 5 Golden Questions

The Sales Coach now includes an interactive Yes/No checklist. Each question explains why it matters:

1. Are you 18 years or older and a South African citizen?
2. Do you bank with one of South Africa’s major banks?
3. Is your cellphone number linked to your bank account?
4. Is a Debt Counsellor or creditor currently debiting your bank account?
5. Are you employed or receiving a regular income into your bank account?

A No answer does not automatically disqualify the client. The consultant must verify the reason, correct the captured details and choose the appropriate compliant next step.

## Sales Opportunity routing rules

The Sales Opportunity Engine now uses this exact order:

1. **Credit score exactly 0** → recommend **Debt Review Removal**.
2. If the score is 0 and active balances remain → also recommend **Debt Mediation**.
3. A confirmed debt-review flag → recommend **Debt Review Removal**; active balances also add **Debt Mediation**.
4. No debt-review flag + score from **100 through 600** + **no active balances** → recommend **Credit Profile Investigation**.
5. No debt-review flag + active home-loan or vehicle-finance balance → recommend **Debt Review**.
6. No debt-review flag + other active balances → recommend **Debt Mediation**.
7. Anything else → manual review.

CPI is no longer triggered only because instalments are below R1,000, and a score from 601–649 does not automatically create a CPI sale.

The CPI opportunity displays:

- Total fee: **R3,000**
- Once-off: R3,000
- 2 months: R1,500 per month
- 3 months: R1,000 per month
- 4 months: R750 per month

## More informative Sales Coach

Each product route now contains:

- A suggested opening script.
- Clear reasons for the recommendation.
- Five product-specific qualifying questions.
- Consultant next steps.
- Product-specific client objections and suggested responses.
- CPI pricing and payment options when applicable.

Objection handling is included for Credit Profile Investigation, Debt Review, Debt Review Removal, Debt Mediation and Manual Review. The responses avoid guaranteed outcomes and require verified report data and supporting documents.

## Routing precedence

1. Exact score 0 or confirmed debt-review flag → Debt Review Removal.
2. Removal route with active balances → add Debt Mediation.
3. No debt-review flag + score 100–600 + no balances → Credit Profile Investigation.
4. No debt-review flag + financed-asset balance → Debt Review.
5. No debt-review flag + other active balances → Debt Mediation.
6. No safe automatic route → Manual Review.

## Deploy to Render

1. Extract this ZIP.
2. Replace all files in the private Git repository.
3. Commit and push.
4. Keep this Render environment variable:

   `DEFAULT_CREDIT_REPORT_PDF_PASSWORD=DN13084`

5. Select **Manual Deploy → Clear build cache & deploy**.
6. Open `https://YOUR-RENDER-URL/api/health`.
7. Confirm `databaseReady` is `true` and `authenticationRequired` is `false`.

No database migration is required because Sales Coach data is generated from the stored client/report payload.

## Important open-access warning

Logins remain disabled as requested. Anyone who knows the Render URL can view or change stored client information. Do not expose the service publicly with real consumer records until authentication is restored.

## Validation completed

- Clean `npm ci` using the public npm registry.
- TypeScript validation and Vite production build.
- Python compilation and Flask API smoke tests.
- Exact score 0 with no balances → Debt Review Removal.
- Exact score 0 with balances → Debt Review Removal plus Debt Mediation.
- Confirmed debt-review flag with balances → Debt Review Removal plus Debt Mediation.
- Scores 100 and 600 with no balances and no flag → CPI.
- Score 601 with no balances → Manual Review.
- Score 500 with balances → Debt Mediation, not CPI.
- Instalments below R1,000 no longer trigger CPI on their own.
- CPI payment values: R3,000 / R1,500 / R1,000 / R750.
- `REF2788037.pdf`: score 553, 5 accounts, R2,344 active balance, routed to Debt Mediation.
- `REF2788225.pdf`: score 566, 9 accounts, R33,119 active balance, routed to Debt Mediation.
- Protected PDF unlock and parsing with `DN13084`.
