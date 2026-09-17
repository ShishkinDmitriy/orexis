"""Every affordance this agent has in ONE world at ONE instant, as a collection.

A COLLECTION THAT IS MADE, not held — `Judgments`' shape, and for the same reason. Nothing stores
an affordance: each row is an action's own precondition run against the world being asked about,
so asking twice in two worlds gives two answers and that is the point. The convention record calls
this out as the case where a repository's name is right and its work is a service's
(a-repository-is-named-for-what-it-holds), and the name it settles on is this one.

**PARAMETERISED BY THE WORLD, not by the agent.** `Wants` is handed a store and `Judgments` the
choir; this is handed a DOOR — `beliefs.query_at` for what is, `imaginarium.query_at` for a world
a plan is imagining — so one agent has as many menus as there are worlds to ask about, and the
precondition names no graph to get it (#666). Which readings a premise reads is the door's to say.

It was `afforder.py`, named for a service that had no class in it. The file held the model, the
assembling, and a question that belonged to another collection.
"""

from __future__ import annotations

from orexis_agent_progression.store import Raw, bind, bindings

from .affordance import Affordance

_ACTIONS_Q = """SELECT ?action ?available WHERE {
  ?action a orexis:Action ; orexis:available ?available }"""


class Affordances:
    """What one agent could do in one world — derived on every ask, written nowhere."""

    def __init__(self, query, agent_uri: str, desires, beliefs: str):
        #  The DOOR this menu is about: whichever world, at whichever instant, the caller means.
        self._query = query
        self._me = agent_uri
        #  The desire modality, for what this agent holds and what each of them is about. The
        #  OBJECT and not its query function, because the question is the collection's own.
        self._desires = desires
        self._beliefs = beliefs

    def _sole(self, abouts) -> str | None:
        """The one thing a want is about, or None where it names none — or several, which only a
        row's own binding can tell apart."""
        return abouts[0] if abouts and len(abouts) == 1 else None


    def find_all(self, only=None) -> list[Affordance]:
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
        about_of = self._desires.abouts(self._me)
        #  ONE PAIR PER (want, about), so a want about two properties offers a row for each and
        #  each action matches the half it serves (#566).
        wants = " ".join(f"(<{w}> <{a}>)" for w, abouts in sorted(about_of.items()) for a in abouts)
        rows = []
        for action in bindings(self._query(_ACTIONS_Q)):
            if only is not None and action["action"] not in only:
                continue
            #  `$beliefs` names the agent's OWN graph, as it does for an effect rule: a premise
            #  may be something only this agent was told — an open round is one (#358) — and
            #  the default graph is public knowledge, so a walk that needs it must say so.
            #  WHICH READINGS a premise reads is the DOOR'S to say (#666), never the text's:
            #  `query` was handed a world by whoever asked — this agent's own, or the one a plan
            #  is imagining — so a row whose premise an earlier step made true (stock after a
            #  refill, #359) appears in the menu of THAT world and not of this one, and the
            #  precondition names no graph to get it.
            #  `$wants` is a VALUES block — rows, not a term — and goes in as `Raw`; the rest
            #  are IRIs the binder renders. A precondition carrying a token nobody binds refuses.
            q = bind(action["available"], me=self._me, wants=Raw(wants), beliefs=self._beliefs)
            #  THE ROW SAYS WHICH about IT MATCHED where its select projects one — every action
            #  that filters on the want's about does now — and the want's own answers where it does
            #  not, which is only legible while the want names exactly one (#566).
            rows += [Affordance(action=action["action"], via=r["via"], want=r.get("want"),
                                about=r.get("about") or self._sole(about_of.get(r.get("want"))),
                                direction=r.get("direction"), for_agent=r.get("for_agent"))
                     for r in bindings(self._query(q))]
        return sorted(rows, key=lambda a: (a.want or "", a.action, a.for_agent or ""))
