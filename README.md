# Fin-Tastic Sales Coach - Separate DebiCheck + Vibe Dashboard

This build updates the consultant dashboard for more motivation/healthy competition and changes NuPay so the consultant can send separate DebiChecks where applicable.

## What changed

### Consultant dashboard

- Dashboard remains performance-only with no client names, IDs, phone numbers or case details.
- Added a higher-energy **Khusela Growth League** layout.
- Added motivational chips, daily mission cards and a stronger top-three podium.
- Leaderboard still ranks consultants by:
  - leads generated / uploaded reports
  - DC value
  - reduced instalment value
  - DRR fees
  - documents received
  - admin handovers
  - performance score

### NuPay DebiCheck

The Banking / NuPay tab now separates the two different collections:

1. **Removal DebiCheck**
   - Used only when Debt Review Removal applies.
   - Collects the R7,000 DRR removal service fee.
   - Consultant can split it over 1, 2 or 3 months.
   - Consultant can choose a separate debit order start date.

2. **Mediation DebiCheck**
   - Used only when Debt Mediation / reduced payment applies.
   - Collects the ongoing monthly reduced payment.
   - No 1/2/3 month split is shown for mediation.
   - Consultant can choose a separate debit order start date.

For DRR + Mediation double-sale clients, the consultant can send both DebiChecks separately.

## New backend routes

```text
POST /api/clients/<client_id>/mandates/removal/send
POST /api/clients/<client_id>/mandates/removal/cancel
GET  /api/clients/<client_id>/mandates/removal/status

POST /api/clients/<client_id>/mandates/mediation/send
POST /api/clients/<client_id>/mandates/mediation/cancel
GET  /api/clients/<client_id>/mandates/mediation/status
```

## New public portal routes

```text
GET/POST /portal/<tenant_id>/nupay-removal/<client_id>/<token>
GET/POST /portal/<tenant_id>/nupay-mediation/<client_id>/<token>
```

## Run

```bat
START_ALL.bat
```

## Restart fully after replacing files

```bat
taskkill /F /IM python.exe
taskkill /F /IM node.exe
START_ALL.bat
```

Then hard refresh the browser with `Ctrl + F5`.
