# Fin-Tastic Sales Coach - Product Assessment + Floor Competition Update

This build updates the consultant-facing performance dashboard and product knowledge assessment.

## Main changes

- Product Knowledge assessment is now service/product focused only.
  - Removed tenant/system/technical assessment question.
  - Questions now cover Debt Review, Debt Review Removal, Debt Mediation, NuPay DebiCheck and sales tonality.

- Consultant Dashboard is now a pure competition dashboard with no client details.
  - Individual consultant leaderboard.
  - Team heat board.
  - Entire floor summary.
  - Manager commission snapshot still stores the full scoreboard metrics for review.

- Khusela consultants are grouped into teams:
  - Team Ignite: Consultants 1-3
  - Team Momentum: Consultants 4-6
  - Team Phoenix: Consultants 7-10

- Heat / thermometer scoring added.
  - Every R5,000 in DC value / DRR fees adds a heat block.
  - Heat is shown for each consultant, each team and the entire floor.

## Metrics tracked

- Leads generated / uploaded reports
- Reduced instalment value
- DRR removal fees
- Total DC value
- Documents received
- Admin handovers
- Consultant rank
- Team rank
- Floor total

## Run

```bat
START_ALL.bat
```

If old local data is not showing team fields, restart the backend once. The backend automatically merges the Khusela team fields into the local JSON database.
