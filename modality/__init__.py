"""The mind's stores — the modalities every layer meets at.

What a fact ASSERTS about its subject — is, may be, would like, doing — is its modality
(knowledge/domain/modality.md), and in code a modality is a class that owns its store:
`Beliefs`, `Desires`, `Intentions`, with the raw `Store` beneath them, the graph naming in
`graphs.py` and the kernel vocabulary in `ontology.py` that all of them spell facts in.

This tree is the FLOOR of the layered kernel (a-layer-is-a-distribution): the layers above —
execution, progression, deliberation, still in `agent/` until #452 — mostly do not call each
other, they meet here. So this tree imports `assembly` and nothing above itself, held to that
by `lint-imports` and by its own dependency list, and it is a root distribution rather than a
package because a grant nobody can lack is not a grant (the-mind-is-not-a-package).
"""

__version__ = "0.1.0"
