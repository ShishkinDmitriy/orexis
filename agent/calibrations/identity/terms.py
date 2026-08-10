"""The terms this package implements — the Python end of `ontology.ttl`.

One family, three members, one implemented — and the predicate that says what unit a sensor's
quantity is in, which is the half of calibration that is not scaling.

**This package owns a namespace**, and `term()` here builds into it. `ontology.ttl` declares the
same one and is the authority. See knowledge/decisions/a-package-owns-its-namespace.md.
"""

from __future__ import annotations

# Where this package's terms live. Held against `ontology.ttl` by `tests/test_layout.py`.
NS = "http://example.org/agora/calibration#"


def term(name: str) -> str:
    return NS + name


# The family, and the predicate a sensor states to choose a member. Absent means the default.
CALIBRATION = term("Calibration")
CALIBRATED_BY = term("calibratedBy")

# What unit the quantity coming out of that calibration is in. The object is a QUDT unit IRI —
# borrowed, not imported: see the ontology.
QUANTITY_UNIT = term("quantityUnit")

# The members. Identity is what runs today, because the firmware scales before it publishes;
# the other two are declared so that moving that work off the board (issue #26) is adding a
# directory rather than deciding what a calibration is.
IDENTITY = term("Identity")
LINEAR = term("Linear")
TWO_POINT = term("TwoPoint")
