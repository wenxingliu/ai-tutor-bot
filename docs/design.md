# Chemistry Course AI Tutor --- Design Document (v1)

This document covers implementation design. Product requirements live in
[`prd.md`](prd.md).

## 1. API Design

The application exposes a small JSON API for the web UI and external
clients. API routes are versioned under `/api/v1`.

### Endpoints

#### `GET /api/v1/health`

Returns service health for uptime checks.

Example response:

```json
{
  "status": "ok"
}
```

#### `POST /api/v1/documents`

Uploads one or more course PDFs and rebuilds the single course vector
store.

Request:

-   `multipart/form-data`
-   one or more `files` fields containing PDF files

Example response:

```json
{
  "message": "PDFs uploaded and indexed.",
  "chunks_indexed": 128
}
```

#### `POST /api/v1/chat`

Submits a student question and returns the tutor answer plus optional
source chunks.

Request body:

```json
{
  "question": "What is the difference between ionic and covalent bonds?"
}
```

Response body:

```json
{
  "answer": "An ionic bond ...",
  "fallback": false,
  "sources": [
    {
      "filename": "Lecture 2.pdf",
      "page_number": 7,
      "score": 0.91,
      "content": "Ionic bonding occurs when ..."
    }
  ]
}
```

### Error format

All API errors return JSON with a `detail` field.

Examples:

```json
{
  "detail": "Only PDF files are supported."
}
```

```json
{
  "detail": "No extractable text was found in the uploaded PDFs."
}
```

### API behavior

-   The API is stateless across users in v1.
-   Uploading PDFs replaces the existing indexed course materials.
-   Chat responses are grounded only in retrieved course content.
-   If retrieval does not produce enough relevant context, the API
    returns a fallback tutor response.

## 2. High-Level Architecture

User/UI Client → API → Retrieval → LLM (system prompt policy + context)
→ Response

## 3. Core Components

-   FastAPI application serving both API routes and the web UI
-   PDF ingestion pipeline for extraction and chunking
-   Single local vector store for retrieval
-   OpenAI embeddings and response generation
