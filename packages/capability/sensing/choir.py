"""The reading choir: what this package asks the agent's other modules about a reading.

`annotate`, `bounds`, `urgency` and `on_reading_recorded` used to be hooks the kernel defined
by name on `Module` and merged in `Agent` — each a sentence about a subject, a property and a
value, which is to say a sensing sentence in the kernel. The kernel keeps the MECHANISM
(`Agent.ask`, `Agent.tell`: every module that defines a hook is asked, an error in one voice is
logged and does not silence the rest) and this file keeps the CONTRACT: what each hook is
asked with, and how the answers merge. A module that wants a say defines the method; bidding
answers `urgency` for a held claim, sensing itself answers all three from the region.
See knowledge/decisions/the-stake-is-sensings-want.md.
"""

from __future__ import annotations


def annotations(agent, subject_uri: str, observed_property: str, value: float) -> dict:
    """Everything the agent's modules want to say about a reading of its own, merged — what
    makes an announcement the AGENT's rather than sensing's: whoever holds an opinion
    contributes it, and a module with no stake contributes nothing."""
    out: dict = {}
    for answer in agent.ask("annotate", subject_uri, observed_property, value):
        out.update(answer)
    return out


def bounds(agent, subject_uri: str, observed_property: str) -> tuple[float, float] | None:
    """The tightest band any module wants this property held in, or None — the highest floor
    and the lowest ceiling, because a board that woke for the loosest opinion would sleep
    through the tightest one's trouble (#151)."""
    answers = agent.ask("bounds", subject_uri, observed_property)
    if not answers:
        return None
    return max(low for low, _ in answers), min(high for _, high in answers)


def urgency(agent, subject_uri: str, observed_property: str,
            value: float | None) -> float | None:
    """How close this reading puts the agent to trouble — the sharpest opinion any module
    holds, or None where nobody has one. `value` None asks how urgent NOT KNOWING is."""
    opinions = agent.ask("urgency", subject_uri, observed_property, value)
    return max(opinions) if opinions else None


def recorded(agent, subject_uri: str, observed_property: str, value: float) -> None:
    """Sensing tells the rest of the agent that something new is known. The agent's own
    modules are the only audience: this is it noticing, not it telling anyone."""
    agent.tell("on_reading_recorded", subject_uri, observed_property, value)
