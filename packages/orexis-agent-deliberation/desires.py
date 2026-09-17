"""Every desire this agent holds, as a collection — and the modality whose store holds them.

`Desires` is BOTH, and they sit together because the store it owns IS the collection: a
projection holding the roots and the records, rebuilt whenever a premise moves. `Wants` is
handed a store because it WRITES, and its writes stale this projection; nothing writes a
declared desire at runtime — they are authored at genesis and projected, never rebuilt (#644) —
so this half reads and offers no `save`.

The model is `desire.py` beside this file, which is the file naming this package keeps: a
singular file holds what a thing is, its plural holds where they are kept. See
knowledge/decisions/a-repository-is-named-for-what-it-holds.md.
"""

from __future__ import annotations

from .desire import Desire

#  --- the desire modality ---------------------------------------------------------------------
#
#  In this file and not one of its own, because the two things here are one subject: the
#  desire is the kernel's shape for a want, and the desire modality is where an agent's wants
#  live — a class per modality, each owning a store the agent never sees, per
#  a-store-is-a-modality. The agent holds the MODALITIES and nothing holds the collection, by
#  the sovereign's ruling: nothing ever addresses it — `orexis-ask` names a modality and a
#  module asks for the one it means — and a holder no question needs is a namespace, not a
#  concept.

import logging

from assembly import loader
from orexis_agent_progression.ontology import DESIRE_ASSERTED_GRAPH
from orexis_agent_progression.store import Store, bindings

log = logging.getLogger("desires")

#  HOW MANY A `find_all` HANDS BACK unless the caller says otherwise — `Wants.PAGE`'s reason,
#  and the same number: a collection whose size is the world's is one an author sizes by hoping.
PAGE = 100

#  The two modality classes whose instances are wants. ConstraintGraph is a want's boundary
#  rather than a want — but gap, menu and validation all read the two together, and the record
#  files both under the desires store because what MAY be and what is PURSUED are the two
#  halves of one question no belief answers.
class Projection(Store):
    """One rebuild's worth of store: the roots and the records PROJECTED, and nothing else left
    standing — nothing deduced (#644). Memory, no path — the imaginarium's construction, one
    lifecycle over. `Deducer` until the roots were seen to be re-derived from a pick.

    Two moves. Every public graph and every record a want lives in is copied in — the roots
    graph genesis authored, the pick record, the obligations, the promises, the pursued
    children — reached by the one construction from an agent's own id the rules allow. Then
    the public premises that are NOT desire content are dropped, since a store answering
    "what do I want" must not answer with the topology beside it — leaving the roots, the
    world's asserted wants (`graph/desire/asserted`, a public graph a world's TriG may fill)
    and the records.
    """

    def __init__(self, beliefs):
        from orexis_agent_progression.ontology import obligations_graph, promises_graph, roots_graph
        from .ontology import pursued_graph

        super().__init__()
        publics = list(beliefs.public_graphs())
        #  A PROJECTION, AND NO RULE (#644, a-root-holds-always-and-an-outdated-graph-is-dropped):
        #  the roots — every Always desire, authored at genesis into the agent's own roots graph
        #  and holding at every instant — and the records sourced at a time: the picks, the
        #  debts, the promises, the wants pursued under a root (#618). The packages' desire
        #  rules ran here on every rebuild until a root was seen to be re-derived from a pick;
        #  they run at genesis now, and this build deduces nothing.
        #  A DEBT AND A PURSUED CHILD ARE GRAPHS OF THEIR OWN, holding during their periods
        #  (#645): every one the door hands at this instant is projected, under the untimed
        #  record it sits beneath, so a lapsed debt and a child past its instant are absent
        #  from this store as they are from every reader.
        timed = [g for g in beliefs.recorded_graphs()
                 if g.startswith(obligations_graph(beliefs.agent_id) + "/")
                 or g.startswith(pursued_graph(beliefs.agent_id) + "/")]
        records = [roots_graph(beliefs.agent_id), beliefs.graph, obligations_graph(beliefs.agent_id),
                   promises_graph(beliefs.agent_id), pursued_graph(beliefs.agent_id), *timed]
        for iri in publics + records:
            for quad in beliefs.quads(iri):
                self._store.add(quad)
        for iri in publics:
            if iri != DESIRE_ASSERTED_GRAPH:
                self.clear_graph(iri)


