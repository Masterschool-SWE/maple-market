"""Orchestration glue between the API and the assistant.

The router calls :func:`invoke_keeper`. Tests monkeypatch this one function so they never need
a real model or API key.
"""
import uuid

from sqlmodel import Session, select

from ..config import KEEPER_MODEL, KEEPER_TEMPERATURE
from ..models import SupportThread, User
from .keeper import build_keeper
from .repair import repair_checkpoint
from .tracing import flush_langfuse, get_langfuse_handler


def get_or_create_thread(session: Session, user_id: int) -> SupportThread:
    thread = session.exec(select(SupportThread).where(SupportThread.user_id == user_id)).first()
    if thread is None:
        thread = SupportThread(user_id=user_id, thread_id=str(uuid.uuid4()))
        session.add(thread)
        session.commit()
        session.refresh(thread)
    return thread


def invoke_keeper(
    session: Session,
    user: User,
    message: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
) -> str:
    """Run one turn of conversation and return the assistant's reply text."""
    thread = get_or_create_thread(session, user.id)
    keeper = build_keeper(
        hero_context=f"- user_id: {user.id}\n- username: {user.username}\n",
        model=model or KEEPER_MODEL,
        temperature=KEEPER_TEMPERATURE if temperature is None else temperature,
        reasoning_effort=reasoning_effort,
    )
    config = {"configurable": {"thread_id": thread.thread_id, "user_id": user.id}}
    handler = get_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]

    repair_checkpoint(keeper, config)
    try:
        result = keeper.invoke({"messages": [{"role": "user", "content": message}]}, config=config)
    except Exception:
        repair_checkpoint(keeper, config)
        raise
    if handler:
        flush_langfuse()
    content = result["messages"][-1].content
    return content if isinstance(content, str) else str(content)
