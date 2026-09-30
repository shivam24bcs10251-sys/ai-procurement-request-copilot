from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.run_public_evals import evaluate
from src.contracts import ProcurementDecision
from src.solution import handle_request


EXPECTED_ACTION_TERMS = {
    "REQ-1001": ("existing capability", "documented gap"),
    "REQ-1002": ("existing capability", "documented gap"),
    "REQ-1003": ("existing capability", "documented gap"),
    "REQ-1005": ("budget exception", "budget"),
    "REQ-1006": ("clarification", "missing information"),
    "REQ-1009": ("manual evidence", "verify the vendor"),
}
MEASURED_RUNS = 5


def wait_for_api(proc: subprocess.Popen, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Vendor API exited during evaluation startup")
        try:
            if requests.get("http://127.0.0.1:8001/health", timeout=0.25).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.1)
    raise RuntimeError("Vendor API did not become ready for evaluation")


def action_is_correct(decision: ProcurementDecision) -> bool:
    text = f"{decision.recommendation} {decision.next_step}".lower()
    return any(term in text for term in EXPECTED_ACTION_TERMS[decision.request_id])


def evidence_is_grounded(decision: ProcurementDecision) -> bool:
    if not decision.telemetry or not decision.evidence:
        return False
    called = set(decision.telemetry.tool_names)
    return all(item.source in called and bool(item.reference) for item in decision.evidence)


def summarize(rows: list[dict[str, object]], architecture: str) -> dict[str, object]:
    selected = [row for row in rows if row["architecture"] == architecture]
    return {
        "architecture": architecture,
        "cases": len(selected),
        "cases_passing_all_quality_checks": sum(
            all(
                bool(row[field])
                for field in (
                    "correct_next_action",
                    "grounded_evidence",
                    "policy_followed",
                    "human_escalation_correct",
                )
            )
            for row in selected
        ),
        "avg_latency_ms": round(sum(float(row["latency_ms"]) for row in selected) / len(selected), 2),
        "avg_llm_calls": round(sum(int(row["llm_calls"]) for row in selected) / len(selected), 2),
        "avg_tool_calls": round(sum(int(row["tool_calls"]) for row in selected) / len(selected), 2),
    }


def main() -> None:
    cases = json.loads((ROOT / "evals" / "public_cases.json").read_text(encoding="utf-8"))
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mock_api.app:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rows: list[dict[str, object]] = []
    try:
        wait_for_api(api)
        # Warm caches for both variants so startup effects do not favor whichever runs second.
        handle_request(cases[0]["request_id"], architecture="single")
        handle_request(cases[0]["request_id"], architecture="staged")
        for architecture in ("single", "staged"):
            for case in cases:
                timings: list[float] = []
                decision: ProcurementDecision | None = None
                for _ in range(MEASURED_RUNS):
                    started = time.perf_counter()
                    decision = handle_request(case["request_id"], architecture=architecture)
                    timings.append((time.perf_counter() - started) * 1000)
                assert decision is not None
                latency_ms = round(sum(timings) / len(timings), 2)
                public_failures = evaluate(decision, case["expectations"])
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "request_id": case["request_id"],
                        "architecture": architecture,
                        "correct_next_action": action_is_correct(decision),
                        "grounded_evidence": evidence_is_grounded(decision),
                        "policy_followed": not public_failures,
                        "human_escalation_correct": decision.human_review_required
                        and not any("approval missing" in failure for failure in public_failures),
                        "latency_ms": latency_ms,
                        "llm_calls": decision.telemetry.llm_calls if decision.telemetry else 0,
                        "tool_calls": decision.telemetry.tool_calls if decision.telemetry else 0,
                        "notes": " | ".join(public_failures),
                        "measurement_runs": MEASURED_RUNS,
                    }
                )
    finally:
        api.terminate()
        try:
            api.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api.kill()

    results_path = ROOT / "evals" / "evaluation_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = [summarize(rows, architecture) for architecture in ("single", "staged")]
    summary_path = ROOT / "evals" / "comparison_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    for item in summary:
        print(
            f"{item['architecture']}: {item['cases_passing_all_quality_checks']}/{item['cases']} quality passes, "
            f"{item['avg_latency_ms']} ms average, {item['avg_llm_calls']} LLM calls, "
            f"{item['avg_tool_calls']} tool calls"
        )
    print(f"Detailed results: {results_path.relative_to(ROOT)}")
    print(f"Summary: {summary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
