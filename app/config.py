from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Chemistry Course AI Tutor"
    uploads_dir: Path = BASE_DIR / "data" / "uploads"
    database_path: Path = BASE_DIR / "data" / "vector_store.db"
    max_chunk_chars: int = 1200
    chunk_overlap_chars: int = 200
    retrieval_k: int = 4
    min_similarity_score: float = 0.45
    tutor_model: str = os.getenv("OPENAI_TUTOR_MODEL", "gpt-5.4-nano")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


settings = Settings()
