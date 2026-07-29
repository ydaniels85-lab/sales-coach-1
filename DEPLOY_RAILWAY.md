# Railway deployment

Deploy the repository root containing `Dockerfile`, `railway.toml`, `backend`, and `frontend`.

- Root Directory: leave blank
- Builder: Dockerfile (automatic from railway.toml)
- Health path: `/api/health`
- Start command: leave blank; Dockerfile supplies Gunicorn

For persistent tenants, clients and uploads, add a Railway Volume mounted at:

`/app/data`

The frontend and backend are served from the same Railway domain. Do not set the frontend API URL to localhost in production.
