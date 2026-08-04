FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FINTASTIC_DATA_DIR=/app/data \
    FINTASTIC_UPLOAD_DIR=/app/data/uploads
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app.py ./app.py
COPY --from=frontend-build /build/frontend/dist ./frontend_dist
RUN mkdir -p /app/data/uploads
EXPOSE 8080
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 180"]
