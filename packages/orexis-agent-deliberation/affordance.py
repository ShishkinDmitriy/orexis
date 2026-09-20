"""One affordance: something this agent could do NOW, with its parameters bound.

The MODEL. `Affordances` beside this file is the collection of them — a singular file holds what
a thing is and its plural holds where they are kept, which is this package's file naming
(a-repository-is-named-for-what-it-holds).

**AN AFFORDANCE IS NOT AN ACTION**, and the two were easy to confuse while one file held the
model, the query and the assembling. An [action](knowledge/domain/action.md) is a SCHEMA: a node
a package declares in its `actions.ttl`, carrying the parameters it takes and the precondition
that says when it is possible, stored, and outliving everything — which is why it can be stored
at all. An affordance is one grounded ROW: this action with these parameters bound, serving this
want, in the world being asked about and at the instant being asked about. Derived on every ask
and written nowhere, so a row can never outlive the plumbing it was concluded from. See
knowledge/domain/affordance.md.

**THE BINDING IS OPAQUE HERE.** An action declares what it takes (`orexis:takes`) and its
precondition projects exactly those; the kernel carries the pairs, names them in identity and
writes them down, and interprets none of them. It had five named columns once — `via`, `about`,
`direction` and the rest — which is how a disk came to be called a lever and a peg a property:
a domain with two parameters had nowhere to put the second but the slot named for the first.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Affordance:
    """One row of the menu: an action, the parameters it is bound with, the WANT it serves, and
    whether it is mine to CHOOSE or to HONOUR.

    Whom it serves is the #218 half: a row of my own is an option a deliberator ranges over;
    one owed to somebody is an obligation exercised on a valid presentation and never proposed.

    `binding` is the pairs the precondition bound, sorted by parameter so two rows of one action
    compare and hash the same way — and it IS the row's identity, which is what the world names
    and the signature states. The kernel never reads a value: what `market:venue` or `hanoi:disk`
    means is the package's, and the rule that declared the parameter is the only thing that
    joins on it.

    `want` is the desire's node, carried from the row to the rule and never read here. Both it
    and `for_agent` are the kernel's own, because the search filters on them: which want a step
    advances, and whether the row is mine to propose. A row owed to someone names the want it
    serves AND whom it is owed to — the market joins its serve to the want that is about the
    debt, so the search takes it by the want's name and never learns what a counterparty is.
    """

    action: str
    binding: tuple[tuple[str, str], ...] = ()
    want: str | None = None
    #  Whom an honoured row serves — the counterparty entitled to demand it. Absent on a chosen
    #  row, which serves nobody but the agent itself. It is what lets an OBLIGATION find its
    #  action: an obligation names who it is owed to, and the row that answers is the one
    #  honoured for exactly that agent.
    for_agent: str | None = None

    @property
    def is_own(self) -> bool:
        """Mine to range over — serves nobody but me. A row that names whom it is owed to is
        an obligation's, exercised for that counterparty and never proposed for my own gap. The one
        column says it; there is no mode term any more (an-action-is-one-node)."""
        return self.for_agent is None

    def value_of(self, parameter: str) -> str | None:
        """What this row bound one parameter to, by its IRI, or None where it bound none.

        The only door into a binding, and every caller of it is the package that declared the
        parameter: actuation asks for its valve, the market for its venue. Nothing in the kernel
        calls this.
        """
        return next((v for p, v in self.binding if p == parameter), None)
