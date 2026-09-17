"""What one action comes to in ONE world — the rows, as a collection.

A repository over situational data: given an [action](action.py) and what this agent holds, run
that action's own precondition against the world this collection was handed and shape each
binding into an `Affordance`. Nothing is stored — a row is a conclusion whose premises are stored
and would outlive them (a-situated-instance-is-kept-only-when-it-is-testimony).

**THE WORLD IS ASKED ABOUT, NOT HELD.** Every question here names one — `at` and `world` — so
one of these serves as many menus as the store has worlds to be asked about, and the precondition
names no graph to get it (#666). Which readings a premise reads is the door's to say.

**IT ASKS FOR NOTHING.** What the agent holds and which actions are worth asking are handed in.
This collection knows how to fetch rows and nothing about what is worth fetching, which is
`Afforder`'s to decide — the file this one was carved out of held both, plus a question that
belonged to the desire modality.
"""

from __future__ import annotations

from orexis_agent_progression.store import Raw, bind, bindings

from .action import Action
from .affordance import Affordance


class Affordances:
    """The rows one world admits, asked one action at a time."""

    def __init__(self, store):
        """The store whose worlds this asks about, and nothing else.

        IT HELD IDENTITY AND NO STORE for one change — the shape inverted — because moving the
        world onto the question took the door out of the constructor and left only the agent's
        URI and graph name behind. The agent is another aggregate root; both are criteria of the
        ask now, and WHICH store this is is the agent's decision, since a search asks the
        imaginarium what an imagined world affords and the present asks the belief base.
        """
        self._store = store

    def find_all_by_action(self, action: Action, about_of: dict[str, tuple[str, ...]],
                           me: str, beliefs: str, *, at=None,
                           world: str | None = None) -> list[Affordance]:
        """Every row this action affords in one world — zero, one or many.

        WHICH WORLD IS A CRITERION, `at` and `world`, and was the constructor's until the
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
        #  `$beliefs` names the agent's OWN graph, as it does for an effect rule: a premise may be
        #  something only this agent was told — an open round is one (#358) — and the default
        #  graph is public knowledge, so a walk that needs it must say so. `$wants` is a VALUES
        #  block — rows, not a term — and goes in as `Raw`; the rest are IRIs the binder renders.
        #  A precondition carrying a token nobody binds refuses rather than reaching the engine as
        #  a free variable (#500).
        q = bind(action.available, me=me, wants=Raw(wants), beliefs=beliefs)
        #  THE ROW SAYS WHICH about IT MATCHED where its select projects one — every action that
        #  filters on the want's about does now — and the want's own answers where it does not,
        #  which is only legible while the want names exactly one (#566).
        return [Affordance(action=action.uri, via=r["via"], want=r.get("want"),
                           about=r.get("about") or _sole(about_of.get(r.get("want"))),
                           direction=r.get("direction"), for_agent=r.get("for_agent"))
                for r in bindings(self._store.query_at(q, at=at, world=world))]


def _sole(abouts) -> str | None:
    """The one thing a want is about, or None where it names none — or several, which only a
    row's own binding can tell apart."""
    return abouts[0] if abouts and len(abouts) == 1 else None
