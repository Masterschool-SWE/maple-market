"""Structured-output demo: forge an Encounter.

Unlike the conversational Keeper (free text), this is a one-shot agent whose output is forced
into the :class:`Encounter` schema via ``response_format``. It still has the worldbook tool, so
it can ground the monster's stats and loot in the actual bestiary/items.
"""
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from .structured import Encounter
from .tools import search_worldbook
from .tracing import get_langfuse_handler

ENCOUNTER_SYSTEM_PROMPT = """\
You are the Keeper, forging a single encounter for a hero in the realm of Aethelgard.
Use the search_worldbook tool to ground the monster's challenge rating and the loot in the
real bestiary and item catalog. Keep the encounter appropriate to the hero's level. Return only
the structured encounter.
"""


def generate_encounter(
    hero_context: str,
    scene: str,
    *,
    model: str,
    temperature: float | None = None,
) -> Encounter:
    model_kwargs = {} if temperature is None else {"temperature": temperature}
    llm = init_chat_model(model, **model_kwargs)

    agent = create_agent(
        llm,
        tools=[search_worldbook],
        system_prompt=f"{ENCOUNTER_SYSTEM_PROMPT}\n\n## The hero\n{hero_context}",
        response_format=Encounter,
    )
    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Forge an encounter for this scene: {scene}"}]},
        config=config,
    )
    return result["structured_response"]
