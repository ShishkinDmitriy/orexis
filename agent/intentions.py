"""The intention modality: what this agent is DOING, in a store that survives it.

Part of a-store-is-a-modality's table — intentions persist in the volume, written by the
keeper, reset by nothing: a commitment must outlive a restart, which is the exact opposite of
a hypothesis and the reason the imaginarium is memory. A modality is a class that owns its
store, so what kind of store this is — and that it is writable, since keeping a ledger IS
writing — are decisions made here and invisible to the agent.

**Deployed, the store is its own room in the agent's volume** (`<state>/intentions`, beside
`<state>/belief-base`), so the ledger's persistence is the volume's and no other store's
compaction, rebirth or replacement can touch it. **A pathless mind has no rooms**: handed no
volume — every test agent — the modality keeps the ledger in the belief base's store, exactly
where pre-split volumes kept it, and the surface stays the boundary either way: the keeper
asks `agent.intentions`, whichever store answers.

`adopt` is the one-time migration a pre-split volume needs: a ledger written into the belief
base before intentions had a room of their own moves over on the first boot that has one, and
the move is idempotent — an empty own-store and a populated old graph is the only state that
triggers it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .store import Store

log = logging.getLogger("intentions")


class Intentions:
    """The intention modality: owns the ledger's store, and is writable — keeping is writing."""

    def __init__(self, state_path: str | None, beliefs):
        self._own = Store(str(Path(state_path) / "intentions")) if state_path else None
        backing = self._own if self._own is not None else beliefs
        self.query = backing.query
        self.query_union = backing.query_union
        self.update = backing.update
        self.quads = backing.quads
        if self._own is not None:
            self._adopt(beliefs)

    def _adopt(self, beliefs) -> None:
        """Move a pre-split volume's ledger into the modality's own room, once."""
        from packages.capability.intention.graphs import intentions_graph
        if len(self._own):
            return
        iri = intentions_graph(beliefs.agent_id)
        quads = list(beliefs.quads(iri))
        if not quads:
            return
        for quad in quads:
            self._own._store.add(quad)
        beliefs.clear_graph(iri)
        log.info("%s: adopted %d ledger quad(s) from the pre-split volume",
                 beliefs.agent_id, len(quads))

    def __len__(self) -> int:
        return len(self._own) if self._own is not None else 0
