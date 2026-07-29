FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

# Tesseract is needed for scanned/image-only Datanamix reports.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates nodejs npm tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --root-user-action=ignore --no-cache-dir --upgrade pip \
    && pip install --root-user-action=ignore --no-cache-dir -r /app/backend/requirements.txt

COPY frontend/package.json /app/frontend/package.json
WORKDIR /app/frontend
RUN npm config set registry https://registry.npmjs.org/ \
    && npm config delete proxy || true \
    && npm config delete https-proxy || true \
    && npm install --registry=https://registry.npmjs.org/ --package-lock=false --no-audit --no-fund --fetch-retries=5 --fetch-timeout=600000

COPY frontend /app/frontend
RUN npm run build

COPY backend /app/backend
RUN mkdir -p /app/backend/frontend_dist \
    && cp -r /app/frontend/dist/* /app/backend/frontend_dist/

WORKDIR /app/backend
EXPOSE 5000
CMD ["sh", "-c", "python -m gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 180 app:app"]
