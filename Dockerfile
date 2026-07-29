# Stable frontend build image. Vite 7 requires Node 20.19+ or 22.12+.
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /build/frontend

ENV npm_config_registry=https://registry.npmjs.org/ \
    npm_config_audit=false \
    npm_config_fund=false \
    npm_config_update_notifier=false \
    npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=20000 \
    npm_config_fetch_retry_maxtimeout=120000

# Copy dependency manifests first so Render can cache this layer.
COPY frontend/package.json frontend/package-lock.json ./

# Retry transient npm/network failures, but fail the image if all attempts fail.
RUN set -eux; \
    node --version; \
    npm --version; \
    for attempt in 1 2 3; do \
      if npm ci --include=dev --no-audit --no-fund; then \
        break; \
      fi; \
      if [ "$attempt" -eq 3 ]; then \
        echo "npm ci failed after 3 attempts" >&2; \
        exit 1; \
      fi; \
      echo "npm ci attempt $attempt failed; retrying..." >&2; \
      sleep $((attempt * 10)); \
    done

COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

RUN useradd --create-home --uid 10001 fintastic \
    && mkdir -p /app/backend/data \
    && chmod +x /app/backend/start.sh \
    && chown -R fintastic:fintastic /app
USER fintastic

EXPOSE 10000
CMD ["/app/backend/start.sh"]
