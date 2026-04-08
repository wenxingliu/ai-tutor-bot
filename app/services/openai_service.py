from __future__ import annotations

import logging
from typing import Sequence

from openai import OpenAI

from app.config import settings


LOGGER = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required.")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        LOGGER.info("Creating embeddings for %s chunks", len(texts))
        response = self._client.embeddings.create(
            model=settings.embedding_model,
            input=list(texts),
        )
        return [item.embedding for item in response.data]

    def answer_question(self, *, question: str, context_blocks: Sequence[str]) -> str:
        instructions = (
            "You are a chemistry course tutor for a university class. "
            "Use only the provided course context. "
            "If the student asks something outside the scope of the uploaded chemistry course materials, "
            "refuse briefly and state that you can only help with questions grounded in those materials. "
            "If the student asks for cheating, answer-only solutions for graded work, hidden test answers, "
            "or other academic-integrity violations, refuse and offer help with concepts instead. "
            "If the retrieved context is insufficient, say that the course materials do not contain enough "
            "information to answer confidently. "
            "Do not invent facts beyond the provided context. Be concise, accurate, and educational."
        )
        context = "\n\n".join(context_blocks)
        prompt = (
            f"Course context:\n{context}\n\n"
            f"Student question:\n{question}\n\n"
            "Write the best response under those rules."
        )

        LOGGER.info("Generating tutor answer")
        response = self._client.responses.create(
            model=settings.tutor_model,
            instructions=instructions,
            input=prompt,
        )
        return response.output_text.strip()
