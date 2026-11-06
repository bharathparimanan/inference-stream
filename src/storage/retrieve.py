from storage.db import get_connection
from storage.store import _model

# =============================================================================
# RETRIEVE — semantic search against the user's stored chunks
#
# Flow:
#   user query (string)
#       ↓
#   embed the query using the same model used at storage time
#       ↓
#   pgvector finds the chunks whose embeddings are closest to the query embedding
#   filtered by user_id — user A never sees user B's content
#       ↓
#   returns the top-k chunk texts, ready to be passed to isolate()
#
# "Closest" means cosine similarity — vectors that point in the same direction
# in 768-dimensional space are semantically similar.
# The <=> operator in Postgres is the pgvector cosine distance operator.
# =============================================================================


def retrieve(user_id: int, query: str, top_k: int = 3) -> list[str]:
    # Step 1: embed the query using the same local model used when storing
    query_embedding = _model.encode([query], convert_to_numpy=True).tolist()[0]

    # Step 2: search pgvector for the closest chunks belonging to this user
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT content
        FROM chunks
        WHERE user_id = %s
        ORDER BY embedding <=> %s   -- <=> is cosine distance; smaller = more similar
        LIMIT %s
    """, (user_id, str(query_embedding), top_k))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    # each row is a tuple (content,) — extract just the text
    return [row[0] for row in rows]
