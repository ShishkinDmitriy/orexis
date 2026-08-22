"""The mind's second store: what this agent pursues, copied out of what it knows.

Part of [a-store-is-a-modality](../knowledge/decisions/a-store-is-a-modality.md), which rules
that a modality is a STORE and a graph says only who put the fact there. This file is the
first store after the belief base: **the desires store**, holding every graph whose content
is a want — the regions and envelopes deduced from what the world states, the obligations a
claim raised, and the picks, since the sovereign ruled that a pick is a want and
`ag:BeliefsGraph` is already typed `ag:DesireGraph` in the vocabulary.

**Rebuilt, never edited.** The store is a materialised view: a copy of the desire-modality
graphs, made at boot and made again whenever a re-derivation changes a premise
(`Agent.rebuild_desires`). Nothing writes INTO it — the handle the runtime holds is
`store.ReadOnly`, which has no update to call — so "recomputation is the only write path" is
a fact about the type rather than a discipline about the caller.

**Selected by asking, never by listing.** What makes a graph a desire graph is its CLASS —
`ag:DesireGraph` or `ag:ConstraintGraph`, asserted in the public catalog for the shared
graphs and in the classification graph for the agent's own — so a package that declares a
new desire-modality graph is copied without this file learning its name. The query runs with
the union default, because the question "what are this store's graphs" is a question about
the whole store, exactly as the sovereign's channel asks it.

The belief base remains the graphs' HOME today — genesis derives into it and a volume
persists it — and this store is the read surface deliberation is moving to. The rest of #298
is that move: the split queries #296 measured, and the pick record the rulings describe.
"""

from __future__ import annotations

import logging

from .ontology import AG
from .store import ReadOnly, Store, bindings

log = logging.getLogger("mind")

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
_DESIRE_MODALITIES_Q = f"""
SELECT DISTINCT ?g WHERE {{
  {{ ?g a <{AG}DesireGraph> }} UNION {{ ?g a <{AG}ConstraintGraph> }}
}}"""


def desire_graphs(source: Store) -> list[str]:
    """Every graph the catalog types with a desire modality, public or this agent's own."""
    return sorted(r["g"] for r in bindings(source.query_union(_DESIRE_MODALITIES_Q)))


class Desires(Store):
    """The desires store: a copy of the desire-modality graphs, alive until the next rebuild.

    A `Store` for the same reason the imaginarium is one: an ordinary query means the same
    thing here as anywhere, and a store constructed with no path is memory with nothing to
    clean up. What differs is the lifecycle — the imaginarium is dropped with a plan, this is
    replaced by a rebuild — and who may write, which for this store is nobody: the runtime is
    handed the read half only.
    """

    def __init__(self, source: Store):
        super().__init__()
        for iri in desire_graphs(source):
            for quad in source.quads(iri):
                self._store.add(quad)


class Mind:
    """The stores an agent's mind is made of — one per modality, as the record's table lands.

    Today it holds the first: `desires`, read-only, rebuilt from the belief base on demand.
    The menu, intentions and history stores join here as #299 moves them, so a module asks
    `agent.mind.<modality>` and never learns how a store is built or where it persists.
    """

    def __init__(self, source: Store):
        self._source = source
        self.desires: ReadOnly = ReadOnly(Desires(source))

    def rebuild_desires(self) -> None:
        """Recompute the desires store from its premises — the ONLY way it ever changes.

        Called after anything that moves a premise: a re-derivation, an endowment, a recorded
        re-pick. A fresh copy rather than an edit, so a want whose premise has ceased is
        absent afterwards without anyone having retracted it (#263's discipline, structural).
        """
        self.desires = ReadOnly(Desires(self._source))
