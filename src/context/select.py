# =============================================================================
# BUCKET 2 — SELECT
#
# Job: from all available conversation history, keep only what is relevant.
#
# When a user has a multi-turn conversation (many messages back and forth),
# all of those messages accumulate. But the model does not need all of them —
# it only needs enough recent context to understand the current question.
# Sending everything wastes the context window and distracts the model.
#
# This file answers the question: "which history turns go in?"
#
# Input:  history   — the full list of past messages (user + assistant turns)
#         max_turns — how many recent back-and-forth pairs to keep
# Output: a trimmed list containing only the most recent turns
#
# What "turns" means:
#   One turn = one user message + one assistant reply = 2 messages in the list.
#   max_turns=3 means keep the last 3 pairs = last 6 messages.
#   We multiply by 2 to get the message count from the turn count.
#
# Where the output goes:
#   The result of select() is inserted into the messages list produced by write(),
#   between the system message and the final user message:
#
#   [ system ]  ← from write.py
#   [ user    ]  ← history turn 1
#   [ asst    ]  ← history turn 1
#   [ user    ]  ← history turn 2  (selected turns go here)
#   [ asst    ]  ← history turn 2
#   [ user    ]  ← the current query  ← from write.py
# =============================================================================


def select(history: list[dict], max_turns: int) -> list[dict]:
    # max_turns * 2 converts turn count to message count
    # (each turn = 1 user message + 1 assistant message)
    max_messages = max_turns * 2

    # negative slice from the end keeps the most recent messages
    # if history has fewer messages than max_messages, the full history is returned
    return history[-max_messages:]
