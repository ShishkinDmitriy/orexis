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

Each is a SET, replacing the one before: a point per member, measured `Holding` or `Conflict`, and one
point measured `Holdings` or `Conflicts` saying how many there are, so an empty set is said too. A
member's tags are coordination's words for it — the origin, the peer, the constraint and the thing, each
an IRI's local name, and `n`, its place in the set, since the series store keeps one point per tag set
and instant — and its fields the values on the constraint's key, by each predicate's local name: a
number where the value is one, the text of anything else. Every name is read off what was said, so
this module spells no domain word.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import local_of

from .holdings import Holding

ASKED, SAID, FORESEEN = "asked", "said", "foreseen"
_NUMBERS = {"http://www.w3.org/2001/XMLSchema#" + t for t in ("integer", "decimal", "double", "float", "int", "long")}


@dataclass(frozen=True)
class Held:
    """The holdings of one `origin` — `asked`, `said` or `foreseen` — under `constraint` with `peer`, as the
    part said or laid them at `at`: all of them, replacing those said before."""
    at: datetime
    origin: str
    peer: str
    constraint: str
    holdings: tuple[Holding, ...] = ()

    def point(self) -> list[dict]:
        tags = {"origin": self.origin, "peer": local_of(self.peer), "constraint": local_of(self.constraint)}
        out = [{"measurement": "Holdings", "tags": dict(tags), "fields": {"count": len(self.holdings)}, "time": self.at}]
        for n, h in enumerate(self.holdings):
            fields = {local_of(p): _value(v) for p, v in h.values}
            fields["from"] = h.start.isoformat() if h.start else ""
            fields["until"] = h.end.isoformat() if h.end else ""
            fields["taken"] = h.taken
            out.append({"measurement": "Holding", "tags": {**tags, "thing": local_of(h.thing), "n": str(n)},
                        "fields": fields, "time": self.at})
        return out


@dataclass(frozen=True)
class Conflict:
    """One conflict as the agent concluded it: with `peer` over `constraint`, whether it `standing`, whether the
    peer is `silent`, the `round` its draw is in and who won that draw, where anybody has."""
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

    def point(self) -> list[dict]:
        out = [{"measurement": "Conflicts", "tags": {}, "fields": {"count": len(self.conflicts)}, "time": self.at}]
        for c in self.conflicts:
            out.append({"measurement": "Conflict", "tags": {"peer": local_of(c.peer), "constraint": local_of(c.constraint)},
                        "fields": {"standing": c.standing, "silent": c.silent, "round": c.round,
                                   "won_by": local_of(c.won_by) if c.won_by else ""},
                        "time": self.at})
        return out


def _value(term: ox.Term):
    if isinstance(term, ox.Literal) and term.datatype.value in _NUMBERS:
        return float(term.value)
    return local_of(term.value) if isinstance(term, ox.NamedNode) else str(term.value)
