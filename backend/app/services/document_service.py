import io
import os
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.config import settings


def ensure_upload_dir() -> None:
    os.makedirs(settings.upload_dir, exist_ok=True)


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n\n".join(parts).strip()
    if lower.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    raise ValueError("Unsupported file type. Use PDF or DOCX.")


def save_upload(filename: str, content: bytes) -> str:
    ensure_upload_dir()
    safe = Path(filename).name
    path = os.path.join(settings.upload_dir, safe)
    base, ext = os.path.splitext(path)
    n = 0
    while os.path.exists(path):
        n += 1
        path = f"{base}_{n}{ext}"
    with open(path, "wb") as f:
        f.write(content)
    return path
