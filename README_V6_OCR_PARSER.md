# Fin-Tastic Sales Coach v6 OCR Parser

This version adds OCR fallback for scanned/image-based credit report PDFs.

## Why this is needed

If the parser says:

`No extractable text found in PDF`

then the PDF probably has no text layer. It is an image scan. `pdfplumber` and `PyPDF2` cannot read it safely, so the backend must use OCR.

## Install backend packages

From the backend folder:

```bat
cd /d C:\Users\user\fin-tastic-sales-coach\fin-tastic-sales-coach\backend
venv\Scripts\pip install -r requirements.txt
```

## Install Tesseract OCR on Windows

Try winget first:

```bat
winget install --id UB-Mannheim.TesseractOCR -e
```

Then close CMD and open a new CMD.

Check:

```bat
tesseract --version
```

If Windows says `tesseract is not recognized`, add this folder to PATH:

```txt
C:\Program Files\Tesseract-OCR
```

The backend also checks this path automatically:

```txt
C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Start backend

```bat
cd /d C:\Users\user\fin-tastic-sales-coach\fin-tastic-sales-coach\backend
venv\Scripts\python app.py
```

Open:

```txt
http://127.0.0.1:5000/api/debug/ocr-status
```

You should see:

```json
"tesseractAvailable": true
```

## Start frontend

```bat
cd /d C:\Users\user\fin-tastic-sales-coach\fin-tastic-sales-coach\frontend
npm run dev
```

## Important

OCR will read scanned reports, but OCR is never perfect. If a bureau layout is unusual, the parser may still need a bureau-specific account rule after OCR text is available. Use:

```txt
http://127.0.0.1:5000/api/debug/last-parse
```

to see the OCR text preview and parser warnings.
