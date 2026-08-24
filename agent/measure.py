"""Running a desire's declared measure — the one place its SPARQL becomes a number.

A desire's KIND declares how badly such a want is unmet: a capability ships `measures.ttl`
with a node carrying `ag:measureOf` — the class of thing the want is about — and `sh:select`,
the query whose one binding is `?urgency` in 0..1. This module resolves a want to its kind's
measure and runs it, the way `agent/effects.py` runs a rule's `sh:construct`: substitution
into the stored text, against whichever dataset the question is being asked ABOUT. The kernel
never knows any measure's content — the split the sovereign ruled: the core is BDI, the
derivation mints the want and its shape, and how badness is measured is planning-domain
machinery, a capability's contribution. Sensing declares the observation-backed one, because
the reading is sensing's whole subject.

The callers ask about different worlds and nothing here distinguishes them — `desires_of` and
the deducer pass the belief base, the planner passes its imaginarium with `$sensed` naming the
readings a candidate's path reached. One measure, asked of whichever world is being judged,
which is the whole reason it is declared rather than compiled into four call sites that could
drift.

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

#  The kind-level resolution: what the want is about, asked what it IS, joined to whatever the
#  loaded packages declare. Run against PUBLIC knowledge — the typing lives in the ontology
#  graphs and the declarations in the measures graph, both public — so an unqualified pattern
#  is exactly right here.
_FOR_PROPERTY_Q = """
SELECT ?measure WHERE {
  <%s> a ?kind .
  ?m ag:measureOf ?kind ; sh:select ?measure } LIMIT 1"""


def for_property(query, observed_property: str) -> str | None:
    """The measure declared for wants about this property's KIND, or None where no loaded
    package measures it.

    None is an answer every caller turns into urgency 1.0 — not knowing how bad is maximal,
    the same choice `urgency(None)` has always made — and the callers log it, because a want
    nothing measures is worth a line where a want nothing has read is routine.
    """
    rows = bindings(query(_FOR_PROPERTY_Q % observed_property))
    return rows[0]["measure"] if rows else None


def urgency_of(query, measure: str, *, me: str, subject: str | None,
               observed_property: str | None, sensed: str, beliefs: str,
               value: float | None = None, region=None) -> float | None:
    """One measure, evaluated: the urgency, or None where the text would not run.

    `query` is the dataset being judged — a belief base's or an imaginarium's. `$value` is the
    caller's number to judge where it holds one (the choir's urgency hook is asked about
    readings it has not written yet, and a predicted value is not in any world); substituted
    with `?reading` when the caller holds none, so the measure judges the live reading in
    `$sensed` — which is the planner's case, and the reason a candidate world scores by what
    its own effects predicted.

    `region` fills the numeric parameters a kind-level text cannot know — `$centre`,
    `$outerLow`, `$outerHigh` — read off the deduced shapes by the caller AT QUERY TIME, the
    same substitution discipline as `$litres` on an effect rule: nothing is baked anywhere, so
    a re-derivation that moves the bounds moves the next answer. Duck-typed on `Region`'s
    attributes rather than importing it, because regions imports this module.

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
            .replace("$value", repr(float(value)) if value is not None else "?reading")
            .replace("$me", f"<{me}>"))
    if region is not None:
        outer_low = region.floor if region.floor is not None else region.low
        outer_high = region.ceiling if region.ceiling is not None else region.high
        text = (text.replace("$centre", repr(float(region.centre)))
                    .replace("$outerLow", repr(float(outer_low)))
                    .replace("$outerHigh", repr(float(outer_high))))
    try:
        rows = bindings(query(text))
    except Exception as exc:    # a capability's measure is declared, but a bug in it is a bug
        log.error("this desire's measure would not run: %s", exc)
        return None
    if not rows or rows[0].get("urgency") is None:
        return None
    return float(rows[0]["urgency"])
