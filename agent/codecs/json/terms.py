"""The terms this package implements — the Python end of `ontology.ttl`.

One family, three members, one of them implemented. Which member serves a sensor is DERIVED at
genesis by `rules.ru` and read back off the graph; nothing here searches for it at runtime.

**This package owns a namespace**, and `term()` here builds into it. `ontology.ttl` declares the
same one and is the authority — `agent.loader` reads it from there, which is how `codec:` reaches
a query. See knowledge/decisions/a-package-owns-its-namespace.md.
"""

from __future__ import annotations

# Where this package's terms live. Held against `ontology.ttl` by `tests/test_layout.py`.
NS = "http://example.org/agora/codec#"


def term(name: str) -> str:
    return NS + name


# The family. A member is what `codec:encoding` states and what `codec:decodedBy` derives.
ENCODING = term("Encoding")

# The members. Only the first has an implementation behind it; the other two are declared for
# the same reason `ag:Polling` and `ag:Consulting` are — the seam is worth naming before the
# second member exists, so building one is adding a directory rather than re-deciding a shape.
JSON = term("Json")
CBOR = term("Cbor")
KAITAI = term("Kaitai")
