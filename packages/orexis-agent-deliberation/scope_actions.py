"""`scope_actions`: the actions an agent holds, clustered into the scopes their effects
join, written to the store — the function that makes the scope partition data
(scope-actions). After the call, the store says which predicates some one action or
derivation reads or writes together, and which scope each predicate and each action is in;
`derive_wants` clusters a desire's results by it and reads no action.

The partition, `scopes` below, is computed from what the shipped rules actually do — never
read off namespaces, the derivations loaded joining predicates as the actions do — over the
edges `relevance` reads off an action, which the planner's closure reads too. It is a function
of the actions loaded, which do not change while the agent runs, so this runs at boot, once,
and whenever the actions are rebuilt; it used to run inside every derivation.
"""

from __future__ import annotations

import logging

from . import relevance
from .relevance import ANYTHING
from .scopes import save_scopes

log = logging.getLogger("scope_actions")


def scope_actions(agent) -> None:
    """Cluster every action the store holds into scopes and write them, replacing what stood.

    An action is in the scope its reads and writes lie in — one by construction, since an
    action touching two would have joined them. An action stating no effect is in no scope, as
    it is on no menu; one whose effect cannot be read joins everything and is in the one scope
    that holds everything. A scope is named for the agent and its place in the partition,
    largest first, so the same actions write the same text."""
    actions = relevance.actions_of(agent.beliefs.query)
    parts = scopes(actions, relevance.rule_edges())
    written = []
    for n, part in enumerate(parts, 1):
        scope = f"{agent.me.uri}.scope.{n}"
        members = {action for action, (reads, writes) in actions.items()
                   if reads is ANYTHING or writes is ANYTHING
                   or any(str(p) in part for p in set(reads) | set(writes))}
        written.append((scope, set(part), members))
    save_scopes(agent.beliefs, agent.id, agent.me.uri, written)
    log.info("%s: %d action(s) in %d scope(s)", agent.id, len(actions), len(parts))


def scopes(actions: dict[str, tuple], rules: tuple = ()) -> tuple[frozenset, ...]:
    """The SCOPES of a vocabulary: predicates joined wherever one action or one derivation
    reads or writes both, and separate where nothing does (#565).

    How far anything an agent does can reach. A hull's compartments are the picture — flooding
    one does not flood the next — and the sovereign ruled the word: a core concept outranks a
    niche one, so a commitment's token says what it `permits` and a want sits on the binding
    axis. Not "component", which is what this repo calls a package.

    Two wants in different scopes cannot contradict, because no action of one writes a fact
    the other reads — which is what makes it safe to plan them apart, one cone each, and to
    concatenate their plans. Independence is PROVEN this way and never read off namespaces: a
    greenhouse's water and climate words look like two vocabularies until a heater dries the
    soil, and two vans in one courier vocabulary look like one until you notice nothing they do
    touches the same van.

    Computed from relevance's own tables, so it says what the shipped rules actually do rather
    than what anyone declared. An action whose reads or writes are unreadable joins everything:
    a lever that might touch any predicate cannot be proven not to.

    **A scope here is a set of PREDICATES, and that is the limit worth naming.** Two vans are
    two scopes only over VARIABLES — a subject and a predicate together — and this sees
    predicates alone, so it separates a vocabulary and never two instances of one. Measured on
    every shipped world, it separates nothing at all: 90 predicates, one scope, whether the
    derivations are counted or the actions taken alone. That is the honest state of the claim,
    and it is why one cone per scope has nothing yet to split.
    """
    edges = list(actions.values()) + list(rules)
    known = {str(p) for reads, writes in edges
             for side in (reads, writes) if side is not ANYTHING for p in side}
    parent: dict = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(terms) -> None:
        terms = list(terms)
        for other in terms[1:]:
            a, b = find(terms[0]), find(other)
            if a != b:
                parent[a] = b

    for term in known:
        find(term)
    for reads, writes in edges:
        if reads is ANYTHING or writes is ANYTHING:
            join(known)          # unreadable: it might touch anything, so it joins everything
            continue
        join(str(p) for p in set(reads) | set(writes))
    out: dict = {}
    for term in known:
        out.setdefault(find(term), set()).add(term)
    return tuple(frozenset(v) for v in sorted(out.values(), key=lambda s: (-len(s), sorted(s))))


def spans(view, parts: tuple[frozenset, ...]) -> int:
    """How many scopes a view falls across — 1 where the want may be planned as one cone,
    more where its plan would be several concatenated. ANYTHING spans everything there is."""
    if view is ANYTHING:
        return len(parts)
    names = {str(p) for p in view}
    return sum(1 for part in parts if part & names)
