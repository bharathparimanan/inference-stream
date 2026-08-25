# Streaming Response — Knowledge Checklist

Use this to track what you understand before and during implementation.
Mark each item: `[ ]` not started / `[~]` in progress / `[x]` understood

---

## 1. Python Generators

- [ ] What `yield` does vs `return`
- [ ] How a generator function is lazy (produces one value at a time)
- [ ] Using `next()` and iterating over a generator
- [ ] Why generators are the foundation of streaming (one chunk at a time)

---

## 2. Async Python

- [ ] What the event loop is and what problem it solves
- [ ] `async def` vs `def` — when to use which
- [ ] `await` — what you're actually waiting for
- [ ] `async for` — iterating over async sources (e.g. LLM token stream)
- [ ] Async generators — `async def` + `yield` combined

---

## 3. HTTP Streaming Mechanics

- [ ] Chunked transfer encoding — server sends pieces, not one blob
- [ ] Server-Sent Events (SSE) — what it is and why LLMs use it
- [ ] Raw SSE chunk format: `data: {...}\n\n`
- [ ] How the client knows the stream has ended

---

## 4. FastAPI Streaming

- [ ] `StreamingResponse` — what it wraps, what media type to set
- [ ] Connecting a generator to `StreamingResponse`
- [ ] Setting correct headers for SSE (`text/event-stream`)
- [ ] `EventSourceResponse` — when to use over raw `StreamingResponse`

---

## 5. Together.ai Streaming API

- [ ] The parameter that enables streaming on the request
- [ ] What each response chunk looks like (structure)
- [ ] How to iterate over chunks from the response
- [ ] The stop signal (`[DONE]`) and how to handle it

---

## Learning Order

```
Generators → Async Python → HTTP mechanics → FastAPI → Together.ai
```

---

## Knowledge Gap Tracker

| Concept               | Status (No idea / Have idea, missing impl / Ready) |
|-----------------------|----------------------------------------------------|
| Generators            |                                                    |
| Async / await         |                                                    |
| SSE format            |                                                    |
| StreamingResponse     |                                                    |
| Together.ai streaming |                                                    |

---

## Clarifications Log

Use this section to log questions that come up during implementation.
Format: `Q: <question> → A: <answer or link to session>`

---
