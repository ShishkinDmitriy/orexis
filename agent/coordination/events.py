"""What coordination says happened — every event its part's signals carry, and which are history.

Coordination emits nothing another part acts on: what it asks and answers goes by speech, and what it
yields to is laid as forecasts the planner reads. Its events are for whoever watches the agent, so each
is made only where its signal is heard (`agent.lifecycle`), and nothing is read for one where no history
store is loaded.

THREE THINGS ARE HISTORY, each said whole at the instant the part did it, so a replay knows at any
instant what the agent stood on:
- the HOLDINGS it asked with, its own, as the question carried them (`asked`);
- the holdings it LAID of a peer, as the peer said them (`said`) or as it foresaw them of a silent peer
  (`foreseen`) — the second told from the first by whether the peer acts for the thing;
- its CONFLICTS, each with its peer, its constraint, whether it stands, whether the peer is silent, the
  round and who won it.

Each is a SET, replacing the one before, and an event in the journal (`agent/journal.py`) in coordination's own
words — the words a question carries its holdings in: `coordination:Asked`, `coordination:Said` or
`coordination:Foreseen`, each a `coordination:Held`, with the peer (`coordination:peer`), the constraint
(`coordination:over`) and each holding (`coordination:holding`) — the thing it is `coordination:of`, its values on the
constraint's key under their own predicates, `coordination:from`, `coordination:until`, `coordination:taken`; and
`coordination:Concluded`, with each `coordination:conflict` as the agent concluded it, under the conflict's own name. A set said empty is an event
with no member. Every name is read off what was said, so this module spells no domain word.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.journal import instant, literal, mint

from .holdings import Holding

ASKED, SAID, FORESEEN = "asked", "said", "foreseen"
COORDINATION = "http://example.org/orexis/coordination#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_KIND = {ASKED: "Asked", SAID: "Said", FORESEEN: "Foreseen"}


def _term(name: str) -> ox.NamedNode:
    return ox.NamedNode(COORDINATION + name)


@dataclass(frozen=True)
class Held:
    """The holdings of one `origin` — `asked`, `said` or `foreseen` — under `constraint` with `peer`, as the
    part said or laid them at `at`: all of them, replacing those said before."""
    at: datetime
    origin: str
    peer: str
    constraint: str
    holdings: tuple[Holding, ...] = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the set, each holding a node of its own."""
        out = [ox.Triple(node, _TYPE, _term(_KIND[self.origin])), ox.Triple(node, _term("peer"), ox.NamedNode(self.peer)),
               ox.Triple(node, _term("over"), ox.NamedNode(self.constraint))]
        for h in self.holdings:
            held = mint()
            out += [ox.Triple(node, _term("holding"), held), ox.Triple(held, _TYPE, _term("Holding")),
                    ox.Triple(held, _term("of"), ox.NamedNode(h.thing)), ox.Triple(held, _term("taken"), literal(h.taken))]
            #  WHAT THE THING IS stays the thing's: a key's type is said of it, and the holding holds the rest.
            out += [ox.Triple(ox.NamedNode(h.thing), _TYPE, v) if p == _TYPE.value else ox.Triple(held, ox.NamedNode(p), v)
                    for p, v in h.values]
            if h.start:
                out.append(ox.Triple(held, _term("from"), instant(h.start)))
            if h.end:
                out.append(ox.Triple(held, _term("until"), instant(h.end)))
        return out


@dataclass(frozen=True)
class Conflict:
    """One conflict as the agent concluded it: with `peer` over `constraint`, whether it `standing`, whether the
    peer is `silent`, the `round` its draw is in and who won that draw, where anybody has; named `conflict`, as both
    agents name it."""
    conflict: str
    peer: str
    constraint: str
    standing: bool
    silent: bool
    round: int
    won_by: str | None = None


@dataclass(frozen=True)
class Concluded:
    """Every conflict the agent holds, as it concluded them at `at`: all of them, replacing those said before."""
    at: datetime
    conflicts: tuple[Conflict, ...] = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: every conflict, each a node of its own."""
        out = [ox.Triple(node, _TYPE, _term("Concluded"))]
        for c in self.conflicts:
            conflict = ox.NamedNode(c.conflict)
            out += [ox.Triple(node, _term("conflict"), conflict), ox.Triple(conflict, _TYPE, _term("Conflict")),
                    ox.Triple(conflict, _term("with"), ox.NamedNode(c.peer)), ox.Triple(conflict, _term("over"), ox.NamedNode(c.constraint)),
                    ox.Triple(conflict, _term("standing"), literal(c.standing)), ox.Triple(conflict, _term("silent"), literal(c.silent)),
                    ox.Triple(conflict, _term("round"), literal(int(c.round)))]
            if c.won_by:
                out.append(ox.Triple(conflict, _term("wonBy"), ox.NamedNode(c.won_by)))
        return out
