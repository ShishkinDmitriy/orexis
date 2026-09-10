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
fourth package's word, which is the test the-mind-is-six-graphs set and `orexis:Mode` now passes for
the same reason `progression:Intention` did. The modes had already made this move once, out of `market:`,
on exactly this argument.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_agent_progression.ontology import OREXIS, STATE_GRAPH
from orexis_agent_progression.store import Raw, bind, bindings

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


#  What this agent wants and what each want is ABOUT — the kernel's words only. A want with no
#  `orexis:about` is one no action query could join a lever to, and it is simply absent from the
#  VALUES block; the obligations are not here at all, because an obligation's row names whom it is owed
#  to and joins on that. (This used to read the property off the met-shape, and the kernel
#  no longer knows a want has one — the-stake-is-sensings-want.)
_WANTS_Q = """SELECT ?me ?want ?about WHERE {
  ?me orexis:holds ?want .
  ?want a orexis:Desire ; orexis:about ?about }"""


_ACTIONS_Q = """SELECT ?action ?available WHERE {
  ?action a orexis:Action ; orexis:available ?available }"""


def wants_of(desires, agent_uri: str) -> dict[str, tuple[str, ...]]:
    """Every want this agent holds that is ABOUT something, want -> what it is about. A want
    absent here — a debt, a call — is about nothing an action query could join, and the planner
    lets it range over any row of the agent's own.

    SEVERAL, because a want may be (#566): a greenhouse bed is comfortable when its soil and
    its air are both in their regions, and that is ONE want about two properties — the first
    shipped want whose plan needs two different levers. Every want the plant worlds hold names
    exactly one, and reads the same through the tuple."""
    out: dict[str, list[str]] = {}
    for r in bindings(desires(_WANTS_Q, {"me": agent_uri})):
        out.setdefault(r["want"], []).append(r["about"])
    return {w: tuple(sorted(a)) for w, a in out.items()}


def _sole(abouts) -> str | None:
    """The one thing a want is about, or None where it names none — or several, which only a
    row's own binding can tell apart."""
    return abouts[0] if abouts and len(abouts) == 1 else None


def affordances_of(query, agent_uri: str, desires, beliefs: str, state: str = STATE_GRAPH,
                   only=None) -> list[Affordance]:
    """What one agent could do, about what, through which lever — derived, never written.

    The Consulting member's prompt substrate and the reflex's worldview as data: a move with no
    row here is a move nothing should propose. Free function for the same reason `gaps_of` is —
    a test about what a world implies should not have to build an agent to ask.

    THE UNION OF WHAT THE LOADED ACTIONS SAY (#207, an-action-is-one-node): every `orexis:Action`
    in the store carries its precondition as `orexis:available`, and this runs each one with `$me`
    and the wanted `$wants` filled in — `VALUES (?want ?about) { … }`, one pair per want the
    agent holds and what its deriver says it is about — and `$beliefs` naming the agent's own
    graph.
    The action itself is the row's kind; a bound
    `?for_agent` makes the row an obligation's. Sensing brings Observe, the market Acquire and the
    host's Apply, actuation Actuate — and a new way of acting is a node in a new directory,
    never an edit here. Sorted because per-action order is no order.

    `only` is the set of actions worth asking at all — the search's RELEVANT set (#504), or
    None for every action. A precondition is a query per action per world, and a lever that
    touches nothing the want reads was already never simulated; now it is never asked
    either, so a menu that grows by unrelated domains costs a pass nothing.
    """
    #  The desired properties, asked of the desire modality once and injected into every
    #  walk: a row is wiring x want, and since the dataset split (#298) the want half lives
    #  in a store of its own. An empty block is legal SPARQL and yields no rows — an agent
    #  with no desires has no menu.
    about_of = wants_of(desires, agent_uri)
    #  ONE PAIR PER (want, about), so a want about two properties offers a row for each and
    #  each action matches the half it serves (#566).
    wants = " ".join(f"(<{w}> <{a}>)" for w, abouts in sorted(about_of.items()) for a in abouts)
    rows = []
    for action in bindings(query(_ACTIONS_Q)):
        if only is not None and action["action"] not in only:
            continue
        #  `$beliefs` names the agent's OWN graph, as it does for an effect rule: a premise
        #  may be something only this agent was told — an open round is one (#358) — and
        #  the default graph is public knowledge, so a walk that needs it must say so.
        #  `$state` names the readings a premise may read — this agent's, or the graph of a
        #  world a plan is imagining, so a row whose premise an earlier step made true (stock
        #  after a refill, #359) appears in the menu of THAT world and not of this one.
        #  `$wants` is a VALUES block — rows, not a term — and goes in as `Raw`; the rest
        #  are IRIs the binder renders. A precondition carrying a token nobody binds refuses.
        q = bind(action["available"], me=agent_uri, wants=Raw(wants), beliefs=beliefs,
                 state=state)
        #  THE ROW SAYS WHICH about IT MATCHED where its select projects one — every action
        #  that filters on the want's about does now — and the want's own answers where it does
        #  not, which is only legible while the want names exactly one (#566).
        rows += [Affordance(action=action["action"], via=r["via"], want=r.get("want"),
                            about=r.get("about") or _sole(about_of.get(r.get("want"))),
                            direction=r.get("direction"), for_agent=r.get("for_agent"))
                 for r in bindings(query(q))]
    return sorted(rows, key=lambda a: (a.want or "", a.action, a.for_agent or ""))
