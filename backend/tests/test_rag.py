"""Hermetic RAG test: ingest policies with fake embeddings, then retrieve."""
from app.agent.rag.ingest import run_ingest
from app.agent.rag.retriever import get_retriever, get_vectorstore


def test_ingest_and_retrieve():
    get_vectorstore.cache_clear()
    n_chunks = run_ingest(chunk_size=600, chunk_overlap=80)
    assert n_chunks > 0, "ingestion produced no chunks"

    get_vectorstore.cache_clear()
    hits = get_retriever(k=3, mode="basic").invoke(
        "How many days do I have to return an item after delivery?"
    )
    assert hits, "retrieval returned nothing"
    sources = {h.metadata.get("source") for h in hits}
    assert "returns-and-refunds.md" in sources, f"expected returns-and-refunds.md, got {sources}"
