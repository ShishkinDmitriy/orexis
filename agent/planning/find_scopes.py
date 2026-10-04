"""Reading the store's scopes — every scope each predicate, each term and each action is in.

`scope_actions` writes the partition; this reads it back, asking the scope graphs by class. A
store holding none at all answers None, which is a store nobody scoped and which the
derivation refuses to guess about; a scoped store with nothing in it answers an empty map.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.store import rows

SCOPES_Q = """
SELECT ?member ?scope WHERE { ?member planning:inScope ?scope }"""

#  EVERY STANDING SCOPE GRAPH, asked of the catalogue by class — what a run replaces, whatever
#  each is called, including a per-agent one a volume was left with before the partition
#  became the store's.
STANDING_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:ScopeGraph } }
ORDER BY ?g"""


class Scopes(dict):
    """The partition as read: every member — predicate, term or action — to the SET of scopes it
    is in, and the one question a reader asks of it, where a thing naming several members is.

    A SET PER MEMBER, NOT ONE SCOPE. It answered one per member, which lost the actions in two
    scopes to whichever row came last and could not say a shared term at all — the bed a pump's
    filling and a heater's both bind — so `scope_actions` wrote such a term in neither and a
    reading of that bed's soil named no member. A reader that wants the term unique to a scope
    asks `one`; a reader placing a reading, a witness or a want takes the `meet`.
    """

    def all(self) -> frozenset[str]:
        """Every scope the store has."""
        return frozenset(s for ss in self.values() for s in ss)

    def one(self, member: str) -> str | None:
        """The scope `member` is in where that is exactly one, else None — a word two scopes'
        keys both hold tells nothing on its own."""
        held = self.get(member)
        return next(iter(held)) if held is not None and len(held) == 1 else None

    def meet(self, names) -> frozenset[str]:
        """The scopes a thing naming `names` is of: the scopes every one of its named members is
        in, and where no scope holds them all, every scope any of them is in; nothing where it
        names no member at all, which is a thing every scope holds.

        The bed is the pump's scope's and the heater's, the soil's property the first pump's and
        the second's, and a reading naming both is the first pump's alone. The tower's one state
        graph names the courier's cells and, in its revisions, the puzzle's `on`, which no scope
        holds together, so it is both scopes' — as it was when each member had one scope or none.
        """
        sets = [self[n] for n in names if n in self]
        if not sets:
            return frozenset()
        together = frozenset.intersection(*sets)
        return together or frozenset().union(*sets)


def find_scopes(store: ox.Store) -> Scopes | None:
    """Every member's scopes, predicate, term or action, from the scope graphs asked by class —
    or None where the store holds none at all, which is a store nobody scoped."""
    graphs = [row["g"] for row in rows(store, STANDING_Q)]
    if not graphs:
        return None
    out: dict[str, set[str]] = {}
    for r in rows(store, SCOPES_Q, graphs):
        out.setdefault(r["member"], set()).add(r["scope"])
    return Scopes({m: frozenset(s) for m, s in out.items()})
