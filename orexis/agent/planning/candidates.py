"""What every action the store holds comes to in ONE world — the CANDIDATES it admits.

THE THIRD OF THREE FILES ABOUT AN ACTION, and the only one that asks which fillings there are.
`effects.py` beside it answers what one costs and when it lands; `apply_effects.py` runs its
effect into a world. This runs its `orexis:available` precondition against the world it is
handed and shapes each row into a `Candidate` — one pair per parameter the action declares it
takes, one candidate per action per legal filling.

Nothing is stored: what a world admits is a conclusion whose premises are stored and would
outlive them (a-situated-instance-is-kept-only-when-it-is-testimony).

**ONE PER ACTION PER LEGAL FILLING**, and the filling is the point: an action's
`orexis:available` is a SELECT projecting the parameters the action declares it takes, so its
ROWS are the candidates. It is not a filter the search applies to a list it already had — it is
where the list comes from, and where `$tank = tank1` comes from.

**A CANDIDATE IS NOT A STEP.** The search walks possible worlds, forking on a candidate at a
time, and when one meets the want the PICKED candidates become the plan's steps. So a step is
the search's RESULT and a candidate is its input, and they were one class until this — on the
argument that a picked one carries what the search added and an unpicked one carries `None`
there, which nothing in this tree ever filled.

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

from dataclasses import dataclass

from orexis.agent.store import bind, bindings, graphs_of, query, remember

from orexis.agent.ontology import FORESEEN, local_of
from orexis.agent import clock
from orexis.agent.ontology import PUBLIC

@dataclass(frozen=True)
class Candidate:
    """One action, filled in — what a world ADMITS, and what the search picks from.

    IT IS NOT A STEP, and the difference is the search. A candidate is a move that COULD be
    made in some world; a step is one a plan holds, and a plan holds only what was picked. The
    two were one class, on the argument that a picked one carries what the search added and an
    unpicked one carries `None` there — but nothing in this tree fills those fields, so the
    argument had no witness and the word did two jobs.

    A STEP IS THE SEARCH'S RESULT AND HAS NO PYTHON TYPE. `extract_plan` mints one RDF node
    per picked candidate — `execution:Step`, chained by `execution:then` — and that is what
    crosses to the ledger. Nothing reads a step back into Python here, so nothing needs a
    class for it.

    AND THIS ONE IS A TYPE FOR THE OPPOSITE REASON TO THE ONES THAT WENT. `Want`, `Plan` and
    `Step` were read OUT of the store into Python and then thrown away, which is the store
    duplicated for the length of an expression. A candidate is not in the store when it is
    made: a world admits many and the search takes one, and only the taken one is written —
    `<world>#by`, by `mark_world`, when the fork happens. So this is a value in flight between
    the two, and there is nowhere to read it from instead.
    """

    action: str                       # which template — `market:Acquiring`, `actuation:Dosing`
    #  WHAT IT IS FILLED WITH: one (parameter, value) pair per parameter the action declares
    #  it `orexis:takes`, sorted, and opaque to everything here. It is also the candidate's
    #  IDENTITY — two of one action are the same candidate when they are filled the same way.
    binding: tuple[tuple[str, str], ...] = ()

    #  TWO FIELDS, AND THE OTHERS WENT WHERE THE READERS ARE. `for_agent` — whom a move serves
    #  where it is an obligation's — was set from a `?for_agent` no shipped precondition
    #  projects, so it was always None and ordered nothing; `is_own` read it and `value_of`
    #  walked the binding, and neither was ever called. `execution:forAgent` is still the
    #  ledger's word for the same thing, waiting on a package that projects it.


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


def find_candidates(store, me: str,
               *, graphs=None, memo=None) -> list[Candidate]:
    """Every candidate this agent could take in one world, name-ordered.

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
    A want states no property now, and nothing narrows what is asked by what one is about.
    """
    found: list[Candidate] = []
    for action in _declared(store, memo):
        found += candidates_of_action(store, action, me, graphs=graphs)
    #  Sorted because per-action order is no order.
    return sorted(found, key=lambda c: (c.action, c.binding))


def _declared(store, memo=None) -> list[dict]:
    """Every action the loaded vocabulary declares, name-ordered so what is built from it is
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


def candidates_of_action(store, action: dict, me: str, *, graphs=None) -> list[Candidate]:
    """Every candidate this action admits in one world — zero, one or many.

    WHICH WORLD IS A CRITERION — `graphs`, the world asked about as the list of graphs
    the caller built for it, an instant and a place in one. A world is part of the QUESTION —
    *what could I do there* — and so is `me`, and so is which graph is the agent's own. It
    was a constructor's once, and the planner built one per node because the world is the
    thing that moves; now there is nothing to construct.

    ZERO IS ORDINARY and is the commonest answer: nine of the eleven actions a simulation
    agent loads are admitted by nothing, because their preconditions do not bind. MANY is
    ordinary too — a supplier with three valves admits `Serving` three times, one per
    valve, and choosing between them is the whole of what a plan does at that step.

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
    return [Candidate(action=action["action"],
                 binding=tuple(sorted((iri, r[local]) for local, iri in params.items()
                                      if r.get(local))))
            for r in bindings(query(store, q, graphs if graphs is not None else
                                                 #  THE PRESENT, where no world is handed in: what a rule
                                                 #  reads and what is expected, as this store holds them now.
                                                 graphs_of(store, *FORESEEN, at=clock.now())))]
