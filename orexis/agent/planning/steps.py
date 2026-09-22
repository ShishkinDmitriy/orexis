"""The MENU: what every action the store holds comes to in ONE world.

THE THIRD OF THREE FILES ABOUT AN ACTION, and the only one that asks which fillings there are.
`effects.py` beside it answers what one costs and when it lands; `apply_effects.py` runs its
effect into a world. This runs its `orexis:available` precondition against the world it is
handed and shapes each row into a `Step` — one pair per parameter the action declares it
takes, one step per action per legal filling.

Nothing is stored: what a world admits is a conclusion whose premises are stored and would
outlive them (a-situated-instance-is-kept-only-when-it-is-testimony).

**A STEP IS AN ACTION PICKED FOR EXECUTION**, and what a world admits is what the search picks
FROM — one per action per legal filling. They are one class, because what a search adds when it
picks is absent on one nobody picked, and that is what `None` in those fields means. This
yielded an `Affordance` once, copied into a step by `Step.from_row` the moment anything wanted
to plan with it: two classes for one shape, and a second word doing no work the absent fields
were not already doing.

**THE WORLD IS ASKED ABOUT, NOT HELD.** `graphs` says which one, so one function serves as
many worlds as there are to ask about, and the precondition names no graph to get it (#666).
Which readings a premise reads is the caller's to say.

**AND EVERY ACTION IS ASKED.** There was an `only` parameter — the set worth asking at all,
which the relevance closure computes from what a want READS — and no caller passed it, the
closure being one of the things this tree does not have. A precondition is a query per action
per world, so narrowing is real the day a vocabulary grows by unrelated domains; it returns
with the closure that would compute it.
"""

from __future__ import annotations

from orexis.agent.store import bind, bindings, graphs_of, query, remember

from orexis.agent.execution.act import Step
from orexis.agent.ontology import FORESEEN, local_of
from orexis.agent import clock
from orexis.agent.ontology import PUBLIC

#  WHAT THE VOCABULARY DECLARES, and the only reason to ask: an action carries the SELECT that
#  says when it is possible, and running it is the only way to learn what a world affords.
#  There is nothing to traverse from — a step and a candidate are what this is about to make.
#
#  `STR(?takes)` because GROUP_CONCAT over an IRI binds NOTHING in this engine — no column at
#  all, measured — where the string form binds; the same trap `find_wants` reads a want's abouts
#  through. An action declaring no parameter yields the empty string, which is a legal answer:
#  it is filled with nothing and affords at most one row.
_ACTIONS = """SELECT ?action ?available (GROUP_CONCAT(DISTINCT STR(?takes); separator=" ") AS ?takes_) WHERE {
  ?action a orexis:Action ; orexis:available ?available .
  OPTIONAL { ?action orexis:takes ?takes }
} GROUP BY ?action ?available"""

#  The memo's key on the store. A constant, because two spellings would be two memos.
_MEMO = ("steps", "actions")


def find_steps(store, me: str,
               *, graphs=None, memo=None) -> list[Step]:
    """Every step this agent could take in one world, name-ordered.

    A FUNCTION OVER THE STORE. It was a collection holding one — `Steps(store).find_all(…)` —
    and the store was the only thing the instance held, so constructing one said nothing a
    parameter could not. Which store is the question's: a search asks its imaginarium what an
    imagined world affords and the present asks the belief base.

    IT ASKS THE STORE FOR ITS OWN TEMPLATES. They were a parameter — every caller handed
    `find_actions(…)` straight in and nothing else ever consumed the list — and the parameter
    existed because a repository may not ask another repository. With that rule gone there is
    nobody to hand them in for: the templates are public and the store has them, including an
    imaginarium, which copies every public graph when the ground is prepared.

    The rest is one criterion: `me`, whose world this is.

    **IT IS NOT NARROWED BY WHAT A WANT IS ABOUT.** Every action was handed a `VALUES` table of
    `(want, about)` pairs and joined itself to the want whose property it served — which is
    filtering to the goal's predicates, and *"filtering to the goal's predicates deletes every
    chain; closing backward through preconditions keeps the bid that makes the dose possible"*.
    A want states no property now, and nothing narrows the menu by what one is about.
    """
    found: list[Step] = []
    for action in _declared(store, memo):
        found += steps_of_action(store, action, me, graphs=graphs)
    #  Sorted because per-action order is no order.
    return sorted(found, key=lambda s: (s.action, s.for_agent or ""))


def _declared(store, memo=None) -> list[dict]:
    """Every action the loaded vocabulary declares, name-ordered so a menu built from it is
    stable — the row, not a model of it.

    REMEMBERED FOR AS LONG AS THE CALLER SAYS (#552, added for this exact symptom — the same
    text fetched per fork by callers none of which could have answered differently). What a
    package declares cannot change while a pass runs, and a search writes nothing to the
    belief base: a three-disk hanoi solve asks this eighteen times and queries twice. The memo
    belongs to the pass, which is what knows that; handed none, this simply asks.

    IT WAS `Actions` AND `Action`, a file each. Their whole content was this query, this memo
    and a three-field dataclass, and the only thing that ever consumed the list was the loop
    above — the action list is not wanted for itself, it is wanted for the texts.
    """
    return remember(memo, _MEMO, lambda: sorted(
        bindings(query(store, _ACTIONS, graphs_of(store, PUBLIC))), key=lambda r: r["action"]))


def steps_of_action(store, action: dict, me: str, *, graphs=None) -> list[Step]:
    """Every step this action affords in one world — zero, one or many.

    WHICH WORLD IS A CRITERION — `graphs`, the world asked about as the list of graphs
    the caller built for it, an instant and a place in one. A world is part of the QUESTION —
    *what could I do there* — and so is `me`, and so is which graph is the agent's own. It
    was a constructor's once, and the planner built one per node because the world is the
    thing that moves; now there is nothing to construct.

    ZERO IS ORDINARY and is the commonest answer: nine of the eleven actions a simulation
    agent loads afford it nothing, because their preconditions do not bind. MANY is ordinary
    too — a supplier with three valves affords `Serving` three times, one per valve, and
    choosing between them is the whole of what a plan does at that step.

    """
    #  A precondition carrying a token nobody binds REFUSES rather than reaching the engine as
    #  a free variable (#500), so what the runner offers is what a premise may read: `$me`, and
    #  nothing else. `$picks` was offered too — the graph an agent's own settings live in — and
    #  no action in this tree named it; it returns with the mechanism that writes picks.
    q = bind(action["available"], me=me)
    #  THE ROW IS WHAT THE PRECONDITION BOUND, held to what the action says it TAKES: one
    #  pair per declared parameter the select projected, sorted so identity is the binding
    #  and nothing downstream has to agree on an order. A projected variable the action
    #  does not declare is ignored, and a declared parameter the row left unbound is
    #  absent — an action with an OPTIONAL hop affords rows of two shapes, and both are
    #  honest.
    params = {local_of(p): p for p in (action.get("takes_") or "").split()}
    return [Step(action=action["action"],
                 binding=tuple(sorted((iri, r[local]) for local, iri in params.items()
                                      if r.get(local))),
                 for_agent=r.get("for_agent"))
            for r in bindings(query(store, q, graphs if graphs is not None else
                                                 #  THE PRESENT, where no world is handed in: what a rule
                                                 #  reads and what is expected, as this store holds them now.
                                                 graphs_of(store, *FORESEEN, at=clock.now())))]
