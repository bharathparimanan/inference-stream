from typing import TypedDict


class ContextDataPoint(TypedDict):
    id: str
    query: str


class ResponseDataPoint(TypedDict):
    id: str
    query: str
    expected: str  # substring the response must contain


# -----------------------------------------------------------------------------
# CONTEXT DATASET
# These data points are fed into build_context() only — no model call.
# The grader checks the structure of what build_context() returns.
# -----------------------------------------------------------------------------

CONTEXT_DATASET: list[ContextDataPoint] = [
    {"id": "ctx-01", "query": "What is machine learning?"},
    {"id": "ctx-02", "query": "Explain neural networks."},
    {"id": "ctx-03", "query": "hi"},
    {"id": "ctx-04", "query": ""},
]


# -----------------------------------------------------------------------------
# RESPONSE DATASET
# These data points go through the full pipeline: build_context → model call.
# The grader checks whether the response contains the expected substring.
# Keep queries unambiguous and expected values short and factual.
# -----------------------------------------------------------------------------

RESPONSE_DATASET: list[ResponseDataPoint] = [
    {
        "id": "res-01",
        "query": "What is the capital of France? Reply in one word.",
        "expected": "paris",
    },
    {
        "id": "res-02",
        "query": "What is 12 multiplied by 12? Reply with just the number.",
        "expected": "144",
    },
    {
        "id": "res-03",
        "query": "At what temperature does water boil at sea level? Reply with just the number and unit.",
        "expected": "100",
    },
    {
        "id": "res-04",
        "query": "What programming language is known for its use in data science? Reply in one word.",
        "expected": "python",
    },
]
