"""The execution layer's own words (#529).

`execution:` for the intentions — what an intention is made of, and the one figure that governs
keeping. A term one layer reads and writes carries that layer's prefix, so a reader of any
query can tell which layer it speaks for; what EVERY layer writes in stays `orexis:` and lives
beside them, in `agent.ontology`.

THESE SAT IN THE SHARED FILE, and its `.ttl` beside it — which declared twenty-seven
`execution:` terms and not one `orexis:` one, so the file both layers imported for the kernel's
vocabulary was carrying only this layer's. The `LAYER_OF` table that decided which namespace a
name belonged to went with them: it had no reader, and `term()` consulted it for one call.
"""

from __future__ import annotations

import re

EXECUTION = "http://example.org/orexis/execution#"

#  A STEP AN INTENTION HAS COMMITTED TO, as a belief over its landing window: the graph's kind and
#  the two lengths of the window the executor states on the step, in seconds, since a rule cannot
#  measure the stretch between the plan's two instants.
COMMITTED_STEP_GRAPH = EXECUTION + "CommittedStepGraph"
LANDS_WITHIN_S = EXECUTION + "landsWithinS"
ANSWERED_WITHIN_S = EXECUTION + "answeredWithinS"

#  WHAT A STEP PREDICTS, as two graphs it names: the facts its world gains and the facts it loses,
#  each a graph of a kind no reader of the present is handed — stated, never asserted
#  (a-steps-prediction-is-two-graphs-it-names). Planning writes them beside the step when the plan is
#  extracted; the executor holds the world to them and a fictive step is written from them.
ADDS_GRAPH = EXECUTION + "AddsGraph"
RETRACTS_GRAPH = EXECUTION + "RetractsGraph"
ADDS = EXECUTION + "adds"
RETRACTS = EXECUTION + "retracts"

#  HOW LONG A COMMITMENT IS GIVEN before a fresh impulse to do the same thing is decided
#  again — the one figure of execution's that something outside it reads: a want
#  foreseen at an instant holds until that instant plus this, because the last step is placed
#  AT the instant and its verdict comes after.
PATIENCE_S = EXECUTION + "patienceS"

_GRAPH = "http://example.org/orexis/graph/"


def intentions_graph(agent_id: str) -> str:
    """What this agent is committed to, standing and resolved. Its own, and only its own.

    NOT public, and the absence is the design: an intention disclosed is strategy leaked. Apart
    from the picks graph on purpose — a pick has one value, held to `sh:maxCount 1`, while
    intentions accumulate a history: every resolved one stays, with its outcome and its reason,
    because intentions that forgot their resolutions could not answer the only question an operator
    brings to it, which is what this agent thought it was doing and why it stopped.
    """
    return _GRAPH + "intentions/" + agent_id


def committed_graph(agent_id: str, step: str) -> str:
    """The graph holding one committed step over its landing window — the agent's own, named for
    the step for eyes; a reader asks the catalogue for `execution:CommittedStepGraph` and the
    writer alone reads it back by this name, to close it and to forget it."""
    local = re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", step.rstrip("#/"))[-1])
    return f"{_GRAPH}committed/{agent_id}/{local}"
