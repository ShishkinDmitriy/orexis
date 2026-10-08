"""`stance`: a figure the agent states of itself, read off its self graph, and the package's own
constant where it states none (knowledge/domain/kernel/stance.md).

A STANCE IS A BELIEF ABOUT ONESELF, NOT CONFIGURATION. How long the agent waits for a step to be
answered, how much a search or a revision may spend in a pass, how many of a sensor's cadences it
lets pass before it doubts the sensor, how far ahead it looks: each is a triple about the self in
the agent's self graph — `:rose_grower sensing:stuckAfter 3` — authored by its world beside
`:rose_grower a orexis:Self`, as a desire is. Each package declares the figures it reads in its own
ontology and asks for them here by the term; the kernel names none of them, and no package names
another's.

READ OF THE SELF GRAPH ALONE. The text asks `?me a orexis:Self ; $stance ?n` over the graphs of kind
`orexis:SelfGraph` and nothing else, so a figure stated of the agent anywhere else — a public world
graph, a graph of its desires, a peer's document — is not the agent's word about itself and is not
read. Not refused, either: the loader holds no vocabulary, so it cannot tell a stance from any other
fact a world states about an agent, and a world stating a figure of an agent may mean something by it.

ONE FIGURE OR THE DEFAULT. Where the self graph states the figure once and as a number, that number,
in the default's type; where it states none, the default — the package's constant, which is never a
second place the figure lives, only what holds where the agent said nothing; where it states several,
or one that is not a number, the default too, said in the log, since two answers are never picked
between. Remembered per pass where a memo is given.
"""

from __future__ import annotations

import logging

from agent.ontology import SELF_GRAPH, local_of
from agent.store import graphs_of, remember, rows

log = logging.getLogger("stance")

_STANCE_Q = "SELECT ?n WHERE { ?me a orexis:Self ; $stance ?n }"


def stance(store, term: str, default, memo=None):
    """The figure `term` the self states of itself in its self graph, in `default`'s type, or
    `default` where it states none, several, or one that is not a number."""
    def read():
        found = rows(store, _STANCE_Q, graphs_of(store, SELF_GRAPH), stance=term)
        if len(found) != 1:
            if found:
                log.warning("the self states %d figures for %s: the default, %s, holds", len(found), local_of(term), default)
            return default
        try:
            return type(default)(float(found[0]["n"]))
        except ValueError:
            log.warning("the self states %r for %s, which is no number: the default, %s, holds",
                        found[0]["n"], local_of(term), default)
            return default
    return remember(memo, ("stance", term), read)
