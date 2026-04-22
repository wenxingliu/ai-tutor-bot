from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(".phoenix_runtime/phoenix.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query Phoenix traces from the local phoenix.db SQLite database.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to phoenix.db. Default: {DEFAULT_DB_PATH}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of most recent traces to print. Default: 1",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.db.exists():
        raise FileNotFoundError(f"Phoenix database not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    trace_rows = conn.execute(
        """
        SELECT t.id, t.trace_id, t.start_time, t.end_time, p.name AS project_name
        FROM traces t
        JOIN projects p ON p.id = t.project_rowid
        ORDER BY t.id DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()

    if not trace_rows:
        print("No traces found.")
        return 0

    for trace in trace_rows:
        print("=" * 80)
        print(f"Trace rowid: {trace['id']}")
        print(f"Project: {trace['project_name']}")
        print(f"Trace ID: {trace['trace_id']}")
        print(f"Start: {trace['start_time']}")
        print(f"End:   {trace['end_time']}")
        print("-" * 80)

        span_rows = conn.execute(
            """
            SELECT id, name, span_kind, start_time, end_time,
                   llm_token_count_prompt, llm_token_count_completion, attributes
            FROM spans
            WHERE trace_rowid = ?
            ORDER BY id
            """,
            (trace["id"],),
        ).fetchall()

        for span in span_rows:
            print_span(span)

    return 0


def print_span(span: sqlite3.Row) -> None:
    latency_ms = compute_latency_ms(span["start_time"], span["end_time"])
    print(f"Span {span['id']}: {span['name']} [{span['span_kind']}]")
    print(f"  Start: {span['start_time']}")
    print(f"  End:   {span['end_time']}")
    print(f"  Latency (approx ms): {latency_ms}")

    prompt_tokens = span["llm_token_count_prompt"]
    completion_tokens = span["llm_token_count_completion"]
    if prompt_tokens is not None or completion_tokens is not None:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
        print(f"  Tokens: prompt={prompt_tokens or 0}, completion={completion_tokens or 0}, total={total_tokens}")

    attributes = safe_load_json(span["attributes"])
    print_special_fields(span["name"], attributes)
    print("-" * 80)


def print_special_fields(span_name: str, attributes: dict) -> None:
    input_value = nested_get(attributes, "input", "value")
    output_value = nested_get(attributes, "output", "value")

    if input_value:
        print(f"  Input: {truncate(input_value, 400)}")
    if output_value and span_name == "tutor.answer_question":
        print(f"  Output: {truncate(output_value, 600)}")

    if span_name == "vector_store.search":
        top_k = nested_get(attributes, "retrieval", "top_k")
        documents_blob = nested_get(attributes, "retrieval", "documents")
        documents = []
        if isinstance(documents_blob, str):
            documents = safe_load_json(documents_blob, default=[])
        print(f"  Retrieval top_k: {top_k}")
        print(f"  Retrieved docs: {len(documents)}")
        for index, document in enumerate(documents, start=1):
            metadata = document.get("document.metadata", {})
            preview = truncate(document.get("document.content", ""), 200)
            print(
                f"    {index}. {metadata.get('filename')} page={metadata.get('page_number')} "
                f"score={metadata.get('score')} id={document.get('document.id')}"
            )
            print(f"       {preview}")


def nested_get(data: dict, *keys: str):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def safe_load_json(value: str, default: dict | list | None = None):
    try:
        return json.loads(value)
    except Exception:
        return {} if default is None else default


def truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit] + "..."


def compute_latency_ms(start_time: str, end_time: str) -> str:
    query = """
        SELECT ROUND((julianday(?) - julianday(?)) * 86400000, 1)
    """
    conn = sqlite3.connect(":memory:")
    result = conn.execute(query, (end_time, start_time)).fetchone()[0]
    conn.close()
    return str(result)


if __name__ == "__main__":
    raise SystemExit(main())
