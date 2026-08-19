INFERENCE STREAM
================

PURPOSE
-------
Sandbox project to build a context layer for applied AI engineering.
Scope: one FastAPI endpoint that takes a user prompt, forwards it to an
LLM, and returns the generated output. Starts as a batch (request-response)
implementation, then evolves into a streamed (token-by-token) response.

The point of the project is not the feature — it's learning how streaming
works end-to-end in a real deployed app: server-side generator/async
iterator, HTTP chunked transfer or SSE, client-side consumption, and
where backpressure and partial-failure handling actually live.

ARCHITECTURE (V1 — BATCH)
--------------------------
Client -> POST /generate -> FastAPI handler -> LLM API call (blocking) ->
full response returned as single JSON payload.

ARCHITECTURE (V2 — STREAM, TARGET)
-----------------------------------
Client -> POST /generate/stream -> FastAPI handler -> LLM API call
(stream=True) -> StreamingResponse / SSE -> client consumes chunks as
they arrive.

BUILD ORDER
------------
1. Batch endpoint working end-to-end (request -> LLM -> full response).
2. Swap blocking call for the LLM SDK's streaming mode.
3. Wrap generator in FastAPI's StreamingResponse.
4. Client-side: consume via fetch + ReadableStream (or SSE EventSource).
5. Ablation: batch vs stream — measure time-to-first-byte, perceived
   latency, and failure modes (mid-stream errors, client disconnects).

OUT OF SCOPE (V1)
------------------
- Auth, rate limiting, persistence.
- Multi-turn conversation state.
- Multiple LLM providers.
These are deliberately excluded to keep the learning loop bounded to
streaming mechanics.

PROJECT STRUCTURE
------------------
app/
  main.py          FastAPI app + route definitions
  llm_client.py     LLM API wrapper (batch + stream variants)
  schemas.py        Pydantic request/response models
.env                API keys (not committed)
requirements.txt
README.txt
.gitignore

SETUP
-----
1. python -m venv venv && source venv/bin/activate
2. pip install -r requirements.txt
3. Set API key in .env
4. uvicorn app.main:app --reload

OPEN QUESTIONS TO RESOLVE WHILE BUILDING
------------------------------------------
- SSE vs raw chunked response: which fits a single-page client better?
- How to propagate a mid-stream LLM error to an already-open connection?
- Where does token-level buffering belong — server or client?