# Golden Questions, objections and revised opportunity routing

## Current routing expression

```text
Removal = debtReviewListed is true OR creditScore equals 0
Mediation add-on = Removal is true AND active outstanding balances are greater than 0
CPI = debtReviewListed is false
      AND creditScore is between 100 and 600 inclusive
      AND active outstanding balances equal 0
```

Low monthly instalments do not independently trigger CPI.

Every `coach` object includes `additionalServices`. When a Removal client still has balances, this array contains `Debt Mediation` and the frontend displays an additional-recommendation warning.

## Five Golden Questions

1. Age 18+ and South African citizenship.
2. Banking with a major South African bank.
3. Cellphone number linked to the bank account.
4. Current Debt Counsellor or creditor debit orders.
5. Employment or regular income paid into the bank account.

## Objection handling

The API returns tailored objection handling for CPI, Debt Review Removal, Debt Review, Debt Mediation and Manual Review. Responses do not guarantee outcomes.
