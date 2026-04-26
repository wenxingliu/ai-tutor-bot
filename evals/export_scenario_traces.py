from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_SCENARIOS_PATH = Path("evals/demo/demo_ai_tutor_bot_test_cases_20.json")
DEFAULT_DB_PATH = Path(".phoenix_runtime/phoenix.db")
DEFAULT_OUTPUT_PATH = Path("evals/demo/demo_ai_tutor_bot_test_cases_20_results.json")
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run scenario queries against the tutor HTTP API and export matching Phoenix traces.",
    )
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenarios = load_scenarios(args.scenarios)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    start_trace_rowid = get_latest_trace_rowid(conn)
    exported: list[dict[str, Any]] = []

    for scenario in scenarios:
        for query in scenario.get("contextualized_queries", []):
            user_query = str(query.get("query", ""))
            response_payload = call_chat_api(
                base_url=args.base_url.rstrip("/"),
                user_query=user_query,
            )
            trace = wait_for_trace(
                conn=conn,
                user_query=user_query,
                min_trace_rowid=start_trace_rowid,
                timeout_seconds=args.poll_seconds,
            )
            if trace:
                start_trace_rowid = max(start_trace_rowid, trace["trace_rowid"])

            exported.append(
                {
                    "scenario_id": scenario.get("scenario_id"),
                    "focus_id": scenario.get("focus_id"),
                    "scenario_name": scenario.get("scenario_name"),
                    "query_id": query.get("query_id"),
                    "user_query": user_query,
                    "expected_behavior": nested_get(scenario, "details", "expected_behavior"),
                    "response": response_payload,
                    "trace": trace,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"results": exported}, indent=2), encoding="utf-8")
    print(f"Wrote {len(exported)} traced scenario results to {args.output}")
    return 0


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("scenarios", [])


def get_latest_trace_rowid(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM traces").fetchone()
    return int(row[0]) if row else 0


def call_chat_api(*, base_url: str, user_query: str) -> dict[str, Any]:
    payload = json.dumps({"question": user_query}).encode("utf-8")
    req = request.Request(
        f"{base_url}/api/v1/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            return {
                "status_code": response.status,
                "ok": True,
                "body": parsed,
            }
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_body: Any = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = body
        return {
            "status_code": exc.code,
            "ok": False,
            "body": parsed_body,
        }
    except error.URLError as exc:
        return {
            "status_code": None,
            "ok": False,
            "body": {"detail": f"Request failed: {exc.reason}"},
        }


def wait_for_trace(
    *,
    conn: sqlite3.Connection,
    user_query: str,
    min_trace_rowid: int,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        trace = find_trace_for_query(
            conn=conn,
            user_query=user_query,
            min_trace_rowid=min_trace_rowid,
        )
        if trace is not None:
            return trace
        time.sleep(0.5)
    return None


def find_trace_for_query(
    *,
    conn: sqlite3.Connection,
    user_query: str,
    min_trace_rowid: int,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT
            t.id AS trace_rowid,
            s.attributes AS span_attributes
        FROM traces t
        JOIN spans s ON s.trace_rowid = t.id
        WHERE t.id > ?
          AND s.name = 'tutor.answer_question'
        ORDER BY t.id ASC
        """,
        (min_trace_rowid,),
    ).fetchall()

    for row in rows:
        attributes = safe_json_loads(row["span_attributes"], default={})
        if nested_get(attributes, "input", "value") == user_query:
            return build_trace_payload(conn=conn, trace_rowid=row["trace_rowid"])
    return None


def build_trace_payload(*, conn: sqlite3.Connection, trace_rowid: int) -> dict[str, Any]:
    trace_row = conn.execute(
        """
        SELECT t.id, t.trace_id, t.start_time, t.end_time, p.name AS project_name
        FROM traces t
        JOIN projects p ON p.id = t.project_rowid
        WHERE t.id = ?
        """,
        (trace_rowid,),
    ).fetchone()
    span_rows = conn.execute(
        """
        SELECT id, name, span_kind, start_time, end_time,
               llm_token_count_prompt, llm_token_count_completion, attributes
        FROM spans
        WHERE trace_rowid = ?
        ORDER BY id
        """,
        (trace_rowid,),
    ).fetchall()

    return {
        "trace_rowid": trace_row["id"],
        "trace_id": trace_row["trace_id"],
        "project_name": trace_row["project_name"],
        "start_time": trace_row["start_time"],
        "end_time": trace_row["end_time"],
        "spans": [build_span_payload(span) for span in span_rows],
    }


def build_span_payload(span: sqlite3.Row) -> dict[str, Any]:
    attributes = safe_json_loads(span["attributes"], default={})
    retrieval_documents = []
    if span["name"] == "vector_store.search":
        documents_blob = nested_get(attributes, "retrieval", "documents")
        if isinstance(documents_blob, str):
            retrieval_documents = safe_json_loads(documents_blob, default=[])

    return {
        "span_rowid": span["id"],
        "name": span["name"],
        "span_kind": span["span_kind"],
        "start_time": span["start_time"],
        "end_time": span["end_time"],
        "latency_ms": compute_latency_ms(span["start_time"], span["end_time"]),
        "token_count": {
            "prompt": span["llm_token_count_prompt"] or 0,
            "completion": span["llm_token_count_completion"] or 0,
            "total": (span["llm_token_count_prompt"] or 0) + (span["llm_token_count_completion"] or 0),
        },
        "input": nested_get(attributes, "input", "value"),
        "output": nested_get(attributes, "output", "value"),
        "retrieval": {
            "top_k": nested_get(attributes, "retrieval", "top_k"),
            "documents_count": len(retrieval_documents),
            "documents": retrieval_documents,
        } if span["name"] == "vector_store.search" else None,
    }


def nested_get(data: dict[str, Any] | None, *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def safe_json_loads(value: str | None, default: dict | list | None = None) -> Any:
    if value is None:
        return {} if default is None else default
    try:
        return json.loads(value)
    except Exception:
        return {} if default is None else default


def compute_latency_ms(start_time: str, end_time: str) -> float | None:
    conn = sqlite3.connect(":memory:")
    row = conn.execute(
        "SELECT ROUND((julianday(?) - julianday(?)) * 86400000, 1)",
        (end_time, start_time),
    ).fetchone()
    conn.close()
    return row[0] if row else None


if __name__ == "__main__":
    raise SystemExit(main())
