import sys
import os
from datetime import datetime

# make src importable when running from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from context import build_context
from service import handle_request


# =============================================================================
# TEST DATASET
#
# Two kinds of test cases:
#
#   CONTEXT TESTS — do not call the model at all.
#     They check that build_context() produces the right structure.
#     Fast, free, deterministic.
#
#   RESPONSE TESTS — call the model with a query.
#     They check that the response meets a rule or matches an expected output.
#     Slower, costs tokens, but tests the full end-to-end path.
# =============================================================================

CONTEXT_TESTS = [
    {
        "id": "ctx-01",
        "description": "build_context returns a list",
        "query": "hello",
        "check": lambda result: isinstance(result, list),
        "expect": "result is a list",
    },
    {
        "id": "ctx-02",
        "description": "context has at least two messages",
        "query": "hello",
        "check": lambda result: len(result) >= 2,
        "expect": "at least 2 messages (system + user)",
    },
    {
        "id": "ctx-03",
        "description": "first message role is system",
        "query": "hello",
        "check": lambda result: result[0]["role"] == "system",
        "expect": "result[0]['role'] == 'system'",
    },
    {
        "id": "ctx-04",
        "description": "last message role is user",
        "query": "hello",
        "check": lambda result: result[-1]["role"] == "user",
        "expect": "result[-1]['role'] == 'user'",
    },
    {
        "id": "ctx-05",
        "description": "last message content matches the query",
        "query": "What is the capital of France?",
        "check": lambda result: result[-1]["content"] == "What is the capital of France?",
        "expect": "user content equals the original query",
    },
    {
        "id": "ctx-06",
        "description": "system message is not empty",
        "query": "hello",
        "check": lambda result: len(result[0]["content"].strip()) > 0,
        "expect": "system content is non-empty",
    },
    {
        "id": "ctx-07",
        "description": "every message has role and content keys",
        "query": "hello",
        "check": lambda result: all("role" in m and "content" in m for m in result),
        "expect": "all messages have 'role' and 'content'",
    },
    {
        "id": "ctx-08",
        "description": "empty query is still passed through as user message",
        "query": "",
        "check": lambda result: result[-1]["content"] == "",
        "expect": "empty string preserved, not dropped",
    },
]

RESPONSE_TESTS = [
    {
        "id": "res-01",
        "description": "response is a non-empty string",
        "query": "Say the word hello.",
        "check": lambda r: isinstance(r, str) and len(r.strip()) > 0,
        "expect": "non-empty string",
    },
    {
        "id": "res-02",
        "description": "factual question — capital of France",
        "query": "What is the capital of France? Answer in one word.",
        "check": lambda r: "paris" in r.lower(),
        "expect": "response contains 'paris'",
    },
    {
        "id": "res-03",
        "description": "factual question — water boiling point",
        "query": "At what temperature does water boil at sea level? Answer with just the number and unit.",
        "check": lambda r: "100" in r,
        "expect": "response contains '100'",
    },
    {
        "id": "res-04",
        "description": "response does not contain filler phrase 'certainly'",
        "query": "What is 2 + 2?",
        "check": lambda r: "certainly" not in r.lower(),
        "expect": "'certainly' not in response (persona constraint)",
    },
    {
        "id": "res-05",
        "description": "response does not contain filler phrase 'great question'",
        "query": "What is the speed of light?",
        "check": lambda r: "great question" not in r.lower(),
        "expect": "'great question' not in response (persona constraint)",
    },
    {
        "id": "res-06",
        "description": "short query still produces a response",
        "query": "hi",
        "check": lambda r: len(r.strip()) > 0,
        "expect": "non-empty response to a very short query",
    },
    {
        "id": "res-07",
        "description": "ambiguous query still produces a response",
        "query": "Tell me about it.",
        "check": lambda r: len(r.strip()) > 0,
        "expect": "non-empty response even with no clear referent",
    },
    {
        "id": "res-08",
        "description": "response to math question contains the correct answer",
        "query": "What is 12 multiplied by 12? Answer with just the number.",
        "check": lambda r: "144" in r,
        "expect": "response contains '144'",
    },
]


# =============================================================================
# RUNNER
# =============================================================================

def run_context_tests() -> list[dict]:
    results = []
    for test in CONTEXT_TESTS:
        context = build_context(test["query"])
        passed = test["check"](context)
        results.append({
            "id": test["id"],
            "description": test["description"],
            "passed": passed,
            "expect": test["expect"],
        })
    return results


def run_response_tests() -> list[dict]:
    results = []
    for test in RESPONSE_TESTS:
        try:
            response = handle_request(test["query"])
            passed = test["check"](response)
            actual = response[:120].replace("\n", " ")  # first 120 chars for the report
        except Exception as e:
            passed = False
            actual = f"ERROR: {e}"
        results.append({
            "id": test["id"],
            "description": test["description"],
            "passed": passed,
            "expect": test["expect"],
            "actual": actual,
        })
    return results


# =============================================================================
# REPORT
# =============================================================================

def build_report(context_results: list[dict], response_results: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx_pass = sum(1 for r in context_results if r["passed"])
    res_pass = sum(1 for r in response_results if r["passed"])
    total = len(context_results) + len(response_results)
    total_pass = ctx_pass + res_pass

    lines = [
        f"# Eval Report",
        f"",
        f"Run at: {now}",
        f"",
        f"**Total: {total_pass}/{total} passed**",
        f"",
        f"---",
        f"",
        f"## Context tests ({ctx_pass}/{len(context_results)} passed)",
        f"",
        f"| ID | Description | Result |",
        f"|----|-------------|--------|",
    ]

    for r in context_results:
        status = "✅ pass" if r["passed"] else "❌ fail"
        lines.append(f"| {r['id']} | {r['description']} | {status} |")

    lines += [
        f"",
        f"## Response tests ({res_pass}/{len(response_results)} passed)",
        f"",
        f"| ID | Description | Expected | Actual (first 120 chars) | Result |",
        f"|----|-------------|----------|--------------------------|--------|",
    ]

    for r in response_results:
        status = "✅ pass" if r["passed"] else "❌ fail"
        lines.append(
            f"| {r['id']} | {r['description']} | {r['expect']} | {r.get('actual', '')} | {status} |"
        )

    return "\n".join(lines)


def save_report(report: str) -> str:
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".md"
    path = os.path.join(reports_dir, filename)
    with open(path, "w") as f:
        f.write(report)
    return path


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("Running context tests...")
    context_results = run_context_tests()

    print("Running response tests (each makes a live API call)...")
    response_results = run_response_tests()

    report = build_report(context_results, response_results)
    path = save_report(report)

    print(report)
    print(f"\nReport saved to: {path}")
