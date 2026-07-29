# Render environment variables

## Required

- `DATABASE_URL` — supplied automatically by the Render Postgres Blueprint.
- `DEFAULT_CREDIT_REPORT_PDF_PASSWORD` — store as a Render secret. The supplied Datanamix reports use `DN13084`.

## Included defaults

- `OWNER_EMAIL=ydaniels85@gmail.com`
- `DEFAULT_TENANT_ID=khusela-debt-management`
- `DEFAULT_TENANT_NAME=Khusela Debt Management`
- `OPEN_ACCESS_OPERATOR_ID=open-access`
- `WEB_CONCURRENCY=2`
- `GUNICORN_THREADS=4`
- `GUNICORN_TIMEOUT=180`

## Authentication variables

This temporary release does not use login or JWT variables. Old login variables may be removed from Render because the application ignores them.

## Security warning

The current release intentionally uses open access. Restore authentication before using the public URL with live consumer records.
