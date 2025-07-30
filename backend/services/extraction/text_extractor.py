"""
Raw‑text helpers copied from your original extractor.py – **unchanged**.
"""
from __future__ import annotations

import json
import os
from typing import Union, Dict

import cv2
import fitz               # PyMuPDF
import pandas as pd
import pdfplumber
import pytesseract
import docx               # python‑docx
from PIL import Image

# 👉 set Tesseract path if needed
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

class RawTextExtractor:
    @staticmethod
    # ------------------------------------------------------------------
    # 1️⃣ low‑level extractors (just as before)
    # ------------------------------------------------------------------
    def _extract_text_pdf(path: str) -> str:
        """Prefer embedded text; fall back to OCR on first page."""
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            print(f"[extract] pdfplumber error: {exc}")

        if len(text.strip()) < 20:          # likely scanned
            try:
                doc = fitz.open(path)
                pix = doc[0].get_pixmap(dpi=300)
                tmp = "_tmp_ocr.png"
                pix.save(tmp)
                img = cv2.imread(tmp)
                text = pytesseract.image_to_string(img)
                os.remove(tmp)
            except Exception as exc:
                print(f"[extract] PDF‑OCR error: {exc}")
        return text

    @staticmethod
    def _extract_text_docx(path: str) -> str:
        try:
            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            print(f"[extract] DOCX read error: {exc}")
            return ""

    @staticmethod
    def _extract_text_csv(path: str) -> str:
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            return df.to_string(index=False)
        except Exception as exc:
            print(f"[extract] CSV read error: {exc}")
            return ""

    @staticmethod
    def _extract_text_json(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data, indent=2)
        except Exception as exc:
            print(f"[extract] JSON read error: {exc}")
            return ""


# ------------------------------------------------------------------
# 2️⃣ single convenience wrapper
# ------------------------------------------------------------------
    @staticmethod
    def extract_text(path: str) -> str:
        """Return raw text for any supported report file."""
        ext = os.path.splitext(path.lower())[1]
        if ext == ".pdf":
            return RawTextExtractor._extract_text_pdf(path)
        elif ext in {".docx", ".doc"}:
            return RawTextExtractor._extract_text_docx(path)
        elif ext == ".csv":
            return RawTextExtractor._extract_text_csv(path)
        elif ext == ".json":
            return RawTextExtractor._extract_text_json(path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


# ------------------------------------------------------------------
# 3️⃣ OCR an image if the user uploads a JPEG/PNG
# ------------------------------------------------------------------
    @staticmethod
    def get_text_from_image(image_path: str) -> str:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
 