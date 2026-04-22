from __future__ import annotations

import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Sequence

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.models import RetrievedChunk, TutorResult
from app.services.openai_service import OpenAIService
from app.services.pdf_ingestion import RawChunk, extract_chunks_from_pdf
from app.services.vector_store import SQLiteVectorStore
from app.tracing import TRACER


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
        with TRACER.start_as_current_span("documents.reindex") as span:
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
            span.set_attribute("documents.files", [path.name for path in saved_paths])
            span.set_attribute("documents.chunk_count", len(all_chunks))
            LOGGER.info("Indexed %s PDFs into %s chunks", len(saved_paths), len(all_chunks))
            return len(all_chunks)

    def answer_question(self, question: str) -> TutorResult:
        with TRACER.start_as_current_span("tutor.answer_question") as span:
            span.set_attribute("input.value", question)

            if not self._vector_store.has_content():
                span.set_attribute("tutor.fallback", False)
                return TutorResult(answer=EMPTY_STORE_MESSAGE)

            query_embedding = self._openai.embed_texts([question])[0]

            with TRACER.start_as_current_span("vector_store.search") as retrieval_span:
                started_at = perf_counter()
                retrieved = self._vector_store.search(query_embedding, limit=settings.retrieval_k)
                retrieval_latency_ms = (perf_counter() - started_at) * 1000
                useful_chunks = [chunk for chunk in retrieved if chunk.score >= settings.min_similarity_score]
                retrieval_span.set_attribute("openinference.span.kind", "RETRIEVER")
                retrieval_span.set_attribute("input.value", question)
                retrieval_span.set_attribute("retrieval.top_k", settings.retrieval_k)
                retrieval_span.set_attribute("retrieval.documents.count", len(useful_chunks))
                retrieval_span.set_attribute("retrieval.latency_ms", retrieval_latency_ms)
                retrieval_span.set_attribute(
                    "retrieval.documents",
                    json.dumps(
                        [
                            {
                                "document.id": str(chunk.id),
                                "document.content": chunk.content,
                                "document.metadata": {
                                    "filename": chunk.filename,
                                    "page_number": chunk.page_number,
                                    "score": round(chunk.score, 3),
                                },
                            }
                            for chunk in useful_chunks
                        ]
                    ),
                )

            if not useful_chunks:
                span.set_attribute("tutor.fallback", True)
                return TutorResult(answer=FALLBACK_MESSAGE, fallback=True)

            context_blocks = [self._format_chunk(chunk) for chunk in useful_chunks]
            answer = self._openai.answer_question(question=question, context_blocks=context_blocks)
            span.set_attribute("tutor.fallback", False)
            span.set_attribute("output.value", answer)
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
