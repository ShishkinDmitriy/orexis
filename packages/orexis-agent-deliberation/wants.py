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
from orexis_agent_progression.ontology import OREXIS, WANT
from orexis_agent_progression.store import NAMESPACES, bindings

from .ontology import DELIBERATION, pursued_graph
from .want import Want
from orexis_agent_progression.ontology import RECORD

log = logging.getLogger("wants")

#  HOW MANY A `find_all_…` HANDS BACK unless the caller says otherwise. Every read is bounded,
#  because a collection whose size is the world's is one an author sizes by hoping: wants are
#  tens today — a few roots, a debt per claim in its window — and nothing enforces that, since
#  a market with a busy ledger mints one per claim and a stuck sweep leaves them standing.
#  Generous enough that no correct caller meets it, small enough that meeting it is survivable.
PAGE = 100


def _moment(value) -> str:
    """One instant as the store keeps it. A string is passed through: a caller that already
    has the literal has nothing to convert."""
    return value if isinstance(value, str) else value.isoformat()


def _instant(text: str | None) -> datetime | None:
    """One instant as a want carries it, or None where the store holds none."""
    return datetime.fromisoformat(text) if text else None


def graph_of(agent_id: str, uri: str) -> str:
    """The graph one DERIVED want lives in. Named for the want so a second episode of the same
    desire reuses it, and everything keyed by the want finds what it kept."""
    return f"{pursued_graph(agent_id)}/{uri.rsplit('#', 1)[-1]}"


