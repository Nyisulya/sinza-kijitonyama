# -*- coding: utf-8 -*-
"""Extract text from database 1.pdf using available libraries."""

PDF_PATH = r"C:\Users\felic\Downloads\database 1.pdf"
OUT_PATH = r"D:\projects\django1\sinza na kijitonyama\database1_text.txt"

extracted = []

# Try pymupdf (fitz)
try:
    import fitz
    doc = fitz.open(PDF_PATH)
    extracted.append(f"=== PyMuPDF: {doc.page_count} pages ===")
    for i, page in enumerate(doc):
        text = page.get_text()
        extracted.append(f"\n----- PAGE {i+1} -----\n{text}")
except ImportError:
    extracted.append("PyMuPDF not installed")

if not extracted or len(extracted) == 1:
    # Try PyPDF2 / pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(PDF_PATH)
        extracted.append(f"\n=== pypdf: {len(reader.pages)} pages ===")
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            extracted.append(f"\n----- PAGE {i+1} -----\n{text}")
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(PDF_PATH)
            extracted.append(f"\n=== PyPDF2: {len(reader.pages)} pages ===")
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                extracted.append(f"\n----- PAGE {i+1} -----\n{text}")
        except ImportError:
            extracted.append("pypdf/PyPDF2 not installed")

# Try pdfplumber as last resort
if len(extracted) <= 2:
    try:
        import pdfplumber
        with pdfplumber.open(PDF_PATH) as pdf:
            extracted.append(f"\n=== pdfplumber: {len(pdf.pages)} pages ===")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                extracted.append(f"\n----- PAGE {i+1} -----\n{text}")
    except ImportError:
        extracted.append("pdfplumber not installed")

full_text = "\n".join(extracted)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"Extracted {len(full_text)} characters -> {OUT_PATH}")
print(full_text[:3000])
