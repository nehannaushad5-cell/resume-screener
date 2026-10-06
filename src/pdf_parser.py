"""PDF text extraction module using PyMuPDF (fitz) with robust error handling."""

import io
import re
from typing import List, Tuple, Union
try:
    import pymupdf as fitz
except ImportError:
    import fitz



def extract_text_from_pdf(
    pdf_source: Union[str, bytes, io.BytesIO], filename: str = "document.pdf"
) -> Tuple[str, List[str]]:
    """
    Extract readable text from a PDF source (filepath, bytes, or BytesIO buffer).

    Returns:
        Tuple of (extracted_text, list_of_warnings).
        If an error or empty document is encountered, extracted_text is empty string,
        and appropriate warning messages are included.
    """
    warnings: List[str] = []
    text_content = ""

    # Check for empty input
    if pdf_source is None:
        warnings.append(f"'{filename}' was empty or null.")
        return "", warnings

    try:
        # Open PDF from bytes or file path
        if isinstance(pdf_source, (bytes, bytearray)):
            if len(pdf_source) == 0:
                warnings.append(f"'{filename}' has 0 bytes (empty file).")
                return "", warnings
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        elif isinstance(pdf_source, io.BytesIO):
            data = pdf_source.getvalue()
            if len(data) == 0:
                warnings.append(f"'{filename}' has 0 bytes (empty file).")
                return "", warnings
            doc = fitz.open(stream=data, filetype="pdf")
        elif isinstance(pdf_source, str):
            doc = fitz.open(pdf_source)
        elif hasattr(pdf_source, "read"):
            data = pdf_source.read()
            if hasattr(pdf_source, "seek"):
                pdf_source.seek(0)
            if len(data) == 0:
                warnings.append(f"'{filename}' has 0 bytes (empty file).")
                return "", warnings
            doc = fitz.open(stream=data, filetype="pdf")
        else:
            warnings.append(f"Unsupported source format for '{filename}'.")
            return "", warnings

        # Validate page count
        if doc.page_count == 0:
            warnings.append(f"'{filename}' contains 0 pages.")
            doc.close()
            return "", warnings

        # Extract text from each page
        pages_text: List[str] = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text") or ""
            pages_text.append(page_text)

        doc.close()

        raw_text = "\n".join(pages_text).strip()

        # Check if text was extractable
        if not raw_text:
            warnings.append(
                f"'{filename}' contains no extractable selectable text (it may be a scanned image or empty). OCR is required to parse scanned documents."
            )
            return "", warnings

        # Text cleaning and normalization
        text_content = clean_extracted_text(raw_text)

    except fitz.FileDataError as e:
        warnings.append(f"'{filename}' is corrupted or not a valid PDF file: {str(e)}")
        return "", warnings
    except Exception as e:
        warnings.append(f"Unexpected error parsing '{filename}': {str(e)}")
        return "", warnings

    return text_content, warnings


def clean_extracted_text(text: str) -> str:
    """Normalize whitespace, remove carriage returns, and heal hyphenated line breaks."""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Heal hyphenated words split across lines (e.g. 'analyt-\nics' -> 'analytics')
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Remove control characters except standard whitespace
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
    # Collapse 3 or more blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
