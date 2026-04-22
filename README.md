# ai-tutor-bot

Chemistry course tutor that answers questions from uploaded course PDFs.

## Features

- Upload one or more PDFs and reindex them into a single local vector store
- Retrieve relevant chunks for each student question
- Refuse obvious out-of-scope or academic-integrity-violating requests
- Show optional source snippets in the UI

## Run

Create a `.env` file in the project root with:

```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_TUTOR_MODEL=gpt-5.4-nano
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
PHOENIX_ENABLE_TRACING=false
PHOENIX_PROJECT_NAME=chemistry-course-ai-tutor
PHOENIX_COLLECTOR_ENDPOINT=
```

Then start the app:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Download the textbook `Introductory Chemistry` from:

`https://open.umn.edu/opentextbooks/textbooks/introductory-chemistry`

Keep the downloaded PDF in `data/uploads/`.

Then open `http://127.0.0.1:8000`.

## Start The UI

1. Activate the virtual environment:

```bash
source .venv/bin/activate
```

2. Make sure `.env` exists in the project root and contains your OpenAI settings.

3. Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

4. Open the UI in your browser:

```text
http://127.0.0.1:8000
```

5. Download `Introductory Chemistry` from:

```text
https://open.umn.edu/opentextbooks/textbooks/introductory-chemistry
```

6. Place the PDF in:

```text
data/uploads/
```

7. Upload the PDF in the UI, then start chatting.

## Use The API

The app also exposes a versioned JSON API under `/api/v1`.

### Health check

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Upload course PDFs

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -F "files=@data/uploads/Introductory Chemistry.pdf"
```

You can send multiple files by repeating the `files` field:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -F "files=@lecture1.pdf" \
  -F "files=@lecture2.pdf"
```

### Ask a tutor question

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the difference between ionic and covalent bonds?"}'
```

Example response:

```json
{
  "answer": "An ionic bond forms when electrons are transferred ...",
  "fallback": false,
  "sources": [
    {
      "filename": "Introductory Chemistry.pdf",
      "page_number": 12,
      "score": 0.913,
      "content": "Ionic bonding occurs when ..."
    }
  ]
}
```

## Phoenix Tracing

To enable Arize Phoenix tracing, add these variables to `.env`:

```bash
PHOENIX_ENABLE_TRACING=true
PHOENIX_PROJECT_NAME=chemistry-course-ai-tutor
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

When enabled, Phoenix captures:

- OpenAI token counts and latency for embeddings and tutor responses
- retrieval latency for vector search
- retrieved chunks from the vector database, including filename, page number, score, and chunk text

## Start With Phoenix

To start both the AI tutor app and a local Phoenix server together:

```bash
./scripts/start_with_phoenix.sh
```

This starts:

- Phoenix UI on `http://127.0.0.1:6006`
- Phoenix OTLP collector on `127.0.0.1:4317`
- AI tutor UI on `http://127.0.0.1:8000`

Local Phoenix data is stored in:

```text
.phoenix_runtime/
```

The local Phoenix SQLite database is:

```text
.phoenix_runtime/phoenix.db
```

Log files are written to:

```text
.phoenix.log
.ai-tutor.log
```
