# Fin-Tastic Sales Coach — Render Deployment

This build is prepared for Render using a single Docker web service.

## What Render will run

- Builds the React frontend with `npm ci && npm run build`
- Copies the built frontend into `backend/frontend_dist`
- Runs Flask with Gunicorn
- Serves the app and API from one service
- Includes Tesseract OCR for scanned Datanamix PDFs
- Uses `/api/health` as the health check

## Required files added

- `render.yaml` — Render Blueprint configuration
- `Dockerfile` — production build/runtime
- `.dockerignore` — keeps the deploy clean

## Deploy from GitHub

1. Push this folder to GitHub.
2. Open Render.
3. Choose **New +** → **Blueprint**.
4. Connect the GitHub repository.
5. Render will read `render.yaml` from the root.
6. Deploy the service.

## Persistent storage

The Blueprint includes a persistent disk mounted at:

```text
/var/data
```

The app stores data using:

```text
DATA_DIR=/var/data/data
UPLOAD_DIR=/var/data/uploads
```

This keeps the local JSON database and uploaded client documents/signatures outside the container filesystem.

## Health check

After deployment, test:

```text
https://YOUR-RENDER-SERVICE.onrender.com/api/health
```

You should see JSON with `success: true` and `status: ok`.

## Local Docker test

From the project root:

```bash
docker build -t fin-tastic-sales-coach .
docker run --rm -p 5000:5000 -e PORT=5000 -e FLASK_DEBUG=0 fin-tastic-sales-coach
```

Open:

```text
http://localhost:5000
```

## Important notes

- Do not deploy only the frontend as a Render Static Site, because the backend handles parsing, tenant isolation, client uploads, portal links, DebiCheck links, admin workflow and dashboards.
- Use the Docker web service so backend and frontend stay together.
- For production, move from local JSON storage to Postgres later if you want stronger multi-user durability and backup controls.
