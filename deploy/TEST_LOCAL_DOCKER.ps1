$ErrorActionPreference = "Stop"

Write-Host "Building Fin-Tastic open-access Docker image..." -ForegroundColor Cyan
docker build -t fintastic-render-open .

Write-Host "Starting on http://localhost:10000" -ForegroundColor Green
docker run --rm -p 10000:10000 `
  -e DEFAULT_CREDIT_REPORT_PDF_PASSWORD="DN13084" `
  -e DATABASE_URL="sqlite:////app/backend/data/fintastic.db" `
  fintastic-render-open
