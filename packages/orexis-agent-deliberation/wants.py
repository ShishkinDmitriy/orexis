"""The wants this agent holds, as a collection — the first repository in the DDD sense.

A **repository** here is a collection of domain objects, BACKED by a store and owning none.
What makes `Wants` a repository rather than a query helper is that the GRAPH NAMES and the
QUERY TEXTS stop being things its callers know. See
knowledge/decisions/a-repository-is-named-for-what-it-holds.md.

**It is handed a store and never learns which one.** Not an agent: an agent is the whole
mind, and a collection that reached into `agent.desires` to read and `agent.beliefs` to write
had a position on which modality answers what — which is the mind's business and not a
collection's. What it needs is somewhere to search, the identity of whoever holds the wants,
and the one identifier a process is legitimately handed (rule 1). Anything with the store
surface will do, which is why this class can be tested against a bare one.

**It reads its own writes, and that is what the narrowing bought.** Reading through the
desire modality's projection meant a want was invisible between being written and the
projection being rebuilt, so every writer had to remember to rebuild before any reader looked.
Now a want is there the moment it is written, and one whose period has CLOSED is not there at
all (#645) — the repository keeps that part of the door itself, in `_select`, because a want IS
its graph and this class is the one that names it.

**A write announces itself and re-derives nothing.** `on_saved` and `on_deleted` are lists
whoever assembles the agent appends to; the desire modality's projection is rebuilt there,
because deciding that a projection is now stale is the assembler's call and not a
collection's. A repository that rebuilt on its own initiative would be reaching up a layer to
do it.

**Wants live in three graph families and this owns one.** Deliberation's derived children are
`deliberation:PursuedGraph`, one graph per want; the ledger's debts and the keeper's promises
are their packages' and are read here but not written — and the keeper's are not yet read
either, because it types a promise `orexis:Desire` alone. What `save` writes is a derived want.
Widening that is the next step and is deliberately not taken here: a repository that wrote a
debt would have to know the ledger's words, which are the ledger's (#635).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH, PERIODS_GRAPH
from orexis_agent_progression.store import bindings

from .ontology import pursued_graph
from .want import Want

log = logging.getLogger("wants")

#  HOW MANY A `find_all_…` HANDS BACK unless the caller says otherwise. Every read is bounded,
#  because a collection whose size is the world's is one an author sizes by hoping: wants are
#  tens today — a few roots, a debt per claim in its window — and nothing enforces that, since
#  a market with a busy ledger mints one per claim and a stuck sweep leaves them standing.
#  Generous enough that no correct caller meets it, small enough that meeting it is survivable.
PAGE = 100


class Wants:
    """Every want this agent holds, however it came to be held."""

    def __init__(self, store):
        """A store, and nothing else.

        THE AGENT IS ANOTHER AGGREGATE ROOT and this collection has no business holding its
        identity. It held the holder's URI and the agent's local id, which made it a thing that
        knew what an Agent is; they are QUERY CRITERIA now, passed by whoever is asking, and
        which store this is at all is the agent's decision since the agent owns both the stores
        and the collections over them.

        The READS take no criterion, and that is not an oversight: one agent, one volume (rule
        4), so the store IS the scope and a want in it is this agent's by construction. Only the
        writes need one, because a graph is NAMED for whose it is.

        The two listener lists are not identity and stay: they are this collection's own
        contract — a write announces itself — and say nothing about who is asking.
        """
        self._store = store
        #  Announced, not acted on: whoever assembled this appends what a write invalidates.
        self.on_saved: list = []
        self.on_deleted: list = []

    # --- read ---------------------------------------------------------------------------

    def find_all(self, at: datetime | None = None, *,
                 limit: int = PAGE, offset: int = 0) -> list[Want]:
        """Every want this store holds, whichever family it belongs to — one page of them.

        TWO OF THE THREE, MEASURED RATHER THAN ASSUMED: deliberation's derived children and the
        ledger's debts are typed `orexis:Want` and are found; the keeper's promises are typed
        `orexis:Desire` alone (keeper.py:580) and are not. That is the gap `ower.owe` had before
        #676 closed it, still open on the other writer, and it is the next migration rather than
        something this query should widen to paper over — a collection that matched a promise by
        some other pattern would be keeping a second definition of what a want is.
        """
        return self._select("?w a orexis:Want .", at, limit, offset)

    def find_all_by_desire(self, desire: str, at: datetime | None = None, *,
                           limit: int = PAGE, offset: int = 0) -> list[Want]:
        """Every want derived from one desire. Several, because a desire universal over a class
        decomposes per instance — which nothing mints yet, and is why `find_first_by_desire`
        below is not simply this with a `[0]`."""
        return self._select(
            f"?w a orexis:Want ; prov:wasDerivedFrom <{desire}> .", at, limit, offset)

    def find_first_by_desire(self, desire: str, at: datetime | None = None) -> Want | None:
        """The want standing under one desire now, or None — the pursuit road's question.

        FILTERED TO THE BINDINGS A SEARCH IS HANDED (`orexis:AtEnd`, `orexis:At`), because a
        debt binds `orexis:Within` and is not what a desire derived: the ledger mints it on a
        claim arriving, and the two roads meet only at #675.
        """
        found = self._select(
            f"?w a orexis:Want ; prov:wasDerivedFrom <{desire}> ; orexis:bindsWhen ?b . "
            f"FILTER(?b IN (orexis:AtEnd, orexis:At))", at, limit=1)
        return found[0] if found else None

    def find_first_by_uri(self, uri: str, at: datetime | None = None) -> Want | None:
        return next(iter(self._select(
            f"BIND(<{uri}> AS ?w) ?w a orexis:Want .", at, limit=1)), None)

    # --- write --------------------------------------------------------------------------

    def save(self, agent_id: str, want: Want) -> None:
        """Write a DERIVED want, then say so.

        THE GRAPH IS THIS REPOSITORY'S TO NAME, and so is what is said ABOUT it: one graph per
        want, classified as the family it belongs to and given the period it holds during
        (#645), so the door hides an ended one from every reader and one sweep drops it. A
        caller naming any of that would hold the knowledge this class exists to hold — and
        would have to remember all three, which is the shape of an omission nobody notices
        until a want outlives its window.
        """
        graph = self.graph_of(agent_id, want.uri)
        points = " ".join(f"<{want.uri}> <{p}> <{o}> ." for p, o in want.points)
        timed = (f' ; orexis:holdsAt "{want.holds_at}"^^xsd:dateTime'
                 f' ; prov:generatedAtTime "{want.derived_at}"^^xsd:dateTime'
                 if want.holds_at is not None else "")
        about = f" ; orexis:about <{want.about}>" if want.about else ""
        ends = (f'\n      orexis:end "{want.ends}"^^xsd:dateTime ;' if want.ends else "")
        self._store.drop_graph(graph)
        self._store.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
  <{want.holder}> orexis:holds <{want.uri}> .
  <{want.uri}> a orexis:Want ; orexis:bindsWhen {want.binds}{timed}{about} ;
      prov:wasDerivedFrom <{want.desire}> ;
      rdfs:label {json.dumps(want.label)} .
  {points} }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{
    <{graph}> a deliberation:PursuedGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;{ends}
      orexis:start "{clock.now().isoformat()}"^^xsd:dateTime ] . }}
}}""")
        for listener in self.on_saved:
            listener(want)

    def delete_by_uri(self, agent_id: str, uri: str) -> None:
        """Forget one want. Its graph goes whole — a want IS its graph since #645, so there is
        nothing to leave behind and no second place to tidy."""
        self._store.drop_graph(self.graph_of(agent_id, uri))
        for listener in self.on_deleted:
            listener(uri)

    # --- where they live ------------------------------------------------------------------

    def graph_of(self, agent_id: str, uri: str) -> str:
        """The graph one DERIVED want lives in. Named for the want so a second episode of the
        same desire reuses it, and everything keyed by the want finds what it kept."""
        return f"{pursued_graph(agent_id)}/{uri.rsplit('#', 1)[-1]}"

    def _select(self, where: str, at: datetime | None = None,
                limit: int = PAGE, offset: int = 0) -> list[Want]:
        """Read every graph this store holds, keep the door THIS repository owns, and hand
        back one ordered page.

        The union rather than `query_at`, because that door resolves a graph's class through
        the vocabulary — so asking it would mean this collection could only be read out of a
        store with an ontology loaded, which is a whole world to stand up a query. The union
        needs nothing, and the part of the door that matters here is one filter: a graph whose
        period has ENDED is not handed out (#645), which is exactly the question
        `find_first_by_desire` is asking. A want IS its graph, so binding `?g` is what lets
        this class ask about the graph while its callers ask about the want.

        **ORDERED BEFORE IT IS CUT, and that is not decoration.** SPARQL leaves an unordered
        result in whatever order the engine reached it, so a `LIMIT` over one is a pick by
        internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the PLANT
        for every pick until a load order changed. Ordering by the want's own name makes a page
        mean something, makes `offset` walk the collection rather than resample it, and makes
        `find_first_by_…` answer the same way twice.

        **A FULL PAGE IS SAID OUT LOUD.** Truncating in silence is the empty-result trap wearing
        a cap: the caller gets a plausible answer and no way to know it was cut. Whoever meets
        the bound either pages or has a leak, and either way someone should see it.
        """
        now = (at or clock.now()).isoformat()
        rows = bindings(self._store.query_union(f"""
SELECT ?w ?desire ?binds ?label ?holdsAt ?since ?about WHERE {{
  GRAPH ?g {{
    {where}
    OPTIONAL {{ ?w prov:wasDerivedFrom ?desire }}
    OPTIONAL {{ ?w orexis:bindsWhen ?binds }}
    OPTIONAL {{ ?w rdfs:label ?label }}
    OPTIONAL {{ ?w orexis:holdsAt ?holdsAt }}
    OPTIONAL {{ ?w prov:generatedAtTime ?since }}
    OPTIONAL {{ ?w orexis:about ?about }}
  }}
  FILTER NOT EXISTS {{
    GRAPH <{PERIODS_GRAPH}> {{ ?g dcterms:temporal ?period . ?period orexis:end ?end }}
    FILTER(?end <= "{now}"^^xsd:dateTime) }}
}} ORDER BY ?w LIMIT {int(limit)} OFFSET {int(offset)}"""))
        if len(rows) == limit:
            log.warning("wants: a full page of %d at offset %d — page or there is a leak",
                        limit, offset)
        return [Want(uri=r["w"], desire=r.get("desire", ""), binds=r.get("binds", ""),
                     label=r.get("label", ""), holds_at=r.get("holdsAt"),
                     derived_at=r.get("since"), about=r.get("about")) for r in rows]
