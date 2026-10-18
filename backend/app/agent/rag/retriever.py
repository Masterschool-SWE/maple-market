"""Retrieval over the persisted policy vector store.

Three modes (set via RETRIEVAL_MODE):
  - basic : dense vector search (the default).
  - hybrid: BM25 (keyword) + dense, fused with an EnsembleRetriever.        [advanced]
  - rerank: hybrid candidates re-scored by a cross-encoder (FlashrankRerank). [advanced]
"""
from functools import lru_cache

from langchain_chroma import Chroma

from ...config import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    RETRIEVAL_K,
    RETRIEVAL_MODE,
)
from .embeddings import get_embeddings


@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    """Open the persisted Chroma collection (built by ingest.py)."""
    return Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )


def get_retriever(k: int | None = None, mode: str | None = None):
    """Return a retriever for the requested mode."""
    k = k or RETRIEVAL_K
    mode = mode or RETRIEVAL_MODE
    dense = get_vectorstore().as_retriever(search_kwargs={"k": k})

    if mode == "basic":
        return dense
    if mode in ("hybrid", "rerank"):
        return _build_advanced_retriever(dense, k, mode)
    raise ValueError(f"Unknown RETRIEVAL_MODE: {mode!r} (use basic|hybrid|rerank)")


def _build_advanced_retriever(dense, k: int, mode: str):
    """Hybrid (BM25 + dense), optionally wrapped with a cross-encoder reranker."""
    from langchain_classic.retrievers import (
        ContextualCompressionRetriever,
        EnsembleRetriever,
    )
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document

    # BM25 needs the raw corpus in memory. Pull every chunk back out of the store.
    raw = get_vectorstore().get()
    docs = [
        Document(page_content=text, metadata=meta or {})
        for text, meta in zip(raw["documents"], raw["metadatas"])
    ]
    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = k

    hybrid = EnsembleRetriever(retrievers=[bm25, dense], weights=[0.5, 0.5])
    if mode == "hybrid":
        return hybrid

    # rerank: a small cross-encoder re-scores the fused candidates (downloads once).
    from langchain_community.document_compressors import FlashrankRerank

    return ContextualCompressionRetriever(
        base_compressor=FlashrankRerank(top_n=k),
        base_retriever=hybrid,
    )
