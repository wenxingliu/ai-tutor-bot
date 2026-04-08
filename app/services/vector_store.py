from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

from app.models import RetrievedChunk
from app.services.pdf_ingestion import RawChunk


LOGGER = logging.getLogger(__name__)


class SQLiteVectorStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def reset(self) -> None:
        with sqlite3.connect(self._database_path) as conn:
            conn.execute("DELETE FROM chunks")
            conn.commit()
        LOGGER.info("Vector store reset")

    def upsert_chunks(self, chunks: Sequence[RawChunk], embeddings: Sequence[Sequence[float]]) -> None:
        records = [
            (
                chunk.filename,
                chunk.page_number,
                chunk.content,
                json.dumps(list(embedding)),
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        with sqlite3.connect(self._database_path) as conn:
            conn.executemany(
                """
                INSERT INTO chunks (filename, page_number, content, embedding)
                VALUES (?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()

        LOGGER.info("Stored %s chunks in vector store", len(records))

    def search(self, query_embedding: Sequence[float], limit: int) -> list[RetrievedChunk]:
        with sqlite3.connect(self._database_path) as conn:
            rows = conn.execute(
                "SELECT id, filename, page_number, content, embedding FROM chunks"
            ).fetchall()

        scored_chunks: list[RetrievedChunk] = []
        for row in rows:
            embedding = json.loads(row[4])
            score = cosine_similarity(query_embedding, embedding)
            scored_chunks.append(
                RetrievedChunk(
                    id=row[0],
                    filename=row[1],
                    page_number=row[2],
                    content=row[3],
                    score=score,
                )
            )

        scored_chunks.sort(key=lambda chunk: chunk.score, reverse=True)
        return scored_chunks[:limit]

    def has_content(self) -> bool:
        with sqlite3.connect(self._database_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return bool(row and row[0] > 0)

    def _initialize(self) -> None:
        with sqlite3.connect(self._database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )
                """
            )
            conn.commit()


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
