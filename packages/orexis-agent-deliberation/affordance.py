"""One affordance: something this agent could do NOW, about what, through which lever.

The MODEL. `Affordances` beside this file is the collection of them — a singular file holds what
a thing is and its plural holds where they are kept, which is this package's file naming
(a-repository-is-named-for-what-it-holds).

**AN AFFORDANCE IS NOT AN ACTION**, and the two were easy to confuse while one file held the
model, the query and the assembling. An [action](knowledge/domain/action.md) is a SCHEMA: a node
a package declares in its `actions.ttl`, carrying the precondition that says when it is possible,
stored, and outliving everything — which is why it can be stored at all. An affordance is one
grounded ROW: this action, through this lever, serving this want, in the world being asked about
and at the instant being asked about. Derived on every ask and written nowhere, so a row can
never outlive the plumbing it was concluded from. See knowledge/domain/affordance.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Affordance:
    """One row of the menu: an action, the WANT it serves, the lever — for an action that
    moves anything — which way it moves it, and whether it is mine to CHOOSE or to HONOUR.

    Whom it serves is the #218 half: a row of my own is an option a deliberator ranges over;
    one owed to somebody is an obligation exercised on a valid presentation and never proposed.

    `want` is the desire's node, and `about` is what that want is ABOUT — `orexis:about`, stated
    by whoever derived the want, and opaque here: sensing says a region want is about a
    property, and its own action queries join a lever to it. The kernel carries it from the
    want to the rule (`$about`) and never reads it. Both None on a row that serves any want —
    a host's Offering — or an obligation's, which names whom it is owed to instead.
    """

    action: str
    via: str
    want: str | None = None
    about: str | None = None
    direction: str | None = None
    #  Whom an honoured row serves — the counterparty entitled to demand this lever. Absent on
    #  a chosen row, which serves nobody but the agent itself. It is what lets a OBLIGATION find its
    #  means: an obligation names who it is owed to, and the row that answers is the one
    #  honoured for exactly that agent.
    for_agent: str | None = None

    @property
    def is_own(self) -> bool:
        """Mine to range over — serves nobody but me. A row that names whom it is owed to is
        an obligation's, exercised for that counterparty and never proposed for my own gap. The one
        column says it; there is no mode term any more (an-action-is-one-node)."""
        return self.for_agent is None
