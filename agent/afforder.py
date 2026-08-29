"""The AFFORDER: the service that answers what an agent could do, about what, through which lever.

It reads the MENU — the modality holding the action templates — and runs each template's
precondition against the world it is asked about. The menu is the repository; affording is what
this does with it.

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

from .ontology import AG, STATE_GRAPH
from .store import bindings

@dataclass(frozen=True)
class Affordance:
    """One row of the menu: an action, the WANT it serves, the lever — for an action that
    moves anything — which way it moves it, and whether it is mine to CHOOSE or to HONOUR.

    Whom it serves is the #218 half: a row of my own is an option a deliberator ranges over;
    one owed to somebody is a duty exercised on a valid presentation and never proposed.

    `want` is the desire's node, and `about` is what that want is ABOUT — `ag:about`, stated
    by whoever derived the want, and opaque here: sensing says a region want is about a
    property, and its own action queries join a lever to it. The kernel carries it from the
    want to the rule (`$about`) and never reads it. Both None on a row that serves any want —
    a host's Offering — or a duty's, which names whom it is owed to instead.
    """

    action: str
    via: str
    want: str | None = None
    about: str | None = None
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


#  What this agent wants and what each want is ABOUT — the kernel's words only. A want with no
#  `ag:about` is one no action query could join a lever to, and it is simply absent from the
#  VALUES block; the duties are not here at all, because a duty's row names whom it is owed
#  to and joins on that. (This used to read the property off the met-shape, and the kernel
#  no longer knows a want has one — the-stake-is-sensings-want.)
_WANTS_Q = """SELECT ?want ?about WHERE {
  <%s> ag:holds ?want .
  ?want a ag:Desire ; ag:about ?about }"""


_ACTIONS_Q = """SELECT ?action ?available WHERE {
  ?action a ag:Action ; ag:available ?available }"""


def wants_of(desires, agent_uri: str) -> dict[str, str]:
    """Every want this agent holds that is ABOUT something, want -> about. A want absent here
    — a debt, a call — is about nothing an action query could join, and the planner lets it
    range over any row of the agent's own."""
    return {r["want"]: r["about"] for r in bindings(desires(_WANTS_Q % agent_uri))}


def affordances_of(query, agent_uri: str, desires, beliefs: str, state: str = STATE_GRAPH) -> list[Affordance]:
    """What one agent could do, about what, through which lever — derived, never written.

    The Consulting member's prompt substrate and the reflex's worldview as data: a move with no
    row here is a move nothing should propose. Free function for the same reason `gaps_of` is —
    a test about what a world implies should not have to build an agent to ask.

    THE UNION OF WHAT THE LOADED ACTIONS SAY (#207, an-action-is-one-node): every `ag:Action`
    in the store carries its precondition as `ag:available`, and this runs each one with `$me`
    and the wanted `$wants` filled in — `VALUES (?want ?about) { … }`, one pair per want the
    agent holds and what its deriver says it is about — and `$beliefs` naming the agent's own
    graph.
    The action itself is the row's kind; a bound
    `?for_agent` makes the row a duty's. Sensing brings Observe, the market Acquire and the
    host's Apply, actuation Actuate — and a new way of acting is a node in a new directory,
    never an edit here. Sorted because per-action order is no order.
    """
    #  The desired properties, asked of the desire modality once and injected into every
    #  walk: a row is wiring x want, and since the dataset split (#298) the want half lives
    #  in a store of its own. An empty block is legal SPARQL and yields no rows — an agent
    #  with no desires has no menu.
    about_of = wants_of(desires, agent_uri)
    wants = " ".join(f"(<{w}> <{a}>)" for w, a in sorted(about_of.items()))
    rows = []
    for action in bindings(query(_ACTIONS_Q)):
        #  `$beliefs` names the agent's OWN graph, as it does for an effect rule: a premise
        #  may be something only this agent was told — an open round is one (#358) — and
        #  the default graph is public knowledge, so a walk that needs it must say so.
        #  `$state` names the readings a premise may read — this agent's, or the graph of a
        #  world a plan is imagining, so a row whose premise an earlier step made true (stock
        #  after a refill, #359) appears in the menu of THAT world and not of this one.
        q = (action["available"].replace("$me", f"<{agent_uri}>")
             .replace("$wants", wants).replace("$beliefs", f"<{beliefs}>")
             .replace("$state", f"<{state}>"))
        rows += [Affordance(action=action["action"], via=r["via"], want=r.get("want"),
                            about=about_of.get(r.get("want")) or r.get("about"),
                            direction=r.get("direction"), for_agent=r.get("for_agent"))
                 for r in bindings(query(q))]
    return sorted(rows, key=lambda a: (a.want or "", a.action, a.for_agent or ""))
