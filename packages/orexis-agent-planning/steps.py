"""What one action comes to in ONE world — the steps it affords.

FUNCTIONS OVER A STORE, not a collection: given an [action](action.py) and what this agent holds, run
that action's own precondition against the world this collection was handed and shape each
binding into a `Step` — one pair per parameter the action declares it takes. Nothing is stored:
what a world admits is a conclusion whose premises are stored and would outlive them
(a-situated-instance-is-kept-only-when-it-is-testimony).

**A STEP IS AN ACTION PICKED FOR EXECUTION**, and what a world admits is what the search picks
FROM — one per action per legal filling. They are one class, because what a search adds when it
picks is absent on one nobody picked, and that is what `None` in those fields means. This
yielded an `Affordance` once, copied into a step by `Step.from_row` the moment anything wanted
to plan with it: two classes for one shape, and a second word doing no work the absent fields
were not already doing.

**THE WORLD IS ASKED ABOUT, NOT HELD.** Every question here names one — `at` and `world` — so
one of these serves as many worlds as the store has to be asked about, and the precondition
names no graph to get it (#666). Which readings a premise reads is the door's to say.

**IT ASKS FOR NOTHING.** What the agent holds and which actions are worth asking are handed in.
This knows how to fetch steps and nothing about what is worth fetching, which is the caller's —
the file this was carved out of held both, plus a question that belonged to the desire modality.
"""

from __future__ import annotations

from orexis_agent_execution.store import Raw, bind, bindings, graphs_of, query, remember

from orexis_agent_execution.act import Step
from orexis_agent_execution.ontology import FORESEEN, local_of
from orexis_agent_execution import clock
from orexis_agent_execution.ontology import PUBLIC

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


def find_steps(store, about_of: dict[str, tuple[str, ...]], me: str, picks: str,
               *, graphs=None, only=None, memo=None) -> list[Step]:
    """Every step this agent could take in one world, name-ordered.

    A FUNCTION OVER THE STORE. It was a collection holding one — `Steps(store).find_all(…)` —
    and the store was the only thing the instance held, so constructing one said nothing a
    parameter could not. Which store is the question's: a search asks its imaginarium what an
    imagined world affords and the present asks the belief base.

    IT ASKS THE STORE FOR ITS OWN TEMPLATES. They were a parameter — every caller handed
    `find_actions(…)` straight in and nothing else ever consumed the list — and the parameter
    existed because a repository may not ask another repository. With that rule gone there is
    nobody to hand them in for: the templates are public and the store has them, including an
    imaginarium, which copies every public graph at init.

    The rest are criteria, as they already were: `about_of` is what the agent holds and what
    each want is about, `me` and `picks` whose world this is.

    `only` is the set of actions worth asking at all — the search's RELEVANT set (#504), or
    None for every action. A precondition is a query per action per world, and an action
    that touches nothing the want reads was already never simulated; skipped here it is
    never asked either, so a vocabulary that grows by unrelated domains costs a pass nothing.
    """
    found: list[Step] = []
    for action in _declared(store, memo):
        if only is not None and action["action"] not in only:
            continue
        found += steps_of_action(store, action, about_of, me, picks, graphs=graphs)
    #  Sorted because per-action order is no order.
    return sorted(found, key=lambda s: (s.want or "", s.action, s.for_agent or ""))


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


def steps_of_action(store, action: dict, about_of: dict[str, tuple[str, ...]],
                    me: str, picks: str, *, graphs=None) -> list[Step]:
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
    q = bind(action["available"], me=me, wants=Raw(wants), picks=picks)
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
                 want=r.get("want"), for_agent=r.get("for_agent"))
            for r in bindings(query(store, q, graphs if graphs is not None else
                                                 #  THE PRESENT, where no world is handed in: what a rule
                                                 #  reads and what is expected, as this store holds them now.
                                                 graphs_of(store, *FORESEEN, at=clock.now())))]
