"""Every action the loaded vocabulary declares, as a collection.

The templates, and nothing situational: one `orexis:Action` node per way of acting, each with the
precondition that says when it is possible. A new way of acting is a node in a new package
directory and never an edit here (#207, an-action-is-one-node).

**PUBLIC AND TIMELESS, which is why this reads through `query` and not through a world's door.**
What a package declares does not depend on which world is being imagined or at which instant —
only what it AFFORDS does. They were read together, once per node of a search, because one file
held both questions: a three-disk solve re-read the same eleven templates eighteen times. Asking
the vocabulary is this collection's job and asking a world is `Affordances`'; an `Afforder` puts
the two together.

This is what knowledge/domain/menu.md describes and had no class for.
"""

from __future__ import annotations

from orexis_agent_progression.store import bindings

from .action import Action

_ACTIONS_Q = """SELECT ?action ?available WHERE {
  ?action a orexis:Action ; orexis:available ?available }"""


class Actions:
    """Every way of acting this agent's packages declare."""

    def __init__(self, query):
        #  Public knowledge's door. Not a world's: a template is the same in every world.
        self._query = query

    def find_all(self) -> list[Action]:
        """Every declared action, name-ordered so a menu built from it is stable."""
        return sorted((Action(uri=r["action"], available=r["available"])
                       for r in bindings(self._query(_ACTIONS_Q))), key=lambda a: a.uri)
