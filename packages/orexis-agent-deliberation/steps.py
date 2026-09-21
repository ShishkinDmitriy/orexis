"""What one action comes to in ONE world — the steps it affords, as a collection.

A repository over situational data: given an [action](action.py) and what this agent holds, run
that action's own precondition against the world this collection was handed and shape each
binding into a `Step` — one pair per parameter the action declares it takes. Nothing is stored:
a step a world affords is a conclusion whose premises are stored and would outlive them
(a-situated-instance-is-kept-only-when-it-is-testimony).

**A STEP A WORLD AFFORDS AND A STEP A PLAN HOLDS ARE ONE THING.** This yielded an `Affordance`
once, which carried four of a step's fields and was copied into one by `Step.from_row` the
moment anything wanted to plan with it. Two classes for one shape is how a reader comes to
believe there are two concepts; what differs is the MOMENT, not the thing.

**THE WORLD IS ASKED ABOUT, NOT HELD.** Every question here names one — `at` and `world` — so
one of these serves as many worlds as the store has to be asked about, and the precondition
names no graph to get it (#666). Which readings a premise reads is the door's to say.

**IT ASKS FOR NOTHING.** What the agent holds and which actions are worth asking are handed in.
This collection knows how to fetch steps and nothing about what is worth fetching, which is the
caller's — the file this one was carved out of held both, plus a question that belonged to the
desire modality.
"""

from __future__ import annotations

from orexis_agent_progression.store import Raw, bind, bindings

from .action import Action
from orexis_agent_progression.act import Step
from orexis_agent_progression.ontology import FORESEEN, local_of
from orexis_agent_progression import clock


class Steps:
    """The steps one world admits, asked one action at a time."""

    def __init__(self, store):
        """The store whose worlds this asks about, and nothing else.

        IT HELD IDENTITY AND NO STORE for one change — the shape inverted — because moving the
        world onto the question took the door out of the constructor and left only the agent's
        URI and graph name behind. The agent is another aggregate root; both are criteria of the
        ask now, and WHICH store this is is the agent's decision, since a search asks the
        imaginarium what an imagined world affords and the present asks the belief base.
        """
        self._store = store

    def find_all(self, actions, about_of: dict[str, tuple[str, ...]], me: str, picks: str,
                 *, graphs=None, only=None) -> list[Step]:
        """Every step this agent could take in one world, name-ordered.

        THIS WAS A SERVICE — an `Afforder` between two collections, holding the templates and
        what the agent holds, and looping one into the other. What it actually did was fetch
        nothing and decide nothing: the actions worth asking are the caller's `only`, what the
        agent holds is handed in, and the merge is a loop and a sort. A thing that decides
        nothing is a repository's support function rather than a service, so it is one.

        EVERY IDENTITY IS A CRITERION, which is what keeps this a collection over a store and
        nothing else: `actions` is the templates the caller thinks are worth asking, `about_of`
        what the agent holds and what each want is about, `me` and `picks` whose world this is.
        The inner ask already took all four; this one takes the list as well.

        `only` is the set of actions worth asking at all — the search's RELEVANT set (#504), or
        None for every action. A precondition is a query per action per world, and an action
        that touches nothing the want reads was already never simulated; skipped here it is
        never asked either, so a vocabulary that grows by unrelated domains costs a pass nothing.
        """
        found: list[Step] = []
        for action in actions:
            if only is not None and action.uri not in only:
                continue
            found += self.find_all_by_action(action, about_of, me, picks, graphs=graphs)
        #  Sorted because per-action order is no order.
        return sorted(found, key=lambda s: (s.want or "", s.action, s.for_agent or ""))

    def find_all_by_action(self, action: Action, about_of: dict[str, tuple[str, ...]],
                           me: str, picks: str, *, graphs=None) -> list[Step]:
        """Every step this action affords in one world — zero, one or many.

        WHICH WORLD IS A CRITERION — `graphs`, the world asked about as the list of graphs
        the caller built for it, an instant and a place in one — and was the constructor's until the
        sovereign asked why the planner was building collections: it built one per node, because
        the world was in the constructor and the world is the thing that moves. A world is part
        of the QUESTION — *what could I do there* — not part of what this collection is. So is
        `me`, and so is which graph is the agent's own.

        ZERO IS ORDINARY and is the commonest answer: nine of the eleven actions a simulation
        agent loads afford it nothing, because their preconditions do not bind. MANY is ordinary
        too — a supplier with three valves affords `Serving` three times, one per valve, and
        choosing between them is the whole of what a plan does at that step.

        `about_of` is what the agent holds and what each of them is ABOUT, handed in by the
        service rather than fetched: one `(want, about)` pair per row of the `VALUES` block, so a
        want about two properties offers a row for each and each action matches the half it
        serves (#566). An empty block is legal SPARQL and yields no rows — an agent with no
        desires has no menu.
        """
        wants = " ".join(f"(<{w}> <{a}>)" for w, abouts in sorted(about_of.items()) for a in abouts)
        #  `$picks` names the agent's OWN graph, as it does for an effect rule: a premise may be
        #  something only this agent was told — an open round is one (#358) — and the default
        #  graph is public knowledge, so a walk that needs it must say so. `$wants` is a VALUES
        #  block — rows, not a term — and goes in as `Raw`; the rest are IRIs the binder renders.
        #  A precondition carrying a token nobody binds refuses rather than reaching the engine as
        #  a free variable (#500).
        q = bind(action.available, me=me, wants=Raw(wants), picks=picks)
        #  THE ROW IS WHAT THE PRECONDITION BOUND, held to what the action says it TAKES: one
        #  pair per declared parameter the select projected, sorted so identity is the binding
        #  and nothing downstream has to agree on an order. A projected variable the action
        #  does not declare is ignored, and a declared parameter the row left unbound is
        #  absent — an action with an OPTIONAL hop affords rows of two shapes, and both are
        #  honest.
        params = {local_of(p): p for p in action.takes}
        return [Step(action=action.uri,
                     binding=tuple(sorted((iri, r[local]) for local, iri in params.items()
                                          if r.get(local))),
                     want=r.get("want"), for_agent=r.get("for_agent"))
                for r in bindings(self._store.query(q, graphs if graphs is not None else
                                                     #  THE PRESENT, where no world is handed in: what a rule
                                                     #  reads and what is expected, as this store holds them now.
                                                     self._store.graphs_of(*FORESEEN, at=clock.now())))]
