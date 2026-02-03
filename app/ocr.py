"""
ocr.py
This module handles Optical Character Recognition (OCR) for both equipment nameplate
images and technical submittal PDFs. It abstracts the details of calling the
underlying OCR engine and normalises output into a convenient structure with
coordinates and page numbers to support downstream explainability.

Requirements:
    - The module expects `pytesseract` and `pdfplumber` to be installed.
    - Tesseract OCR must be available on the system for `pytesseract` to work.

If these dependencies are missing, the extraction functions will raise
`ImportError`. See the `README` or deployment notes for instructions on
installing the necessary packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import io
import os

try:
    from PIL import Image
    import pytesseract
    import pdfplumber
except ImportError as exc:  # pragma: no cover
    # The actual import error is raised when functions are called.
    PIL = None  # type: ignore
    pytesseract = None  # type: ignore
    pdfplumber = None  # type: ignore


@dataclass
class OCRWord:
    """Represents a recognised word from OCR with its location and confidence."""

    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    page_num: int


def ocr_image(image_bytes: bytes) -> List[OCRWord]:
    """Perform OCR on a nameplate image.

    Args:
        image_bytes: The raw bytes of the uploaded image.

    Returns:
        A list of `OCRWord` objects containing detected words with their
        bounding boxes, confidence scores and page number (always 0 for
        single images).

    Raises:
        ImportError: If PIL or pytesseract is not installed.
    """
    if Image is None or pytesseract is None:
        raise ImportError(
            "OCR dependencies are missing. Please install pillow and pytesseract."
        )
    # Load image from bytes
    image = Image.open(io.BytesIO(image_bytes))
    # Use Tesseract to get word-level data
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words: List[OCRWord] = []
    n_boxes = len(data.get("text", []))
    for i in range(n_boxes):
        text = data["text"][i].strip()
        conf_str = data.get("conf", ["-1"])[i]
        try:
            conf = float(conf_str) if conf_str not in ("", "-1") else 0.0
        except ValueError:
            conf = 0.0
        if text:
            x, y, w, h = (
                int(data["left"][i]),
                int(data["top"][i]),
                int(data["width"][i]),
                int(data["height"][i]),
            )
            words.append(
                OCRWord(text=text, bbox=(x, y, x + w, y + h), confidence=conf, page_num=0)
            )
    return words


def ocr_pdf(pdf_bytes: bytes) -> List[OCRWord]:
    """Perform OCR on a technical submittal PDF.

    The function attempts to extract text directly from the PDF using
    `pdfplumber`. If no text is found on a page (e.g. scanned image), the page
    is converted to an image and processed with Tesseract as a fallback.

    Args:
        pdf_bytes: The raw bytes of the uploaded PDF.

    Returns:
        A list of `OCRWord` objects containing detected words with bounding
        boxes, confidence scores and page numbers.

    Raises:
        ImportError: If `pdfplumber` or `pytesseract` is not installed.
    """
    if pdfplumber is None or pytesseract is None:
        raise ImportError(
            "OCR dependencies are missing. Please install pdfplumber and pytesseract."
        )

    words: List[OCRWord] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            # Try to extract text directly
            page_text = page.extract_text() or ""
            if page_text.strip():
                # Roughly approximate bounding boxes by searching for words in the
                # extracted text. pdfplumber provides character-level positioning
                # which we can group by lines and words. For simplicity we treat
                # the whole page as a single region here. A more advanced
                # implementation would walk through page.chars.
                words.extend(
                    [
                        OCRWord(text=word, bbox=(0, 0, int(page.width), int(page.height)), confidence=100.0, page_num=page_index)
                        for word in page_text.split()
                    ]
                )
            else:
                # Fallback: convert to image and OCR via tesseract
                image = page.to_image(resolution=300).original
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                n_boxes = len(data.get("text", []))
                for i in range(n_boxes):
                    text = data["text"][i].strip()
                    conf_str = data.get("conf", ["-1"])[i]
                    try:
                        conf = float(conf_str) if conf_str not in ("", "-1") else 0.0
                    except ValueError:
                        conf = 0.0
                    if text:
                        x, y, w, h = (
                            int(data["left"][i]),
                            int(data["top"][i]),
                            int(data["width"][i]),
                            int(data["height"][i]),
                        )
                        words.append(
                            OCRWord(
                                text=text,
                                bbox=(x, y, x + w, y + h),
                                confidence=conf,
                                page_num=page_index,
                            )
                        )
    return words


def words_to_text(words: List[OCRWord]) -> str:
    """Flatten a list of OCRWord objects into a single space-separated string.

    This helper is used by downstream extraction functions which operate on
    raw text rather than bounding boxes.

    Args:
        words: List of `OCRWord` instances.

    Returns:
        A single string containing all word texts separated by spaces.
    """
    return " ".join([w.text for w in words])
