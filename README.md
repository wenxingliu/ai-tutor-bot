# ai-tutor-bot

Chemistry course tutor that answers questions from uploaded course PDFs.

## Features

- Upload one or more PDFs and reindex them into a single local vector store
- Retrieve relevant chunks for each student question
- Refuse obvious out-of-scope or academic-integrity-violating requests
- Show optional source snippets in the UI

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Set `OPENAI_API_KEY` before starting the app.

Then open `http://127.0.0.1:8000`.
