"""Checkpoint repair: dangling tool_calls must get stub ToolMessages."""
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.repair import (
    history_needs_repair,
    prepare_messages,
    repair_message_list,
    trim_message_list,
    truncate_tool_contents,
)


def test_inserts_stubs_before_the_next_user_message():
    messages = [
        HumanMessage(content="look around"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "search_policies", "args": {"query": "returns"}, "id": "call_a"},
                {"name": "ask_archivist", "args": {"question": "orders"}, "id": "call_b"},
                {"name": "search_policies", "args": {"query": "cancel"}, "id": "call_c"},
            ],
        ),
        HumanMessage(content="end the role-play"),
    ]
    repaired = repair_message_list(messages)
    assert history_needs_repair(messages, repaired)
    assert [type(m) for m in repaired] == [
        HumanMessage, AIMessage, ToolMessage, ToolMessage, ToolMessage, HumanMessage
    ]
    assert [m.tool_call_id for m in repaired[2:5]] == ["call_a", "call_b", "call_c"]
    assert repaired[-1].content == "end the role-play"


def test_complete_tool_round_is_left_alone():
    messages = [
        HumanMessage(content="inventory?"),
        AIMessage(
            content="",
            tool_calls=[{"name": "ask_archivist", "args": {"question": "inv"}, "id": "call_1"}],
        ),
        ToolMessage(content="3 draughts", tool_call_id="call_1"),
        AIMessage(content="You carry three draughts."),
    ]
    repaired = repair_message_list(messages)
    assert history_needs_repair(messages, repaired) is False
    assert repaired == messages


def test_partial_tool_results_get_the_missing_stubs():
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "search_worldbook", "args": {}, "id": "call_ok"},
                {"name": "ask_archivist", "args": {}, "id": "call_missing"},
            ],
        ),
        ToolMessage(content="lore", tool_call_id="call_ok"),
        HumanMessage(content="go on"),
    ]
    repaired = repair_message_list(messages)
    assert [getattr(m, "tool_call_id", None) for m in repaired] == [
        None, "call_ok", "call_missing", None
    ]


def test_trim_does_not_start_on_a_tool_message():
    messages = [
        HumanMessage(content="1"),
        AIMessage(content="", tool_calls=[{"name": "search_worldbook", "args": {}, "id": "c1"}]),
        ToolMessage(content="lore " * 50, tool_call_id="c1"),
        AIMessage(content="You stand in a bog."),
        HumanMessage(content="2"),
        AIMessage(content="Go north."),
    ]
    trimmed = trim_message_list(messages, max_messages=3)
    assert not isinstance(trimmed[0], ToolMessage)
    assert trimmed[-1].content == "Go north."


def test_prepare_truncates_huge_worldbook_dumps():
    huge = "x" * 8000
    messages = [
        HumanMessage(content="where am I"),
        AIMessage(content="", tool_calls=[{"name": "search_worldbook", "args": {}, "id": "c1"}]),
        ToolMessage(content=huge, tool_call_id="c1"),
        AIMessage(content="A misty bog."),
    ]
    truncated = truncate_tool_contents(messages, max_chars=100)
    assert len(truncated[2].content) < len(huge)
    assert truncated[2].content.endswith("…[truncated]")
    prepared = prepare_messages(messages)
    tool = next(m for m in prepared if isinstance(m, ToolMessage))
    assert len(tool.content) < len(huge)
