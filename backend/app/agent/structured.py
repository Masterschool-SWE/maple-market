"""Structured-output schemas for the agent.

When passed as ``response_format`` to ``create_agent``, the agent returns a validated instance
of this model in ``result["structured_response"]`` instead of free text.
"""
from pydantic import BaseModel, Field


class Encounter(BaseModel):
    """A combat/story encounter the Keeper forges for a hero."""

    title: str = Field(description="A short, evocative name for the encounter.")
    narrative: str = Field(description="2-3 sentences setting the scene, addressed to the hero.")
    monster_name: str = Field(description="The main creature faced.")
    challenge_rating: int = Field(description="The creature's challenge rating (see the bestiary).")
    suggested_tactics: str = Field(description="One or two tactics that play to the hero's class.")
    loot: list[str] = Field(description="1-3 items the hero might win.")
