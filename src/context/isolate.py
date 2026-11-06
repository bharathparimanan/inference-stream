# =============================================================================
# BUCKET 4 — ISOLATE
#
# Job: wrap a block of content in a named tag so the model knows what it is.
#
# When you add extra content to the context — a retrieved document, a user
# profile, a tool result, a constraint list — the model needs to know what
# kind of content it is reading. Without a label, the model must infer this
# from surrounding text, which leads to confusion.
#
# Isolate wraps content in XML-like tags. The tag name tells the model what
# the block is for. Models are trained on vast amounts of XML and HTML so
# they parse these boundaries reliably.
#
# This file answers the question: "what is this block of content?"
#
# Input:  label   — a short name describing what the content is
#                   e.g. "document", "user_profile", "tool_result", "rules"
#         content — the text to wrap
# Output: a tagged string
#
# What the output looks like:
#   isolate("document", "The Eiffel Tower is in Paris.")
#   →
#   <document>
#   The Eiffel Tower is in Paris.
#   </document>
#
# Where the output goes:
#   The tagged string is added to the system message content (from write.py)
#   so the model sees it as authored, trusted context — not as user input.
#
# Example of a full system message with an isolated block:
#   You are an inference assistant...     ← from SYSTEM_MESSAGE in write.py
#
#   <document>
#   The Eiffel Tower is in Paris.         ← from isolate()
#   </document>
#
# Why XML-like tags and not plain text headers?
#   Tags have an opening AND closing boundary. The model can clearly see
#   where a block starts and where it ends. A plain header like "DOCUMENT:"
#   has no closing — the model cannot tell when the document content stops
#   and the next instruction begins.
# =============================================================================


def isolate(label: str, content: str) -> str:
    # wrap content between opening and closing tags
    # the newlines inside keep the content visually separated from the tags
    return f"<{label}>\n{content}\n</{label}>"
