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

#  The memo's key on the belief store. A constant, because two spellings would be two memos.
_MEMO = "deliberation:actions"


class Actions:
    """Every way of acting this agent's packages declare."""

    def __init__(self, beliefs):
        #  The STORE, not one of its doors. Public knowledge is where a template lives — a
        #  template is the same in every world — and the store is what can say when the answer
        #  could have changed.
        self._beliefs = beliefs

    def find_all(self) -> list[Action]:
        """Every declared action, name-ordered so a menu built from it is stable.

        REMEMBERED UNTIL THE NEXT WRITE, which is `Store.remember`'s whole purpose (#552, added
        for this exact symptom — the same text fetched per fork by callers none of which could
        have answered differently). What a package declares cannot change while a pass runs, and
        a search writes nothing to the belief base: a three-disk hanoi solve asks this eighteen
        times and queries twice.

        THE MEMO IS HERE AND NOT ON WHOEVER ASKS. It was on the afforder, which made that service
        stateful and therefore a thing every caller had to keep — so a search held one per pass, a
        deliberator built one per call, and `on_menu_now` built one per remembered candidate,
        which is three answers to "how many afforders does an agent have" where the right one is
        ONE. A collection knows when its own answer goes stale; a service does not.
        """
        return self._beliefs.remember(_MEMO, lambda: sorted(
            (Action(uri=r["action"], available=r["available"])
             for r in bindings(self._beliefs.query(_ACTIONS_Q))), key=lambda a: a.uri))
