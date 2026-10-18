"""Keep checkpointed history valid and small enough for the model API.

- Dangling ``tool_calls`` (no matching ToolMessage) get stubs so OpenAI does not 400.
- Old Worldbook dumps are truncated and the tail of the thread is kept so a single
  request can fit a low TPM cap (gpt-4o-mini at 10k tokens/min rejects >10k in one call).
"""
from langchain_core.messages import RemoveMessage, ToolMessage

from ..config import MAX_THREAD_MESSAGES, MAX_TOOL_RESULT_CHARS


def _tool_call_id(tc) -> str | None:
    if isinstance(tc, dict):
        return tc.get("id")
    return getattr(tc, "id", None)


def _ai_tool_call_ids(msg) -> list[str]:
    tcs = getattr(msg, "tool_calls", None) or []
    return [tid for tid in (_tool_call_id(tc) for tc in tcs) if tid]


def _is_tool_message(msg) -> bool:
    if isinstance(msg, ToolMessage):
        return True
    return getattr(msg, "type", None) == "tool" or getattr(msg, "role", None) == "tool"


def repair_message_list(messages: list) -> list:
    """Insert stub ToolMessages for any unanswered tool_calls, in place."""
    out: list = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        out.append(msg)
        needed = _ai_tool_call_ids(msg)
        if not needed:
            i += 1
            continue
        seen: set[str] = set()
        j = i + 1
        while j < len(messages) and _is_tool_message(messages[j]):
            out.append(messages[j])
            tid = getattr(messages[j], "tool_call_id", None)
            if tid:
                seen.add(tid)
            j += 1
        for tid in needed:
            if tid not in seen:
                out.append(
                    ToolMessage(
                        content="Tool call was interrupted; no result was recorded.",
                        tool_call_id=tid,
                    )
                )
        i = j
    return out


def history_needs_repair(original: list, repaired: list) -> bool:
    if len(original) != len(repaired):
        return True
    return any(
        isinstance(a, ToolMessage) is not isinstance(b, ToolMessage)
        or getattr(a, "tool_call_id", None) != getattr(b, "tool_call_id", None)
        for a, b in zip(original, repaired)
    )


def truncate_tool_contents(messages: list, max_chars: int = MAX_TOOL_RESULT_CHARS) -> list:
    """Shrink stored tool dumps (Worldbook passages) so they do not dominate the context."""
    out = []
    for msg in messages:
        if _is_tool_message(msg):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if len(content) > max_chars:
                msg = msg.model_copy(update={"content": content[:max_chars] + "\n…[truncated]"})
        out.append(msg)
    return out


def trim_message_list(messages: list, max_messages: int = MAX_THREAD_MESSAGES) -> list:
    """Keep the most recent messages without splitting a tool_call group."""
    if max_messages <= 0 or len(messages) <= max_messages:
        return messages
    start = len(messages) - max_messages
    while start > 0 and _is_tool_message(messages[start]):
        start -= 1
    return messages[start:]


def prepare_messages(messages: list) -> list:
    repaired = repair_message_list(messages)
    truncated = truncate_tool_contents(repaired)
    return trim_message_list(truncated)


def _fingerprint(messages: list) -> list:
    return [
        (
            type(m).__name__,
            getattr(m, "id", None),
            getattr(m, "tool_call_id", None),
            len(m.content if isinstance(getattr(m, "content", ""), str) else str(getattr(m, "content", ""))),
        )
        for m in messages
    ]


def repair_checkpoint(graph, config: dict) -> None:
    """Fix dangling tool_calls and shrink history before the next model call."""
    try:
        snapshot = graph.get_state(config)
    except Exception:
        return
    values = getattr(snapshot, "values", None) or {}
    messages = list(values.get("messages") or [])
    if not messages:
        return
    prepared = prepare_messages(messages)
    if _fingerprint(messages) == _fingerprint(prepared):
        return
    removals = [RemoveMessage(id=m.id) for m in messages if getattr(m, "id", None)]
    graph.update_state(config, {"messages": removals + prepared})
