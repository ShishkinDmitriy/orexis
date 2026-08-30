"""The manifest: the mind's stores, held as graphs — the floor the layers meet at.

What a fact ASSERTS about its subject — is, may be, would like, doing — is its modality
(knowledge/domain/modality.md), and in code a modality is a class that owns its store:
`Beliefs`, `Desires`, `Intentions`, with the raw `Store` beneath them, the private-graph
naming in `graphs.py` and the kernel vocabulary in `ontology.py` that all of them spell
facts in.

This package is the family's first member: the modalities held as named RDF graphs in an
embedded store. It is a package in the one tree, NOT a capability — nothing grants it and
there is no `provides()` below, because a store decides nothing and a modality nobody may
write is not a modality (the-mind-is-not-a-package). What loads it is NEED: the layers
above — execution, progression, deliberation, still in `agent/` until #452 — depend on it,
and until #455 builds the pull, the kernel's own declared dependency carries it
(a-layer-is-a-package-and-need-loads-it). It imports `assembly` and nothing above itself:
no layer, no capability, held to that by tests/test_layering.py.

It contributes no knowledge either — the T-Box stays the kernel's `agent/ontology.ttl`,
whose terms are true of every agent; this package holds only their Python spelling — so
the manifest is this docstring, and an omission is a statement.
"""
