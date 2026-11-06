import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# DB — connection and schema setup
#
# This file owns two things:
#   1. get_connection() — returns a live connection to Postgres
#   2. setup()          — creates the tables and vector index if they don't exist
#
# Every other file in storage/ calls get_connection() to talk to the database.
# setup() is called once when the app starts.
# =============================================================================


def get_connection():
    # reads DATABASE_URL from .env and opens a connection
    # psycopg2 is the standard Python driver for Postgres
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


def setup():
    # creates all tables and the vector index if they do not already exist
    # safe to call on every app start — IF NOT EXISTS means it is idempotent
    conn = get_connection()
    cur = conn.cursor()

    # enable the pgvector extension — this adds the VECTOR column type to Postgres
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # users table — one row per username
    # each user's content is isolated by their user_id foreign key
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id      SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL
        )
    """)

    # documents table — one row per uploaded file
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id       SERIAL PRIMARY KEY,
            user_id  INTEGER REFERENCES users(id),
            filename TEXT NOT NULL
        )
    """)

    # chunks table — one row per chunk of a document
    # embedding is a 768-dimension vector (matches the Together.ai embedding model)
    # this is the table pgvector searches against
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id          SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            user_id     INTEGER REFERENCES users(id),
            content     TEXT NOT NULL,
            embedding   VECTOR(768)
        )
    """)

    # IVFFlat index — makes vector search fast on large tables
    # cosine similarity is standard for text embeddings
    cur.execute("""
        CREATE INDEX IF NOT EXISTS chunks_embedding_idx
        ON chunks USING ivfflat (embedding vector_cosine_ops)
    """)

    conn.commit()
    cur.close()
    conn.close()


def get_or_create_user(username: str) -> int:
    # returns the user's id, creating a row if the username is new
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING", (username,))
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return user_id
