from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.models import RetrievedChunk, TutorResult
from app.services.openai_service import OpenAIService
from app.services.pdf_ingestion import RawChunk, extract_chunks_from_pdf
from app.services.vector_store import SQLiteVectorStore


LOGGER = logging.getLogger(__name__)

EMPTY_STORE_MESSAGE = (
    "No course PDFs are indexed yet. Upload the course materials before asking questions."
)
FALLBACK_MESSAGE = (
    "I could not find enough support in the uploaded course materials to answer that confidently."
)


class TutorService:
    def __init__(
        self,
        *,
        vector_store: SQLiteVectorStore,
        openai_service: OpenAIService,
    ) -> None:
        self._vector_store = vector_store
        self._openai = openai_service
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    async def reindex_pdfs(self, files: Sequence[UploadFile]) -> int:
        saved_paths = [await self._save_upload(file) for file in files]

        all_chunks: list[RawChunk] = []
        for path in saved_paths:
            extracted = extract_chunks_from_pdf(path)
            all_chunks.extend(extracted)

        if not all_chunks:
            raise HTTPException(
                status_code=400,
                detail="No extractable text was found in the uploaded PDFs.",
            )

        self._vector_store.reset()
        embeddings = self._openai.embed_texts([chunk.content for chunk in all_chunks])
        self._vector_store.upsert_chunks(all_chunks, embeddings)
        LOGGER.info("Indexed %s PDFs into %s chunks", len(saved_paths), len(all_chunks))
        return len(all_chunks)

    def answer_question(self, question: str) -> TutorResult:
        if not self._vector_store.has_content():
            return TutorResult(answer=EMPTY_STORE_MESSAGE)

        query_embedding = self._openai.embed_texts([question])[0]
        retrieved = self._vector_store.search(query_embedding, limit=settings.retrieval_k)
        useful_chunks = [chunk for chunk in retrieved if chunk.score >= settings.min_similarity_score]

        if not useful_chunks:
            return TutorResult(answer=FALLBACK_MESSAGE, fallback=True)

        context_blocks = [self._format_chunk(chunk) for chunk in useful_chunks]
        answer = self._openai.answer_question(question=question, context_blocks=context_blocks)
        return TutorResult(answer=answer, sources=useful_chunks)

    async def _save_upload(self, upload: UploadFile) -> Path:
        destination = settings.uploads_dir / upload.filename
        data = await upload.read()
        destination.write_bytes(data)
        LOGGER.info("Saved upload to %s", destination)
        return destination

    @staticmethod
    def _format_chunk(chunk: RetrievedChunk) -> str:
        return (
            f"Source: {chunk.filename}, page {chunk.page_number}\n"
            f"Similarity score: {chunk.score:.3f}\n"
            f"{chunk.content}"
        )
