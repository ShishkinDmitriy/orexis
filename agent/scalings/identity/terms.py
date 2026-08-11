"""The terms this package implements — the Python end of `ontology.ttl`.

One family, three members, one implemented — and the predicate that says what unit a sensor's
quantity is in, which is the half of calibration that is not scaling. Which member serves a
sensor is DERIVED at genesis by `rules.ru`; nothing here searches for it at runtime.

**This package owns a namespace**, and `term()` here builds into it. `ontology.ttl` declares the
same one and is the authority. See knowledge/decisions/a-package-owns-its-namespace.md.
"""

from __future__ import annotations

# Where this package's terms live. Held against `ontology.ttl` by `tests/test_layout.py`.
NS = "http://example.org/agora/scaling#"


def term(name: str) -> str:
    return NS + name


# The family. A member is what `scaling:curve` states and `scaling:scaledBy` derives.
SCALING = term("Scaling")

# The members. Identity is what runs today, because the firmware scales before it publishes;
# the other two are declared so that moving that work off the board (issue #26) is adding a
# directory rather than deciding what a calibration is.
IDENTITY = term("Identity")
LINEAR = term("Linear")
TWO_POINT = term("TwoPoint")
