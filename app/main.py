from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.services.openai_service import OpenAIService
from app.services.tutor import TutorService
from app.services.vector_store import SQLiteVectorStore
from app.tracing import configure_tracing


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
configure_tracing()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
api_router = APIRouter(prefix="/api/v1", tags=["tutor"])


class ChatRequest(BaseModel):
    question: str


class HealthResponse(BaseModel):
    status: str


class UploadResponse(BaseModel):
    message: str
    chunks_indexed: int


class SourceResponse(BaseModel):
    filename: str
    page_number: int
    score: float
    content: str


class ChatResponse(BaseModel):
    answer: str
    fallback: bool = Field(default=False)
    sources: list[SourceResponse]


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:  # type: ignore[no-untyped-def]
    logging.exception("Unhandled error while processing %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


def build_tutor_service() -> TutorService:
    return TutorService(
        vector_store=SQLiteVectorStore(settings.database_path),
        openai_service=OpenAIService(),
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@api_router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@api_router.post("/documents", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required.")
    if any(not file.filename.lower().endswith(".pdf") for file in files):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    tutor_service = build_tutor_service()
    chunk_count = await tutor_service.reindex_pdfs(files)
    return UploadResponse(message="PDFs uploaded and indexed.", chunks_indexed=chunk_count)


@api_router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    tutor_service = build_tutor_service()
    result = tutor_service.answer_question(payload.question.strip())
    return ChatResponse(
        answer=result.answer,
        fallback=result.fallback,
        sources=[
            SourceResponse(
                filename=source.filename,
                page_number=source.page_number,
                score=round(source.score, 3),
                content=source.content,
            )
            for source in result.sources
        ],
    )


app.include_router(api_router)


@app.get("/health", include_in_schema=False)
def legacy_health() -> HealthResponse:
    return health()


@app.post("/upload", include_in_schema=False)
async def legacy_upload(files: list[UploadFile] = File(...)) -> UploadResponse:
    return await upload_documents(files)


@app.post("/chat", include_in_schema=False)
def legacy_chat(payload: ChatRequest) -> ChatResponse:
    return chat(payload)
