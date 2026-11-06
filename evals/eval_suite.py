import sys
import os
import json
from datetime import datetime
from typing import TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from context.write import write as build_context
from service import handle_request
from datasets import CONTEXT_DATASET, RESPONSE_DATASET


# =============================================================================
# TRACE
# One trace = one data point run through the pipeline with its outcome.
# Every trace is written to the transcript — pass or fail.
# =============================================================================

class Trace(TypedDict):
    id: str
    type: str        # "context" | "response"
    query: str
    outcome: str     # "pass" | "fail"
    grader: str      # the rule that was checked
    detail: str      # what was actually seen


# =============================================================================
# GRADERS
# A grader is a plain function. It takes the raw output and returns
# (passed: bool, detail: str) — what it saw, stated as a fact.
# =============================================================================

def grade_context_structure(context: list[dict]) -> tuple[bool, str]:
    # Rule: must be a list of at least 2 dicts, first role=system, last role=user
    if not isinstance(context, list) or len(context) < 2:
        return False, f"expected list of >=2 messages, got {type(context).__name__} len={len(context) if isinstance(context, list) else 'n/a'}"
    if context[0]["role"] != "system":
        return False, f"expected first role=system, got '{context[0]['role']}'"
    if context[-1]["role"] != "user":
        return False, f"expected last role=user, got '{context[-1]['role']}'"
    if not context[0]["content"].strip():
        return False, "system message content is empty"
    return True, f"{len(context)} messages, roles={[m['role'] for m in context]}"


def grade_query_preserved(context: list[dict], query: str) -> tuple[bool, str]:
    # Rule: the original query must appear unchanged as the last user message
    actual = context[-1]["content"]
    if actual == query:
        return True, f"query preserved: '{actual[:60]}'"
    return False, f"expected '{query[:60]}', got '{actual[:60]}'"


def grade_response_contains(response: str, expected: str) -> tuple[bool, str]:
    # Rule: response must contain the expected substring (case-insensitive)
    if expected.lower() in response.lower():
        return True, f"found '{expected}' in response"
    return False, f"'{expected}' not found — response: '{response[:100]}'"


def grade_response_not_empty(response: str) -> tuple[bool, str]:
    if response.strip():
        return True, f"response is non-empty ({len(response)} chars)"
    return False, "response is empty"


# =============================================================================
# RUNNER
# =============================================================================

def run_context_suite() -> list[Trace]:
    traces: list[Trace] = []

    for dp in CONTEXT_DATASET:
        context = build_context(dp["query"])

        # grader 1: structure
        passed, detail = grade_context_structure(context)
        traces.append(Trace(
            id=dp["id"] + "-a",
            type="context",
            query=dp["query"],
            outcome="pass" if passed else "fail",
            grader="structure: list, roles=[system...user], system non-empty",
            detail=detail,
        ))

        # grader 2: query preserved
        passed, detail = grade_query_preserved(context, dp["query"])
        traces.append(Trace(
            id=dp["id"] + "-b",
            type="context",
            query=dp["query"],
            outcome="pass" if passed else "fail",
            grader="query preserved as last user message",
            detail=detail,
        ))

    return traces


def run_response_suite() -> list[Trace]:
    traces: list[Trace] = []

    for dp in RESPONSE_DATASET:
        try:
            response = handle_request(build_context(dp["query"]))
        except Exception as e:
            traces.append(Trace(
                id=dp["id"],
                type="response",
                query=dp["query"],
                outcome="fail",
                grader=f"contains '{dp['expected']}'",
                detail=f"API error: {e}",
            ))
            continue

        # grader 1: not empty
        passed, detail = grade_response_not_empty(response)
        traces.append(Trace(
            id=dp["id"] + "-a",
            type="response",
            query=dp["query"],
            outcome="pass" if passed else "fail",
            grader="response is non-empty",
            detail=detail,
        ))

        # grader 2: expected substring
        passed, detail = grade_response_contains(response, dp["expected"])
        traces.append(Trace(
            id=dp["id"] + "-b",
            type="response",
            query=dp["query"],
            outcome="pass" if passed else "fail",
            grader=f"response contains '{dp['expected']}'",
            detail=detail,
        ))

    return traces


# =============================================================================
# TRANSCRIPT
# One JSON file per run saved to evals/transcript/
# =============================================================================

def write_transcript(traces: list[Trace]) -> str:
    transcript_dir = os.path.join(os.path.dirname(__file__), "transcript")
    os.makedirs(transcript_dir, exist_ok=True)

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(transcript_dir, f"{run_id}.json")

    total = len(traces)
    passed = sum(1 for t in traces if t["outcome"] == "pass")

    payload = {
        "run_id": run_id,
        "summary": {"total": total, "passed": passed, "failed": total - passed},
        "traces": traces,
    }

    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

    return path


# =============================================================================
# LIVE REQUEST EVAL
# Called from app.py after every real user request.
# No extra API calls — evaluates the query and response already in hand.
# =============================================================================

def evaluate_live_request(query: str, response: str) -> list[Trace]:
    traces: list[Trace] = []

    # context graders — rebuild context from the same query to inspect structure
    context = build_context(query)

    passed, detail = grade_context_structure(context)
    traces.append(Trace(
        id="live-ctx-a",
        type="context",
        query=query,
        outcome="pass" if passed else "fail",
        grader="structure: list, roles=[system...user], system non-empty",
        detail=detail,
    ))

    passed, detail = grade_query_preserved(context, query)
    traces.append(Trace(
        id="live-ctx-b",
        type="context",
        query=query,
        outcome="pass" if passed else "fail",
        grader="query preserved as last user message",
        detail=detail,
    ))

    # response grader — check the response that just came back
    passed, detail = grade_response_not_empty(response)
    traces.append(Trace(
        id="live-res-a",
        type="response",
        query=query,
        outcome="pass" if passed else "fail",
        grader="response is non-empty",
        detail=detail,
    ))

    write_transcript(traces)
    return traces


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("── context suite ──")
    context_traces = run_context_suite()
    for t in context_traces:
        mark = "✅" if t["outcome"] == "pass" else "❌"
        print(f"  {mark} [{t['id']}] {t['grader']}")
        if t["outcome"] == "fail":
            print(f"       {t['detail']}")

    print("\n── response suite ──")
    response_traces = run_response_suite()
    for t in response_traces:
        mark = "✅" if t["outcome"] == "pass" else "❌"
        print(f"  {mark} [{t['id']}] {t['grader']}")
        if t["outcome"] == "fail":
            print(f"       {t['detail']}")

    all_traces = context_traces + response_traces
    path = write_transcript(all_traces)

    total = len(all_traces)
    passed = sum(1 for t in all_traces if t["outcome"] == "pass")
    print(f"\n── {passed}/{total} passed — transcript: {path}")
