from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.services.openai_service import OpenAIService
from app.services.tutor import TutorService
from app.services.vector_store import SQLiteVectorStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


class ChatRequest(BaseModel):
    question: str


def build_tutor_service() -> TutorService:
    return TutorService(
        vector_store=SQLiteVectorStore(settings.database_path),
        openai_service=OpenAIService(),
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)) -> dict[str, int | str]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required.")
    if any(not file.filename.lower().endswith(".pdf") for file in files):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    tutor_service = build_tutor_service()
    chunk_count = await tutor_service.reindex_pdfs(files)
    return {"message": "PDFs uploaded and indexed.", "chunks_indexed": chunk_count}


@app.post("/chat")
def chat(payload: ChatRequest) -> dict[str, object]:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    tutor_service = build_tutor_service()
    result = tutor_service.answer_question(payload.question.strip())
    return {
        "answer": result.answer,
        "fallback": result.fallback,
        "sources": [
            {
                "filename": source.filename,
                "page_number": source.page_number,
                "score": round(source.score, 3),
                "content": source.content,
            }
            for source in result.sources
        ],
    }
