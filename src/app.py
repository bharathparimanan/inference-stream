import sys
import os
import streamlit as st

from service import handle_request_stream
from storage.db import setup, get_or_create_user
from storage.store import store_document
from storage.retrieve import retrieve
from context.write import write
from context.compress import compress
from context.isolate import isolate

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
from eval_suite import evaluate_live_request

# run once on startup — creates tables if they don't exist
setup()


def build_messages(query: str, user_id: int) -> list[dict]:
    # Step 1: retrieve relevant chunks from pgvector for this user
    chunks = retrieve(user_id, query, top_k=3)

    # Step 2: start with the base context from write()
    messages = write(query)

    # Step 3: if chunks were found, compress + isolate + inject into system message
    if chunks:
        compressed = [compress(c, max_chars=500) for c in chunks]  # shrink each chunk
        combined = "\n\n".join(compressed)                          # join into one block
        tagged = isolate("retrieved_context", combined)             # wrap in named tag
        messages[0]["content"] += "\n\n" + tagged                  # append to system message

    return messages


def run():
    st.set_page_config(page_title="Inference Stream", layout="centered")
    st.title("Inference Stream")

    # ── sidebar: identity + file upload ──────────────────────────────────────
    st.sidebar.header("User")
    username = st.sidebar.text_input("Username", placeholder="enter a username")

    st.sidebar.divider()
    st.sidebar.header("Upload document")
    uploaded_file = st.sidebar.file_uploader("Plain text file", type=["txt"])

    if uploaded_file and username:
        user_id = get_or_create_user(username)
        text = uploaded_file.read().decode("utf-8")
        doc_id = store_document(user_id, uploaded_file.name, text)
        st.sidebar.success(f"Stored: {uploaded_file.name} ({doc_id})")

    # ── main: query + response ────────────────────────────────────────────────
    query = st.text_area("Query", placeholder="Type your request here...", height=120)
    send = st.button("Send", type="primary")
    response_container = st.empty()

    if send and query:
        if not username:
            st.warning("Enter a username in the sidebar first.")
        else:
            user_id = get_or_create_user(username)
            messages = build_messages(query, user_id)

            with response_container:
                reply = st.write_stream(handle_request_stream(messages))

            traces = evaluate_live_request(query, reply)
            passed = sum(1 for t in traces if t["outcome"] == "pass")
            total = len(traces)
            status = "✅" if passed == total else "❌"
            st.caption(f"{status} eval: {passed}/{total} passed — trace saved to evals/transcript/")


run()
