# Sales Opportunity Engine routing matrix

| Priority | Conditions | Primary recommendation | Additional recommendation |
|---:|---|---|---|
| 1 | Credit score exactly 0 | Debt Review Removal | Debt Mediation when balances remain |
| 2 | Confirmed debt-review flag | Debt Review Removal | Debt Mediation when balances remain |
| 3 | No flag, score 100–600, no balances | Credit Profile Investigation | None |
| 4 | No flag, active home/vehicle finance | Debt Review | None |
| 5 | No flag, other active balances | Debt Mediation | None |
| 6 | No rule matches | Manual Review | None |

Balances are calculated from included accounts with a positive current balance. Rule priority prevents a score-zero client from being routed to CPI and prevents a client with active balances from being routed to CPI.
