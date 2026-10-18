"""Embedding-model factory.

The embedding model is chosen by the EMBEDDING_MODEL env var so you can switch between a
cloud model (OpenAI), a local one (Ollama), or a deterministic fake (tests, no API key).
The SAME embeddings must be used for ingestion and for retrieval, or search won't work.
"""
from ...config import EMBEDDING_MODEL, openai_client_kwargs


def get_embeddings():
    provider, _, name = EMBEDDING_MODEL.partition(":")

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        short = name or "text-embedding-3-small"
        if short.startswith("openai/"):
            short = short[len("openai/") :]
        return OpenAIEmbeddings(
            model=short,
            tiktoken_model_name="text-embedding-3-small",
            check_embedding_ctx_length=False,
            **openai_client_kwargs(),
        )

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=name or "nomic-embed-text")

    if provider == "fake":
        # Deterministic vectors — no network, no key. Great for tests/CI.
        from langchain_core.embeddings import DeterministicFakeEmbedding
        return DeterministicFakeEmbedding(size=int(name or 256))

    raise ValueError(f"Unknown EMBEDDING_MODEL provider: {provider!r} (use openai|ollama|fake)")
