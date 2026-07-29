@echo off
echo Checking Python OCR packages...
venv\Scripts\python -c "import fitz, pytesseract, PIL; print('Python OCR packages OK'); print('Tesseract cmd:', pytesseract.pytesseract.tesseract_cmd); print('Tesseract version:', pytesseract.get_tesseract_version())"
echo.
echo Checking backend OCR status endpoint. Backend must be running for this line to work.
curl http://127.0.0.1:5000/api/debug/ocr-status
echo.
pause
