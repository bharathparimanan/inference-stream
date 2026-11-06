# =============================================================================
# BUCKET 3 — COMPRESS
#
# Job: shrink text that is too long before it enters the context window.
#
# The context window has a fixed size (measured in tokens, roughly 1 token
# per word). If you try to put a 50,000-word document into a 10,000-token
# window, the API either rejects the request or silently cuts off the end.
# Either way, the model never sees the full content.
#
# Compress solves this by cutting content down to a size that fits,
# before it is inserted into the messages list.
#
# This file answers the question: "is this content short enough to include?"
#
# Input:  text      — any string (a document, a retrieved chunk, a long message)
#         max_chars — the character limit to enforce
# Output: the original text if it fits, or a truncated version if it does not
#
# The "[compressed]" marker at the end is intentional.
# It tells the model that something was cut here — so it does not try to
# complete or hallucinate the missing part.
#
# Note on characters vs tokens:
#   This uses characters, not tokens, for simplicity.
#   In production: 1 token ≈ 4 characters in English.
#   A 4000-token limit ≈ 16,000 characters.
#   You can swap the character limit for a token count using a tokeniser
#   library (e.g. tiktoken) without changing the interface of this function.
#
# Where compress() is called:
#   Before passing any long content to isolate() or directly into the messages.
#   Example:
#     short_doc = compress(long_document, max_chars=2000)
#     tagged    = isolate("document", short_doc)
# =============================================================================


def compress(text: str, max_chars: int) -> str:
    # if the text already fits, return it unchanged
    if len(text) <= max_chars:
        return text

    # cut at max_chars and append the marker so the model knows content was removed
    return text[:max_chars] + " ...[compressed]"
