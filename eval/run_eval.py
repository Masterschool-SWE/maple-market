"""Evaluate the Worldbook RAG with Ragas.

For each question in golden.json we retrieve context, generate an answer, and score four metrics:
faithfulness, answer relevancy, context precision, and context recall.

Run it (needs OPENAI_API_KEY and an ingested store built with the SAME embeddings):

    # build the store with real embeddings first
    uv run python -m app.agent.rag.ingest --app-dir backend
    uv run python eval/run_eval.py

This is an *advanced* exercise. Ragas calls an LLM to judge each answer, so it costs tokens.
"""
import json
import os
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# --- Compatibility shim -------------------------------------------------------------------
# Ragas 0.4.x imports two Vertex AI symbols that langchain-community 0.4.x removed. We never use
# Vertex AI, so we register harmless placeholders before importing ragas. Remove this once Ragas
# ships a release compatible with the installed langchain-community.
_vmod = types.ModuleType("langchain_community.chat_models.vertexai")
_vmod.ChatVertexAI = object
sys.modules.setdefault("langchain_community.chat_models.vertexai", _vmod)
import langchain_community.llms as _llms  # noqa: E402

if not hasattr(_llms, "VertexAI"):
    _llms.VertexAI = object
# -----------------------------------------------------------------------------------------

from langchain.chat_models import init_chat_model  # noqa: E402
from ragas import EvaluationDataset, evaluate  # noqa: E402
from ragas.dataset_schema import SingleTurnSample  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from app.agent.rag.embeddings import get_embeddings  # noqa: E402
from app.agent.rag.retriever import get_retriever  # noqa: E402
from app.config import KEEPER_MODEL  # noqa: E402


def answer_with_rag(question: str, llm) -> tuple[str, list[str]]:
    """Retrieve context and answer the question from it (a minimal RAG chain)."""
    docs = get_retriever().invoke(question)
    contexts = [d.page_content for d in docs]
    context_block = "\n\n".join(contexts)
    prompt = (
        "Answer the question using ONLY the context below. Be concise.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {question}"
    )
    return llm.invoke(prompt).content, contexts


def main() -> None:
    golden = json.loads((pathlib.Path(__file__).parent / "golden.json").read_text(encoding="utf-8"))
    answer_llm = init_chat_model(KEEPER_MODEL, temperature=0)

    samples = []
    for item in golden:
        answer, contexts = answer_with_rag(item["question"], answer_llm)
        samples.append(SingleTurnSample(
            user_input=item["question"],
            response=answer,
            retrieved_contexts=contexts,
            reference=item["reference"],
        ))

    dataset = EvaluationDataset(samples=samples)
    judge_llm = LangchainLLMWrapper(init_chat_model(os.getenv("RAGAS_MODEL", KEEPER_MODEL), temperature=0))
    judge_emb = LangchainEmbeddingsWrapper(get_embeddings())

    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextPrecisionWithReference(),
            LLMContextRecall(),
        ],
        llm=judge_llm,
        embeddings=judge_emb,
    )
    print("\n=== Ragas scores ===")
    print(result)


if __name__ == "__main__":
    main()
