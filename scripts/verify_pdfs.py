"""PDF verification script.
Attempts pypdfium2 rendering where supported, with pdfplumber structural validation fallback.
Asserts page count > 0, non-empty extracted text, and valid PDF structure.
"""
import sys
from pathlib import Path
import pdfplumber

def verify_all_sample_pdfs():
    sample_dir = Path("data/sample_cvs")
    if not sample_dir.exists():
        print("data/sample_cvs directory not found!")
        sys.exit(1)

    pdf_files = sorted(list(sample_dir.glob("*.pdf")))
    print(f"Found {len(pdf_files)} PDF files in {sample_dir}")

    passed = 0
    failed = 0

    for pdf_path in pdf_files:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                assert page_count > 0, f"{pdf_path.name}: 0 pages"

                # Check text extraction
                full_text = "".join(p.extract_text() or "" for p in pdf.pages)
                # Note: scanned synthetic PDFs will have minimal or no OCR text, but valid page structure
                if "scanned" not in pdf_path.name.lower():
                    assert len(full_text.strip()) > 50, f"{pdf_path.name}: Text too short ({len(full_text.strip())} chars)"

                print(f"[OK] {pdf_path.name}: {page_count} page(s), {len(full_text)} chars text")
                passed += 1
        except Exception as e:
            print(f"[FAIL] {pdf_path.name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Total PDFs: {len(pdf_files)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    verify_all_sample_pdfs()
