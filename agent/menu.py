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

from . import loader
from .ontology import AG
from .store import bindings

#  Whether a row is mine to choose or a lever others may demand — the kernel's words now, and
#  the menu's own. Absent means chosen, so a branch written before the distinction keeps its
#  meaning.
CHOSEN = AG + "Chosen"
HONOURED = AG + "Honoured"

@dataclass(frozen=True)
class Affordance:
    """One row of the menu: a means, the property it is about, the lever, — for a means that
    moves anything — which way it moves it, and whether it is mine to CHOOSE or to HONOUR.

    The mode is the #218 half: a chosen row is an option a deliberator ranges over; an
    honoured row is a duty exercised on a valid presentation and never proposed. Absent
    means chosen, so a branch written before the distinction keeps its meaning.
    """

    means: str
    observed_property: str
    via: str
    direction: str | None = None
    mode: str = CHOSEN
    #  Whom an honoured row serves — the counterparty entitled to demand this lever. Absent on
    #  a chosen row, which serves nobody but the agent itself. It is what lets a DUTY find its
    #  means: an obligation names who it is owed to, and the row that answers is the one
    #  honoured for exactly that agent.
    for_agent: str | None = None

    @property
    def is_chosen(self) -> bool:
        return self.mode == CHOSEN


#  Through `ag:metWhen`, since the desire became a node carrying its shape: the ShouldBecome
#  force lives on the met-shape's property shapes, and reading it there keeps the envelope
#  (Warning) and the freshness want (sh:sparql, no sh:property) out, exactly as before.
_DESIRED_Q = """SELECT DISTINCT ?property WHERE {
  <%s> ag:holds ?desire .
  ?desire ssn:forProperty ?property ;
          ag:metWhen/sh:property/sh:severity ag:ShouldBecome }"""


def menu_of(query, agent_uri: str, desires) -> list[Affordance]:
    """What one agent could do, about what, through which lever — derived, never written.

    The Consulting member's prompt substrate and the reflex's worldview as data: a move with no
    row here is a move nothing should propose. Free function for the same reason `gaps_of` is —
    a test about what a world implies should not have to build an agent to ask.

    THE UNION OF WHAT THE LOADED PACKAGES CONTRIBUTE (#207): each package may ship an
    `affordances.rq` — its rows, its preconditions as its own walk — and this collects them,
    so the menu's KINDS stop being a registry in this package's directory. Sensing ships the
    Observe branch, the market ships Acquire, and a new way of acting is a new directory:
    ontology as the tool's schema, affordances.rq as its availability, a module as its
    implementation — or no module at all, where execution reduces to an existing actor.
    Sorted here because ORDER BY lived in the one big query; per-file order is no order.
    """
    #  The desired properties, asked of the desire modality once and injected into every
    #  walk: a row is wiring x want, and since the dataset split (#298) the want half lives
    #  in a store of its own. An empty block is legal SPARQL and yields no rows — an agent
    #  with no desires has no menu, exactly as when the shape pattern sat in each file.
    props = " ".join(f"<{r['property']}>" for r in bindings(desires(_DESIRED_Q % agent_uri)))
    rows = []
    for path in loader.affordance_files() + loader.honoured_files():
        q = (path.read_text().replace("$me", f"<{agent_uri}>")
             .replace("$properties", props))
        rows += [Affordance(means=r["means"], observed_property=r["property"], via=r["via"],
                            direction=r.get("direction"), mode=r.get("mode") or CHOSEN,
                            for_agent=r.get("buyer"))
                 for r in bindings(query(q))]
    return sorted(rows, key=lambda a: (a.observed_property, a.means, a.mode))


