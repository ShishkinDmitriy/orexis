"""`scoping_actions`: the actions an agent holds, clustered into the scopes their effects
join, written to the store — the function that makes the scope partition data
(scoping-actions). After the call, the store says which predicates some one action or
derivation reads or writes together, and which scope each predicate and each action is in;
`derive_wants` clusters a desire's results by it and reads no action.

The partition is `relevance.scopes`' — computed from what the shipped rules actually do,
never read off namespaces, the derivations loaded joining predicates as the actions do — and
it is a function of the actions loaded, which do not change while the agent runs. So this runs
at boot, once, and whenever the actions are rebuilt; it used to run inside every derivation.
"""

from __future__ import annotations

import logging

from . import relevance
from .scopes import save_scopes

log = logging.getLogger("scoping_actions")


def scoping_actions(agent) -> None:
    """Cluster every action the store holds into scopes and write them, replacing what stood.

    An action is in the scope its reads and writes lie in — one by construction, since an
    action touching two would have joined them. An action stating no effect is in no scope, as
    it is on no menu; one whose effect cannot be read joins everything and is in the one scope
    that holds everything. A scope is named for the agent and its place in the partition,
    largest first, so the same actions write the same text."""
    actions = relevance.actions_of(agent.beliefs.query)
    parts = relevance.scopes(actions, relevance.rule_edges())
    scopes = []
    for n, part in enumerate(parts, 1):
        scope = f"{agent.me.uri}.scope.{n}"
        members = {action for action, (reads, writes) in actions.items()
                   if reads is relevance.ANYTHING or writes is relevance.ANYTHING
                   or any(str(p) in part for p in set(reads) | set(writes))}
        scopes.append((scope, set(part), members))
    save_scopes(agent.beliefs, agent.id, agent.me.uri, scopes)
    log.info("%s: %d action(s) in %d scope(s)", agent.id, len(actions), len(parts))
