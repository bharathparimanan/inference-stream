# inference-stream

A minimal, fully observable agentic inference system built to understand the
mechanics of context engineering, tool calling, retrieval-augmented generation,
and evaluation — from request to response.

---

## What it is

A Streamlit application that takes a user query, assembles a structured context
window, optionally retrieves relevant content from a vector store, calls an LLM
with tool-use support, streams the response token by token, and records an eval
trace for every interaction.

The purpose is not the feature set — it is understanding how each layer
influences model behaviour and where control actually lives in an agentic system.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit UI  (src/app.py)                                     │
│  username · file upload · query input · streaming response      │
└────────────────────────┬────────────────────────────────────────┘
                         │ messages: list[dict]
┌────────────────────────▼────────────────────────────────────────┐
│  Context layer  (src/context/)                                  │
│                                                                 │
│  write()     authors system message + user message              │
│  select()    trims conversation history to last N turns         │
│  compress()  shrinks content to a character budget              │
│  isolate()   wraps content in named XML tags                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
┌─────────────▼──────┐  ┌───────────▼──────────────────────────┐
│  Storage layer     │  │  Service  (src/service.py)            │
│  (src/storage/)    │  │                                       │
│                    │  │  1. tool loop (batch)                 │
│  db.py    schema   │  │     model → tool_call?                │
│  store.py upload   │  │     yes → dispatch() → append result  │
│  retrieve.py search│  │     repeat until finish_reason=stop   │
└─────────────┬──────┘  │                                       │
              │  chunks  │  2. final answer (streaming)         │
              └──────────►     yield tokens → st.write_stream() │
                         └───────────────────────────────────────┘
                                        │
                         ┌──────────────▼──────────────────────┐
                         │  Eval layer  (evals/)                │
                         │  evaluate_live_request() after every │
                         │  request → trace → transcript/        │
                         └─────────────────────────────────────┘
```

---

## Project structure

```
inference-stream/
├── main.py                        # entry point — launches streamlit
├── src/
│   ├── app.py                     # UI: query input, file upload, streaming output
│   ├── service.py                 # model call: tool loop + streaming
│   ├── context/
│   │   ├── write.py               # bucket 1: author system + user message
│   │   ├── select.py              # bucket 2: filter conversation history
│   │   ├── compress.py            # bucket 3: shrink text to fit context budget
│   │   └── isolate.py             # bucket 4: wrap content in named XML tags
│   ├── storage/
│   │   ├── db.py                  # postgres connection + schema setup
│   │   ├── store.py               # chunk → embed (local) → save to pgvector
│   │   └── retrieve.py            # embed query → cosine search → top-k chunks
│   └── tools/
│       └── weather.py             # schema (contract) + implementation + dispatcher
└── evals/
    ├── datasets.py                # curated context and response data points
    ├── eval_suite.py              # graders, runner, transcript writer
    └── transcript/                # one JSON file per run, every trace inside
```

---

## Context engineering

The model's context window is its only working memory. Everything it reasons
about must be present at call time. The four buckets control what goes in and
how it is structured.

| Bucket | File | Problem it solves |
|--------|------|-------------------|
| **write** | `context/write.py` | context poisoning, context confusion |
| **select** | `context/select.py` | context distraction |
| **compress** | `context/compress.py` | context clash |
| **isolate** | `context/isolate.py` | context confusion, context clash |

The assembled messages list goes directly to the model API as the `messages`
parameter. The shape never changes — it is always a list of `{role, content}`
dicts.

---

## Tool calling

A tool has two parts that must stay in sync:

- **Schema** — a JSON object the model reads before the conversation. It
  describes the tool name, what it does, and what arguments it needs. The model
  uses this to decide whether and when to call it.

- **Implementation** — the Python function that runs in your application when
  the model outputs a `tool_call`. The model never executes code directly.

The execution flow:

```
messages + tools → model
                 → finish_reason == "tool_calls"
                 → dispatch(name, args_json)
                 → append tool_result to messages
                 → model again
                 → finish_reason == "stop"
                 → stream final answer
```

To add a new tool: define the schema and function in `src/tools/`, register it
in `REGISTRY` inside the same file, and add the schema to `TOOLS` in
`service.py`.

---

## Storage and retrieval

User-uploaded plain text files are chunked, embedded locally using
`sentence-transformers/all-mpnet-base-v2` (768-dim, no API cost), and stored in
PostgreSQL with the pgvector extension.

At query time the query is embedded with the same model and pgvector returns the
top-k chunks by cosine similarity, filtered by `user_id` so each user's content
is isolated. Retrieved chunks pass through `compress()` → `isolate()` before
being injected into the system message.

Schema:

```sql
users     (id, username)
documents (id, user_id, filename)
chunks    (id, document_id, user_id, content, embedding vector(768))
```

---

## Eval suite

Every interaction is evaluated automatically. Two suites run on demand; the live
grader runs after every real user request.

| Suite | What it checks | Cost |
|-------|---------------|------|
| Context suite | `build_context()` structure, roles, query preservation | free, no API call |
| Response suite | expected substring in model response | live API calls |
| Live grader | context structure + non-empty response for every real request | no extra API call |

Traces are written to `evals/transcript/<timestamp>.json`.

Run the full suite:

```bash
uv run python evals/eval_suite.py
```

---

## Setup

**Prerequisites**

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- [Postgres.app](https://postgresapp.com) (includes pgvector)
- Together.ai API key

**Install**

```bash
uv sync
```

**Environment**

```bash
# .env
TOGETHER_API_KEY=your_key_here
MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct-Turbo
DATABASE_URL=postgresql://your_user@localhost:5434/inference
```

**Database**

Start Postgres.app, then:

```bash
psql -p 5434 -c "CREATE DATABASE inference;"
psql -p 5434 -d inference -c "CREATE EXTENSION vector;"
```

Schema is created automatically on first app start.

---

## Run

```bash
uv run python main.py
# or
uv run streamlit run src/app.py
```

Open [http://localhost:8501](http://localhost:8501).

1. Enter a username in the sidebar
2. Upload a `.txt` file (optional — enables retrieval)
3. Ask a question — the model answers from your document or its own knowledge
4. Ask about the weather in London, New York, or Tokyo to trigger tool calling

---

## Response delivery modes

| Mode | Analogy | When to use |
|------|---------|-------------|
| Batch | POST → full JSON body | need complete text before next step |
| Streaming | SSE / chunked transfer | showing output to a user |
| Async | POST → 202 job id → poll | long generation, serverless, mobile |

This system uses streaming for all final responses. Tool resolution runs
synchronously (batch) before the streaming phase begins.
