from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.config import settings


@dataclass(slots=True)
class RawChunk:
    filename: str
    page_number: int
    content: str


def extract_chunks_from_pdf(pdf_path: Path) -> list[RawChunk]:
    reader = PdfReader(str(pdf_path))
    chunks: list[RawChunk] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        if not text:
            continue

        for chunk_text in split_text(text):
            chunks.append(
                RawChunk(
                    filename=pdf_path.name,
                    page_number=page_number,
                    content=chunk_text,
                )
            )

    return chunks


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_text(text: str) -> list[str]:
    max_size = settings.max_chunk_chars
    overlap = settings.chunk_overlap_chars

    if len(text) <= max_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + max_size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)

    return [chunk for chunk in chunks if chunk]