def save_want(engine, agent_id: str, want: Want) -> None:
    """Write one derived want over the ENGINE: its graph, replaced whole, and the catalogue's
    account of that graph — its family, how it arrived, whose it is and the period it holds
    during — in one update, so a want and what is said about it land together or not at all.

    THE KNOWLEDGE STAYS IN THIS FILE, which is the point of it being here (#677): the derivation
    decides what a want IS — its name, its label, what it points at, when it must hold — and
    where a want is kept is this module's, whether the collection below or the derivation asks. The
    catalogue is found by its own row and every kind the vocabulary puts a pursued graph
    beneath is written from one `rdfs:subClassOf` step, the closure being materialised at
    genesis (one-graph-both-engines-read).
    """
    graph = graph_of(agent_id, want.uri)
    points = " ".join(f"<{want.uri}> <{p}> <{o}> ." for p, o in want.points)
    shape = "\n  ".join(want.shape)
    #  INSTANTS CROSS HERE AND NOWHERE ELSE. A want carries them as instants, because what
    #  reads them — the keeper placing a step, the container measuring the room left — works in
    #  instants; the store keeps them as `xsd:dateTime` literals. This is the boundary, so it
    #  is where the two forms meet, one line each way (`_moment` below, and `_instant` on read).
    timed = (f' ; orexis:holdsAt "{_moment(want.holds_at)}"^^xsd:dateTime'
             f' ; prov:generatedAtTime "{_moment(want.derived_at)}"^^xsd:dateTime'
             if want.holds_at is not None else "")
    about = "".join(f" ; orexis:about <{a}>" for a in want.about)
    #  WHICH WAY IT BROKE, where the met-test's block said so (`orexis:violationIs`).
    side = f" ; orexis:violationIs <{want.side}>" if want.side else ""
    period = f' ; orexis:start "{clock.now().isoformat()}"^^xsd:dateTime' + (
        f' ; orexis:end "{_moment(want.ends)}"^^xsd:dateTime' if want.ends else "")
    engine.update(f"""
DROP SILENT GRAPH <{graph}> ;
DELETE {{ GRAPH ?cat {{ <{graph}> ?p ?o . ?period ?pp ?po }} }}
WHERE  {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{graph}> ?p ?o .
          OPTIONAL {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }} }} ;
INSERT {{
  GRAPH <{graph}> {{
  <{want.holder}> orexis:holds <{want.uri}> .
  <{want.uri}> a orexis:Want{timed}{about}{side} ;
      prov:wasDerivedFrom <{want.desire}> ;
      rdfs:label {json.dumps(want.label)} .
  {points}
  {shape} }}
  GRAPH ?cat {{ <{graph}> a deliberation:PursuedGraph ; orexis:arrivedBy orexis:Recorded ;
      orexis:beliefsOf <{want.holder}> ;
      dcterms:temporal [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ deliberation:PursuedGraph rdfs:subClassOf ?kind }} }}""",
                  prefixes=NAMESPACES)


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

    def find_all_pursued(self, at: datetime | None = None, *,
                         limit: int = PAGE, offset: int = 0) -> list[Want]:
        """Every want the DERIVATION minted, whatever desire each came under.

        The family, not a criterion a caller could name: `deliberation:PursuedGraph` is this
        collection's own word for where it writes, and handing it out would be handing out the
        graph names this class exists to keep. What a caller is asking is *which of my wants did
        a desire reading unmet bring about* — as against a debt, which the ledger mints when a
        claim arrives, or a promise, which a level below raises.

        THE CONTAINER ASKED THIS AS A QUERY OF ITS OWN, keyed on the agent and on the parent
        being a desire, and every column it selected — the parent, the want, the instant, when it
        was derived — is a field of `Want`. A query about this collection's contents belongs to
        this collection, which is where `root_of` and the abouts went before it.
        """
        return self._select("?w a orexis:Want .", at, limit, offset,
                            family=DELIBERATION + "PursuedGraph")

    def find_all_by_desire(self, desire: str, at: datetime | None = None, *,
                           limit: int = PAGE, offset: int = 0) -> list[Want]:
        """Every want derived from one desire. Several, because a desire universal over a class
        decomposes per instance — which nothing mints yet, and is why `find_first_by_desire`
        below is not simply this with a `[0]`."""
        return self._select(
            f"?w a orexis:Want ; prov:wasDerivedFrom <{desire}> .", at, limit, offset)

    def find_first_by_desire(self, desire: str, at: datetime | None = None) -> Want | None:
        """The want standing under one desire now, or None — the derivation's question.

        SCOPED TO THE DERIVATION'S OWN FAMILY. While the ledger minted its own wants, in a
        family of its own, this had to say whose it asked for; one function mints every
        want now (#675) and the scope is simply the family every derived want is in. It asked
        the BINDING before, which named that difference in a property where the graph's
        classification already said it (#681).
        """
        found = self._select(
            f"?w a orexis:Want ; prov:wasDerivedFrom <{desire}> .", at, limit=1,
            family=DELIBERATION + "PursuedGraph")
        return found[0] if found else None

    def find_first_by_uri(self, uri: str, at: datetime | None = None) -> Want | None:
        return next(iter(self._select(
            f"BIND(<{uri}> AS ?w) ?w a orexis:Want .", at, limit=1)), None)

    # --- write --------------------------------------------------------------------------

    def save(self, agent_id: str, want: Want) -> None:
        """Write a DERIVED want, then say so.

        THE GRAPH IS THIS MODULE'S TO NAME, and so is what is said ABOUT it: one graph per
        want, classified as the family it belongs to and given the period it holds during
        (#645), so the door hides an ended one from every reader and one sweep drops it. A
        caller naming any of that would hold the knowledge this file exists to hold — and
        would have to remember all three, which is the shape of an omission nobody notices
        until a want outlives its window.

        THE WRITE ITSELF IS `save_want`, over the engine. The derivation is a function over
        the store and holds no collection, so where a want is kept had to be sayable without
        one; what this collection adds is what a collection adds — that a write announces
        itself. A caller writing through the module function announces nothing, and its
        callers refresh what they hold.
        """
        save_want(self._store.engine, agent_id, want)
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
        """The graph one DERIVED want lives in — `graph_of` above, which the derivation asks too."""
        return graph_of(agent_id, uri)

    def _select(self, where: str, at: datetime | None = None,
                limit: int = PAGE, offset: int = 0, family: str = "") -> list[Want]:
        """Read the graphs of wants holding at `at` — of one family where a finder names it —
        and hand back one ordered page.

        A WANT IS ITS GRAPH, so which family it belongs to and whether it still holds are
        questions about the graph — the classification its writer set and the period it set
        with it, never a property on the want — and a want lives in ONE graph, so the text
        asks both of the catalogue itself, by the kinds it names and the instant it stands at
        (a-reader-states-the-kinds-it-reads). No name, and no graph list handed in. It
        replaced a filter on `orexis:bindsWhen`, which named a kind where a graph class
        already said it (#681).

        **ORDERED BEFORE IT IS CUT, AND CAPPED BY DEFAULT.** SPARQL returns a
        result in whatever order the engine reached it, so a `LIMIT` over one is a pick by
        internal layout — the trap `beliefs.py` records, where a bare `LIMIT 1` read the PLANT
        for every pick until a load order changed. Ordering by the want's own name makes a page
        mean something, makes `offset` walk the collection rather than resample it, and makes
        `find_first_by_…` answer the same way twice.

        **A FULL PAGE IS SAID OUT LOUD.** Truncating in silence is the empty-result trap wearing
        a cap: the caller gets a plausible answer and no way to know it was cut. Whoever meets
        the bound either pages or has a leak, and either way someone should see it.
        """
        #  EVERY GRAPH A WANT MAY LIVE IN, where no family is named: the graphs of wants, and
        #  the records — the ledger writes its debts as wants into its own record.
        #  SAID IN THE TEXT, since a want lives in one graph: which kinds, by the catalogue's
        #  rows — every kind a graph is stands on its row — and which instant, by the period
        #  on the same row. The text is handed no default graph; it names what it reads.
        #
        #  AND WHOSE, where the store has been told: a reader that means its own gets its own,
        #  which is what `graphs_of` does for every read that goes through it and what this
        #  text had to say for itself once it named its own graphs. Rule 4 makes the two the
        #  same in a volume — one agent, one store — and they are not the same in a store
        #  built with a whole world in it, where the derivation derives under every holder's
        #  desires and this collection would otherwise hand back another agent's wants. A
        #  graph saying no owner is anyone's, and a store told nothing keeps every graph.
        now = (at or clock.now()).isoformat()
        kinds = " ".join(f"<{k}>" for k in ((family,) if family else (WANT, RECORD)))
        mine = (f'    OPTIONAL {{ ?g orexis:beliefsOf ?owner }}\n'
                f'    FILTER(!BOUND(?owner) || ?owner = <{self._store.agent_uri}>)'
                if self._store.agent_uri else "")
        rows = bindings(self._store.query(f"""
SELECT ?w ?desire ?label ?holdsAt ?since ?side (GROUP_CONCAT(STR(?about); separator=" ") AS ?abouts) WHERE {{
  GRAPH ?g {{
    {where}
    OPTIONAL {{ ?w prov:wasDerivedFrom ?desire }}
    OPTIONAL {{ ?w rdfs:label ?label }}
    OPTIONAL {{ ?w orexis:holdsAt ?holdsAt }}
    OPTIONAL {{ ?w prov:generatedAtTime ?since }}
    OPTIONAL {{ ?w orexis:about ?about }}
    OPTIONAL {{ ?w orexis:violationIs ?side }}
  }}
  GRAPH ?catalogue {{
    ?catalogue a orexis:CatalogueGraph .
    ?g a ?kind . VALUES ?kind {{ {kinds} }}
{mine}
    OPTIONAL {{ ?g dcterms:temporal ?period . OPTIONAL {{ ?period orexis:start ?start }} OPTIONAL {{ ?period orexis:end ?end }} }} }}
  FILTER(!BOUND(?start) || ?start <= "{now}"^^xsd:dateTime)
  FILTER(!BOUND(?end) || ?end > "{now}"^^xsd:dateTime)
}} GROUP BY ?w ?desire ?label ?holdsAt ?since ?side ORDER BY ?w LIMIT {int(limit)} OFFSET {int(offset)}""", ()))
        #  A PAGE OF ONE IS ALWAYS FULL: `find_first_by_x` asks for one, and one standing is
        #  the ordinary answer, not a leak.
        if limit > 1 and len(rows) == limit:
            log.warning("wants: a full page of %d at offset %d — page or there is a leak",
                        limit, offset)
        return [Want(uri=r["w"], desire=r.get("desire"),
                     label=r.get("label", ""), holds_at=_instant(r.get("holdsAt")),
                     derived_at=_instant(r.get("since")), side=r.get("side"),
                     #  ONE ROW PER WANT, however many things it is about: grouped, so a page
                     #  counts wants and not (want, about) pairs, and the abouts come back as one
                     #  space-joined string. `STR()` IS LOAD-BEARING: this engine's GROUP_CONCAT
                     #  over an IRI binds NOTHING — no error, no column, the page reads as about
                     #  nothing — and over its string it binds. Measured on a bare store, and
                     #  pinned by `test_wants.py`.
                     about=tuple(sorted(r["abouts"].split())) if r.get("abouts") else ())
                for r in rows]
