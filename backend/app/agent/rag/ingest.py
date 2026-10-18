"""Offline RAG ingestion: load -> chunk -> embed -> store.

This is the full offline flow. Run it once (and after any policy edit):

    uv run python -m app.agent.rag.ingest --app-dir backend

It reads the policy markdown, splits it into chunks, embeds them, and writes them to a
persistent Chroma collection that the retriever (and search_policies) reads at query time.
"""
import argparse
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...config import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    WORLDBOOK_DIR,
)
from .embeddings import get_embeddings


def _load_worldbook(worldbook_dir: str) -> list[Document]:
    """Read every markdown file into a Document, tagging it with its filename.

    We load by hand to stay dependency-light and future-proof. (LangChain also ships
    ``DirectoryLoader``/``TextLoader`` in ``langchain-community`` — a fine alternative, but that
    package is being sunset, so we avoid it on the path every student runs.)
    """
    docs: list[Document] = []
    for path in sorted(Path(worldbook_dir).glob("**/*.md")):
        docs.append(Document(page_content=path.read_text(encoding="utf-8"),
                             metadata={"source": path.name}))
    return docs


def run_ingest(
    worldbook_dir: str = WORLDBOOK_DIR,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> int:
    """Build (or rebuild) the policy vector store. Returns the number of chunks stored."""
    docs = _load_worldbook(worldbook_dir)

    # 2) CHUNK — split into overlapping windows the embedder can handle.
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)  # 'source' metadata carries through to each chunk

    # 3) EMBED + 4) STORE — write to a persistent Chroma collection.
    store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )
    store.reset_collection()  # start clean so re-running doesn't duplicate chunks
    store.add_documents(chunks)

    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest shop policies into Chroma.")
    parser.add_argument("--worldbook-dir", default=WORLDBOOK_DIR)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    args = parser.parse_args()

    print(f"Ingesting {args.worldbook_dir} (chunk_size={args.chunk_size}, overlap={args.chunk_overlap})...")
    n = run_ingest(args.worldbook_dir, args.chunk_size, args.chunk_overlap)
    print(f"Done. Stored {n} chunks in '{CHROMA_COLLECTION}' at {CHROMA_DIR}.")


if __name__ == "__main__":
    main()