class Desires:
    """The desire modality: what this agent pursues, owning a store the agent never sees.

    A modality is a class that owns its store, and its store's nature is ITS decision
    (a-store-is-a-modality). This one's choices: in memory, DERIVED and never edited —
    `rebuild()` re-runs the want-derivation wholesale, so a want whose premise has ceased is
    absent afterwards because the derivation no longer implies it (#263's discipline, live) —
    and READ-ONLY on the surface: the class exposes queries and no writer, so a write attempt
    fails at the call site, whatever the store underneath could do.

    Since #312 there is no copy and no selection: genesis derives no wants, the belief base
    holds no desire-modality graphs, and this build is the one place the regions, envelopes,
    freshness wants and asserted root desires come to exist — from the world, the records,
    and the packages' `desires.ru`. The pick record and the obligations record are projected in
    beside them, because the picks ARE wants by the sovereign's ruling and an obligation is this
    agent's debts record, served as the wants they raise.
    """

    def __init__(self, beliefs):
        self._beliefs = beliefs
        self.rebuild()

    def rebuild(self) -> None:
        """Re-derive the store from its premises — the ONLY way this modality ever changes.

        Called after anything that moves a premise: an obligation transition, a recorded
        re-pick, an endowment. A fresh store rather than an edit; the read surface is
        rebound, so every holder of `agent.desires` sees the new state and nobody holds a
        stale handle.
        """
        built = Projection(self._beliefs)
        self.query = built.query
        self.query_union = built.query_union
        self.construct = built.construct
        self.quads = built.quads

    def read(self, picks):
        """Fill one capability's picks FROM THE DESIRE MODALITY — where they belong,
        because a pick is a want (#297's sort, knowledge/domain/pick.md). Served from
        this store's rebuilt copy, so a re-pick reaches a module the moment the rebuild runs
        and never before: the record is the belief base's, the read surface is this one."""
        from .beliefs import read_picks
        return read_picks(self.query_union, self._beliefs.agent_uri, self._beliefs.graph,
                          self._beliefs.agent_id, picks)

    def read_optional(self, picks):
        """The picks, or None where the agent said nothing at all — `Beliefs.read_optional`'s
        contract, served from this modality's copy."""
        from .beliefs import read_picks_optional
        return read_picks_optional(self.query_union, self._beliefs.agent_uri,
                                   self._beliefs.graph, self._beliefs.agent_id, picks)

    # --- the collection ---------------------------------------------------------------------
    #
    #  `Desires` is a repository as well as a modality, and the two sit together because the
    #  store it owns IS the collection: a projection holding the roots and the records, rebuilt
    #  whenever a premise moves (a-repository-is-named-for-what-it-holds). `Wants` is handed a
    #  store because it WRITES and its writes stale this projection; nothing writes a declared
    #  desire at runtime — they are authored at genesis and projected, never rebuilt (#644) —
    #  so this half reads and offers no `save`.

    def find_all(self, *, limit: int = PAGE, offset: int = 0) -> list[Desire]:
        """Every declared desire this agent holds — `orexis:Always`, the standing rules.

        NOT the wants derived under them, which are `Wants`'. A want is an `orexis:Desire` too,
        by the subclass axis, so the binding is what separates the two roads and it is asked
        for here rather than left to a caller to remember.
        """
        return self._desires("?d orexis:bindsWhen orexis:Always .", limit, offset)

    def find_first_by_uri(self, uri: str) -> Desire | None:
        """One desire by name, declared or derived — the binding on what comes back says which."""
        return next(iter(self._desires(f"BIND(<{uri}> AS ?d) ?d a orexis:Desire .", 1, 0)), None)

    def find_first_by_want(self, want: str) -> Desire | None:
        """The desire `want` was derived under, or None where it was derived from no desire.

        THE QUESTION BELONGS HERE because the ANSWER is a desire. It was asked of `Wants` —
        find the want by its uri, then read the name it kept — which walks through one
        collection to reach an element of another, and hands back a field rather than a thing.
        A want's provenance is the want's; what stands at the end of it is this collection's.
        """
        rows = bindings(self.query_union(
            f"SELECT ?d WHERE {{ <{want}> prov:wasDerivedFrom ?d . ?d a orexis:Desire }} LIMIT 1"))
        return self.find_first_by_uri(rows[0]["d"]) if rows else None

    def _desires(self, where: str, limit: int, offset: int) -> list[Desire]:
        """Ordered before it is cut, and capped by default — the convention's two clauses. An
        unordered `LIMIT` picks by the engine's internal layout, which is the trap `beliefs.py`
        records, and a silent truncation is the empty-result trap wearing a cap."""
        rows = bindings(self.query_union(f"""
SELECT ?d ?binds ?label ?about WHERE {{
  {where}
  OPTIONAL {{ ?d orexis:bindsWhen ?binds }}
  OPTIONAL {{ ?d rdfs:label ?label }}
  OPTIONAL {{ ?d orexis:about ?about }}
}} ORDER BY ?d LIMIT {int(limit)} OFFSET {int(offset)}"""))
        if len(rows) == limit and limit != 1:
            log.warning("desires: a full page of %d at offset %d — page or there is a leak",
                        limit, offset)
        return [Desire(uri=r["d"], binds=r.get("binds", ""), label=r.get("label", ""),
                       about=r.get("about")) for r in rows]
