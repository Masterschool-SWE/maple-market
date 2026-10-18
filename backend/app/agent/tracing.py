"""Langfuse tracing (cloud).

Tracing is opt-in: if the Langfuse keys aren't set, ``get_langfuse_handler`` returns None and
the app runs untraced. When configured, the same handler is attached to the Keeper's run; because
it's a LangChain callback, nested runs (Keeper -> Archivist -> tools) appear in one trace tree.
"""
import os


def get_langfuse_handler():
    """Return a Langfuse LangChain CallbackHandler, or None if Langfuse isn't configured."""
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def flush_langfuse() -> None:
    """Flush buffered events. Important for short-lived requests so traces aren't lost."""
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        pass  # never let tracing break a request
