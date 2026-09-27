"""Everything execution reports of how it is doing — its gauges and its events — and nowhere else.

Instrumentation, not model (`agent/metrics.py`). Adding a figure is editing this module.

THE GAUGES ARE OVER THE INTENTIONS STORE, the one the executor owns and alone writes. A resolved
intention stays with its outcome, so these are totals since the store was made — which, where the
runtime makes it, is the process's start (#842).

THE EVENT is the executor's, at the verdict on a step: how late the world answered it. Whether it
landed is history's; this is the lateness.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.metrics import Event, Gauge, sample
from agent.ontology import local_of
from agent.store import rows

#  THE INTENTIONS: standing, and how each resolved one ended. `failed` is the one to watch — the
#  world did not answer a step within the patience, or a step kept below could not be kept.
#
#  AN OUTCOME IS COALESCED BEFORE IT IS COMPARED. A standing intention has none, and `?outcome =
#  "failed"` over an unbound outcome is an error that left the whole column unbound — no `failed`
#  at all while one intention stood — measured on the greenhouse's first pass, 2026-09-27.
INTENTIONS = Gauge("intentions", """
SELECT (SUM(IF(BOUND(?resolved), 0, 1)) AS ?standing)
       (SUM(IF(COALESCE(?outcome, "") = "done", 1, 0)) AS ?done)
       (SUM(IF(COALESCE(?outcome, "") = "failed", 1, 0)) AS ?failed)
       (SUM(IF(COALESCE(?outcome, "") = "superseded", 1, 0)) AS ?superseded)
       (SUM(IF(COALESCE(?outcome, "") = "abandoned", 1, 0)) AS ?abandoned)
WHERE { GRAPH ?g { ?i a execution:Intention .
                   OPTIONAL { ?i execution:resolvedAt ?resolved }
                   OPTIONAL { ?i execution:outcome ?outcome } } }""")

#  THE ACTS: steps taken, and steps whose taking raised (knowledge/domain/execution/act.md).
ACTS = Gauge("acts", """
SELECT (SUM(IF(?taken, 1, 0)) AS ?taken) (SUM(IF(?taken, 0, 1)) AS ?notTaken)
WHERE { GRAPH ?g { ?act a execution:Act ; execution:taken ?taken } }""")

#  A VERDICT ON A STEP: how late the world answered it in the agent's seconds — the instant it was
#  seen to, less the `landsAt` the plan placed — and whether the patience ran out, tagged by the
#  action and the desire.
LANDING = Event("landing", values=("late_s",), flags=("timed_out",), tags=("action", "desire"))


def gauges(intentions: ox.Store) -> list:
    """Execution's gauges, sampled over the intentions store."""
    return sample(__name__, [intentions])


#  WHAT A PURSUED THING WAS DERIVED FROM, in PROV's words — read off the store a plan came from, for
#  the metrics alone, and in no word of the layer above.
_DERIVED_FROM_Q = """SELECT ?d WHERE { GRAPH ?g { $want prov:wasDerivedFrom ?d } } LIMIT 1"""


def derived_from(source: ox.Store, want: str) -> str | None:
    """The local name of what `want` was derived from in `source`, the store its plan came from — the
    desire, where a derivation minted it — or None."""
    found = rows(source, _DERIVED_FROM_Q, (), want=want)
    return local_of(found[0]["d"]) if found else None
