"""The menu: what an agent COULD do, about what, through which lever.

*Could do* is one of the six modalities the mind is made of, and this is where it is
materialised — derived on every ask and never stored, so a row can never outlive the plumbing
it was concluded from. See knowledge/domain/affordance.md.

**Kernel, and it was always going to be.** This lived in the deliberation package, which is
where the rows were first needed; but three OTHER packages already reached for its vocabulary to
describe their own rows — sensing, actuation and market each bound its Chosen mode by hand
in their `affordances.rq`. A word three packages must speak to describe themselves is not the
fourth package's word, which is the test the-mind-is-six-graphs set and `ag:Mode` now passes for
the same reason `ag:Intention` did. The modes had already made this move once, out of `market:`,
on exactly this argument.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ontology import AG
from .store import bindings

@dataclass(frozen=True)
class Affordance:
    """One row of the menu: a means, the property it is about, the lever, — for a means that
    moves anything — which way it moves it, and whether it is mine to CHOOSE or to HONOUR.

    Whom it serves is the #218 half: a row of my own is an option a deliberator ranges over;
    one owed to somebody is a duty exercised on a valid presentation and never proposed.
    """

    means: str
    observed_property: str
    via: str
    direction: str | None = None
    #  Whom an honoured row serves — the counterparty entitled to demand this lever. Absent on
    #  a chosen row, which serves nobody but the agent itself. It is what lets a DUTY find its
    #  means: an obligation names who it is owed to, and the row that answers is the one
    #  honoured for exactly that agent.
    for_agent: str | None = None

    @property
    def is_own(self) -> bool:
        """Mine to range over — serves nobody but me. A row that names whom it is owed to is
        a duty's, exercised for that counterparty and never proposed for my own gap. The one
        column says it; there is no mode term any more (an-action-is-one-node)."""
        return self.for_agent is None


#  Through `ag:metWhen`, since the desire became a node carrying its shape: the ShouldBecome
#  force lives on the met-shape's property shapes, and reading it there keeps the envelope
#  (Warning) and the freshness want (sh:sparql, no sh:property) out, exactly as before.
_DESIRED_Q = """SELECT DISTINCT ?property WHERE {
  <%s> ag:holds ?desire .
  ?desire ssn:forProperty ?property ;
          ag:metWhen/sh:property/sh:severity ag:ShouldBecome }"""


_ACTIONS_Q = """SELECT ?means ?available WHERE {
  ?action a ag:Action ; ag:means ?means ; ag:available ?available }"""


def menu_of(query, agent_uri: str, desires) -> list[Affordance]:
    """What one agent could do, about what, through which lever — derived, never written.

    The Consulting member's prompt substrate and the reflex's worldview as data: a move with no
    row here is a move nothing should propose. Free function for the same reason `gaps_of` is —
    a test about what a world implies should not have to build an agent to ask.

    THE UNION OF WHAT THE LOADED ACTIONS SAY (#207, an-action-is-one-node): every `ag:Action`
    in the store carries its precondition as `ag:available`, and this runs each one with `$me`
    and the desired `$properties` filled in. The action's `ag:means` is the row's; a bound
    `?for_agent` makes the row a duty's. Sensing brings Observe, the market Acquire and the
    host's Apply, actuation Actuate — and a new way of acting is a node in a new directory,
    never an edit here. Sorted because per-action order is no order.
    """
    #  The desired properties, asked of the desire modality once and injected into every
    #  walk: a row is wiring x want, and since the dataset split (#298) the want half lives
    #  in a store of its own. An empty block is legal SPARQL and yields no rows — an agent
    #  with no desires has no menu.
    props = " ".join(f"<{r['property']}>" for r in bindings(desires(_DESIRED_Q % agent_uri)))
    rows = []
    for action in bindings(query(_ACTIONS_Q)):
        q = (action["available"].replace("$me", f"<{agent_uri}>")
             .replace("$properties", props))
        rows += [Affordance(means=action["means"], observed_property=r["property"],
                            via=r["via"], direction=r.get("direction"),
                            for_agent=r.get("for_agent"))
                 for r in bindings(query(q))]
    return sorted(rows, key=lambda a: (a.observed_property, a.means, a.for_agent or ""))
