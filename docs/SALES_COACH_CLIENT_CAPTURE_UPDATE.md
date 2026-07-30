# Sales Coach and Client Capture update

## Client workflow

A consultant can now either create a client manually or upload a report first. A successful report upload opens the Client Capture screen automatically. The consultant selects Single or Joint and completes the required personal, contact, address, employment, affordability and banking information.

The backend exposes:

- `POST /api/clients` — create a manual client.
- `GET /api/clients/<client_id>` — retrieve a client.
- `PATCH /api/clients/<client_id>` — save personal, joint and banking details.
- `POST /api/upload/credit-report` — parse and attach/update a protected report.

Captured fields are merged with a later report upload instead of being erased.

## Credit Profile Investigation rule

The rule checks the sum of `monthlyInstallment` for included accounts. It activates when the sum is greater than zero and below R1,000 and `debtReviewListed` is false.

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
2. Credit Profile Investigation low-instalment rule.
3. Asset-protection Debt Review rule.
4. Debt Mediation for active balances.
5. Manual Review.
