from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from app.main import app


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_SCENARIOS_PATH = Path("evals/test_scenarios.json")
DEFAULT_RESULTS_PATH = Path("evals/test_results.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run test scenario queries against the tutor API and save outputs.",
    )
    parser.add_argument(
        "--transport",
        choices=("inprocess", "http"),
        default="inprocess",
        help="How to call the tutor app. Default: inprocess",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for the tutor app when --transport=http. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS_PATH,
        help=f"Path to the scenario file. Default: {DEFAULT_SCENARIOS_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help=f"Path to write test results. Default: {DEFAULT_RESULTS_PATH}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenarios_payload = load_json(args.scenarios)
    scenario_results = run_scenarios(
        scenarios=scenarios_payload.get("scenarios", []),
        transport=args.transport,
        base_url=args.base_url.rstrip("/"),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"results": scenario_results}, indent=2), encoding="utf-8")
    print(f"Wrote {len(scenario_results)} results to {args.output}")
    return 0


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def run_scenarios(
    *,
    scenarios: list[dict[str, Any]],
    transport: str,
    base_url: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    client = TestClient(app, raise_server_exceptions=False) if transport == "inprocess" else None

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "")
        expected_output = scenario.get("details", {}).get("expected_behavior", "")

        for query in scenario.get("contextualized_queries", []):
            user_query = query.get("query", "")
            query_id = query.get("query_id", "")
            actual_output = call_chat_api(
                transport=transport,
                base_url=base_url,
                user_query=user_query,
                client=client,
            )
            results.append(
                {
                    "scenario_id": scenario_id,
                    "query_id": query_id,
                    "user_query": user_query,
                    "actual_output": actual_output,
                    "expected_output": expected_output,
                }
            )

    return results


def call_chat_api(
    *,
    transport: str,
    base_url: str,
    user_query: str,
    client: TestClient | None,
) -> str:
    if transport == "inprocess":
        assert client is not None
        try:
            response = client.post("/api/v1/chat", json={"question": user_query})
        except Exception as exc:
            return f"Request failed: {exc}"
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return response.text
        if response.status_code >= 400:
            return f"HTTP {response.status_code}: {payload}"
        return str(payload.get("answer", ""))

    payload = json.dumps({"question": user_query}).encode("utf-8")
    api_request = request.Request(
        url=f"{base_url}/api/v1/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(api_request) as response:
            response_body = response.read().decode("utf-8")
            parsed = json.loads(response_body)
            return str(parsed.get("answer", ""))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return f"HTTP {exc.code}: {body}"
    except error.URLError as exc:
        return f"Request failed: {exc.reason}"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
