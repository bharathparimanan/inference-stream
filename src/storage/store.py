from sentence_transformers import SentenceTransformer
from storage.db import get_connection

# =============================================================================
# STORE — upload a plain text file into pgvector
#
# Flow:
#   raw text
#       ↓
#   split into chunks (plain text split by double newline or fixed size)
#       ↓
#   generate an embedding vector for each chunk (local model, no API call)
#       ↓
#   save chunk + embedding into the chunks table
#
# A chunk is a small piece of the document — typically a paragraph or
# a fixed number of characters. We chunk because:
#   - the embedding model has a token limit per input
#   - smaller chunks give more precise retrieval results
#   - you retrieve only the relevant chunk, not the whole document
# =============================================================================

CHUNK_SIZE = 500      # characters per chunk

# all-mpnet-base-v2 runs locally, no API key needed, produces 768-dim vectors
# first run downloads the model (~420MB) and caches it — subsequent runs are instant
_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


def _chunk_text(text: str) -> list[str]:
    # split on double newlines first (natural paragraph boundaries)
    # then fall back to fixed-size character chunks if paragraphs are too long
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= CHUNK_SIZE:
            chunks.append(para)
        else:
            # paragraph is too long — split it into fixed-size pieces
            for i in range(0, len(para), CHUNK_SIZE):
                chunks.append(para[i:i + CHUNK_SIZE])
    return chunks


def _embed(texts: list[str]) -> list[list[float]]:
    # runs locally — returns one 768-dim vector per input text
    return _model.encode(texts, convert_to_numpy=True).tolist()


def store_document(user_id: int, filename: str, text: str) -> int:
    # splits the text, embeds all chunks, saves everything to Postgres
    # returns the document_id of the newly created document row

    chunks = _chunk_text(text)
    embeddings = _embed(chunks)   # one API call for all chunks (batched)

    conn = get_connection()
    cur = conn.cursor()

    # insert the document row and get its id
    cur.execute(
        "INSERT INTO documents (user_id, filename) VALUES (%s, %s) RETURNING id",
        (user_id, filename)
    )
    document_id = cur.fetchone()[0]

    # insert each chunk with its embedding
    # the embedding vector is passed as a string Postgres understands: '[0.1, 0.2, ...]'
    for content, embedding in zip(chunks, embeddings):
        cur.execute(
            "INSERT INTO chunks (document_id, user_id, content, embedding) VALUES (%s, %s, %s, %s)",
            (document_id, user_id, content, str(embedding))
        )

    conn.commit()
    cur.close()
    conn.close()
    return document_id
