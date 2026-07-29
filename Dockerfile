# Node 24 LTS avoids the npm 10.9.x / Node 22 Docker "Exit handler never called" failure.
FROM node:24-bookworm-slim AS frontend-build

ENV NPM_CONFIG_REGISTRY=https://registry.npmjs.org/ \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_PROGRESS=false

WORKDIR /build/frontend

# Intentionally copy only package.json. The supplied lockfile was generated
# against a private build registry, so Railway must not use it.
COPY frontend/package.json ./package.json
RUN npm install --include=dev --no-audit --no-fund --foreground-scripts

COPY frontend/index.html ./index.html
COPY frontend/tsconfig.json ./tsconfig.json
COPY frontend/vite.config.ts ./vite.config.ts
COPY frontend/src ./src
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINTASTIC_DATA_DIR=/app/data \
    FINTASTIC_UPLOAD_DIR=/app/data/uploads

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app.py ./app.py
COPY --from=frontend-build /build/frontend/dist ./frontend_dist
RUN mkdir -p /app/data/uploads

EXPOSE 8080
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 300"]
