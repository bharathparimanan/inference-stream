# =============================================================================
# BUCKET 1 — WRITE
#
# Job: author the context window from scratch.
#
# This is the first thing that runs before any request reaches the model.
# It creates the two foundational messages that every single call needs:
#   1. a system message — who the model is, what it must do
#   2. a user message   — the actual request from the user
#
# Why this is a separate file:
#   The system message is the highest-authority content in the entire context.
#   It is authored by you, the developer — not by the user, not retrieved from
#   a database. Having it in its own file means you can find it, read it, and
#   change it without touching anything else.
#
# Input:  query  — the raw string the user typed
# Output: messages — a list of two dicts, ready to be sent to the model API
#
# What the output looks like:
#   [
#     { "role": "system", "content": "You are a ..." },
#     { "role": "user",   "content": "What is ...?"  }
#   ]
#
# This list is what the Together API (and any OpenAI-compatible API) expects
# as the `messages` parameter. The model reads this top to bottom before
# generating a single token.
# =============================================================================


# The system message is defined as a plain string constant.
# Keeping it at the top of this file makes it easy to find and change.
# Every request goes through this — it is the global instruction layer.

SYSTEM_MESSAGE = """
ROLE
You are an inference assistant that answers questions clearly and directly.

PERSONA
You are precise and concise. You do not use filler phrases like "Certainly!" or "Great question!".

TASK
Answer the user's question. If you do not know the answer, say so plainly.

CONSTRAINTS
Reply in plain prose. Keep answers under 200 words unless more depth is requested.
""".strip()


def write(query: str) -> list[dict]:
    # Step 1: build the system message dict
    # role="system" tells the model this is the authoritative instruction layer
    system = {
        "role": "system",
        "content": SYSTEM_MESSAGE,
    }

    # Step 2: build the user message dict
    # role="user" tells the model this is what the person is asking
    # the query is placed here exactly as the user typed it — no modification
    user = {
        "role": "user",
        "content": query,
    }

    # Step 3: return them as a list in the correct order
    # system MUST come first — it frames everything the model reads after it
    return [system, user]
