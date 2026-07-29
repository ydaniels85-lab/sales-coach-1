# Sales Coach and Client Capture update

## Client workflow

A consultant can create a client manually or upload a report first. A successful report upload opens the Client Capture screen automatically. The consultant selects Single or Joint and completes the required personal, contact, address, employment, affordability and banking information.

The backend exposes:

- `POST /api/clients` — create a manual client.
- `GET /api/clients/<client_id>` — retrieve a client.
- `PATCH /api/clients/<client_id>` — save personal, joint and banking details.
- `POST /api/upload/credit-report` — parse and attach/update a protected report.

Captured fields are merged with a later report upload instead of being erased.

## Current Credit Profile Investigation rule

The CPI rule has been expanded. It activates when debt review is not confirmed and either:

- the verified credit score is between 100 and 600 inclusive; and
- there are no active outstanding balances and no debt-review flag.

Pricing returned by the API:

```json
{
  "onceOff": 3000,
  "paymentPlans": [
    { "months": 1, "monthlyAmount": 3000 },
    { "months": 2, "monthlyAmount": 1500 },
    { "months": 3, "monthlyAmount": 1000 },
    { "months": 4, "monthlyAmount": 750 }
  ]
}
```

## Routing precedence

1. Confirmed debt review.
2. Credit Profile Investigation low-score or low-instalment rule.
3. Asset-protection Debt Review rule.
4. Debt Mediation for active balances.
5. Manual Review.

See `SALES_COACH_GOLDEN_QUESTIONS_CPI_UPDATE.md` for the five Golden Questions and objection-handler payloads.
