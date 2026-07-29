# Render SPA Frontend Fix

This build serves the React/Vite frontend from Flask/Gunicorn on Render.

Fixes included:
- Root `/` now serves `backend/frontend_dist/index.html` when the frontend is built.
- `/assets/...` and other static Vite files are served from `backend/frontend_dist`.
- `/api/...` remains backend API and `/api/health` remains the Render health check.
- `gunicorn==23.0.0` added to backend requirements.
- Docker start command uses `python -m gunicorn`.
- Docker npm install uses the public npm registry and ignores the old package-lock during install.

After pushing:
1. Render → Manual Deploy
2. Choose Clear build cache & deploy
3. Open `https://your-service.onrender.com/`
