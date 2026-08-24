"""Running a desire's declared measure — the one place its SPARQL becomes a number.

A desire states its own measure (`ag:measuredBy`, a SELECT whose one binding is `?urgency` in
0..1), and this runs it the way `agent/effects.py` runs a rule's `sh:construct`: substitution
into the stored text, against whichever dataset the question is being asked ABOUT. The callers
ask about different worlds and nothing here distinguishes them — `desires_of` and the deducer
pass the belief base, the planner passes its imaginarium with `$sensed` naming the readings a
candidate's path reached. One measure, asked of whichever world is being judged, which is the
whole reason it is declared rather than compiled into four call sites that could drift.

**It runs on pyoxigraph, never rdflib, and the choice is deliberate.** The planner holds each
candidate world twice — a named graph in the imaginarium and a flat rdflib copy for pySHACL —
and the measure is asked of the first, because that is the engine every other stored query here
runs on. Asking rdflib would mean two SPARQL engines answering one question, which is the
disagreement one-graph-both-engines-read exists to prevent, one layer up.

See knowledge/decisions/a-desire-states-its-own-measure.md.
"""

from __future__ import annotations

import logging

from .store import bindings

log = logging.getLogger("measure")


def urgency_of(query, measure: str, *, subject: str | None, observed_property: str | None,
               sensed: str, beliefs: str, value: float | None = None) -> float | None:
    """One measure, evaluated: the urgency, or None where the text would not run.

    `query` is the dataset being judged — a belief base's or an imaginarium's. `$value` is the
    caller's number to judge where it holds one (the choir's urgency hook is asked about
    readings it has not written yet, and a predicted value is not in any world); substituted
    with `?reading` when the caller holds none, so the measure judges the live reading in
    `$sensed` — which is the planner's case, and the reason a candidate world scores by what
    its own effects predicted.

    None is for a measure that RAISED, and every caller treats it as 1.0 — a package's broken
    query must not take an agent down, and not knowing is maximal, as it is everywhere. An
    unbound `?urgency` cannot happen by unmeasured-ness alone: the measure's own COALESCE lands
    that case on 1.0, which is the explicitness the engine's silent-nothing arithmetic demands.
    """
    text = (measure
            .replace("$subject", f"<{subject}>" if subject else "<urn:nobody>")
            .replace("$property",
                     f"<{observed_property}>" if observed_property else "<urn:nothing>")
            .replace("$sensed", f"<{sensed}>")
            .replace("$beliefs", f"<{beliefs}>")
            .replace("$value", repr(float(value)) if value is not None else "?reading"))
    try:
        rows = bindings(query(text))
    except Exception as exc:      # a desire's measure is derived, but a bug in it is still a bug
        log.error("this desire's measure would not run: %s", exc)
        return None
    if not rows or rows[0].get("urgency") is None:
        return None
    return float(rows[0]["urgency"])
