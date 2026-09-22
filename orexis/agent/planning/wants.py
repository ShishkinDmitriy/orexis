"""The wants this agent holds — two functions over a store, and no collection.

**A function over the store is handed the engine's door and nothing else.** `Wants` was the
first repository in the DDD sense, and what it bought was that the GRAPH NAMES and the QUERY
TEXTS stopped being things its callers knew. That is still true here and costs no object: the
names and the text live in this module, a caller says which store to search and by what
criteria, and nothing is constructed, held, or invalidated. What the class added on top was
an instance per agent, assembled at boot, holding one attribute — the store it was handed.

**FIVE FINDERS WERE ONE QUESTION ASKED FIVE WAYS.** `find_all`, `find_all_pursued`,
`find_all_by_desire`, `find_first_by_desire` and `find_first_by_uri` ran one query with one
`where` clause swapped and one graph family named or not. Three of the five had no caller
outside their own test. The criteria are arguments now, said at the call site where a reader
can see them, and the only distinction that survives as a NAME is the one the answer's shape
makes: `find_wants` hands back a page, `find_want` hands back one or None.

**IT READS ITS OWN WRITES.** Reading through the desire modality's projection meant a want was
invisible between being written and the projection being rebuilt, so every writer had to
remember to rebuild before any reader looked. A want is there the moment it is written, and
one whose period has CLOSED is not there at all (#645) — the filter is in `_select`, because a
want IS its graph.

**THIS READS AND DOES NOT WRITE.** Writing a want is the derivation's, and lives where the
want is decided (`derive_wants`); whoever wrote says what changed. Where a want LIVES is
`derive_wants.graph_of`, asked of the module that writes it rather than re-exported here.

**Wants live in graphs of wants and in records, and this reads both.** The derivation's
children are one graph of wants each, `orexis:arrivedBy orexis:Derived`; a world's ratified
want is a graph of wants that is `orexis:Asserted`; the ledger's debts are in its record. Which
writer put a want there is the ARRIVAL axis and `derived=True` is the only caller that cares —
it was a graph CLASS of the derivation's own, which is arrival wearing content, and the cost
was that a read for the world's wants could not be written at all. The keeper's promises are
not found here, because it types a promise `orexis:Desire` alone.
"""

from __future__ import annotations

import logging
from datetime import datetime

from orexis.agent import clock
from orexis.agent.ontology import OREXIS, RECORD, WANT
from orexis.agent.store import bindings, query, remember

from .want import Want

log = logging.getLogger("wants")

#  HOW MANY A READ HANDS BACK unless the caller says otherwise. Every read is bounded,
#  because a collection whose size is the world's is one an author sizes by hoping: wants are
#  tens today — a few roots, a debt per claim in its window — and nothing enforces that, since
#  a market with a busy ledger mints one per claim and a stuck sweep leaves them standing.
#  Generous enough that no correct caller meets it, small enough that meeting it is survivable.
PAGE = 100

#  HOW THE DERIVATION'S WANTS ARRIVED, which `derived=True` narrows to. This was a graph CLASS
#  of its own once, under `orexis:WantGraph`, whose whole content was that the derivation
#  rather than a world put the rows there — the ARRIVAL axis wearing a content class, which the
#  kernel vocabulary forbids in its own words. A want is in a graph of wants whoever wrote it,
#  and which writer is `orexis:arrivedBy`.
DERIVED = OREXIS + "Derived"


def _instant(text: str | None) -> datetime | None:
    """One instant as a want carries it, or None where the store holds none."""
    return datetime.fromisoformat(text) if text else None


def find_wants(store, at: datetime | None = None, *, uri: str = "", desire: str = "",
               derived: bool = False, holder: str = "", limit: int = PAGE,
               offset: int = 0) -> list[Want]:
    """The wants `store` holds that stand at `at`, narrowed by whichever criteria are named.

    `uri` asks after one want by name, `desire` after those derived from one desire, and
    `derived` narrows to the family the derivation mints into — as against a debt, which the
    ledger mints when a claim arrives, or a promise, which a level below raises. Said at the
    call site rather than spelled into a method name, so a reader sees what is being asked.

    THE READ TAKES NO OWNER ORDINARILY, and that is not an oversight: one agent, one volume
    (rule 4), so the store IS the scope and a want in it is this agent's by construction. A
    store built with a WHOLE WORLD in it is the exception, and there `holder` is a criterion
    like any other — said at the call site, because the predecessor kept it on the store and a
    read that asks the store whose it is is a read that cannot be given a second answer.

    **A FULL PAGE IS SAID OUT LOUD.** Truncating in silence is the empty-result trap wearing a
    cap: the caller gets a plausible answer and no way to know it was cut. Whoever meets the
    bound either pages or has a leak, and either way someone should see it.
    """
    patterns = "?w a orexis:Want"
    if desire:
        patterns += f" ; prov:wasDerivedFrom <{desire}>"
    where = f"BIND(<{uri}> AS ?w) {patterns} ." if uri else f"{patterns} ."
    found = _select(store, where, at, limit, offset, DERIVED if derived else "", holder)
    #  A PAGE OF ONE IS ALWAYS FULL: `find_want` asks for one, and one standing is the
    #  ordinary answer, not a leak.
    if limit > 1 and len(found) == limit:
        log.warning("wants: a full page of %d at offset %d — page or there is a leak",
                    limit, offset)
    return found


def find_want(store, at: datetime | None = None, *, uri: str = "", desire: str = "",
              derived: bool = False, holder: str = "") -> Want | None:
    """The first want matching those criteria, or None — the same read, cut to one.

    Its own name because the SHAPE of the answer differs and a caller branches on it, not
    because the question does. `desire=…, derived=True` is the derivation's question: the want
    standing under one desire now. A desire universal over a class decomposes per instance, so
    `find_wants` with the same criteria may hand back several, which is why this is not simply
    that with a `[0]`.
    """
    return next(iter(find_wants(store, at, uri=uri, desire=desire,
                                derived=derived, holder=holder, limit=1)), None)


def _select(store, where: str, at: datetime | None, limit: int, offset: int,
            arrival: str, holder: str = "") -> list[Want]:
    """Read the graphs of wants holding at `at` — of one arrival where a caller names it — and
    hand back one ordered page.

    A WANT IS ITS GRAPH, so which family it belongs to and whether it still holds are
    questions about the graph — the classification its writer set and the period it set with
    it, never a property on the want — and a want lives in ONE graph, so the text asks both of
    the catalogue itself, by the kinds it names and the instant it stands at
    (a-reader-states-the-kinds-it-reads). No name, and no graph list handed in. It replaced a
    filter on `orexis:bindsWhen`, which named a kind where a graph class already said it (#681).

    **ORDERED BEFORE IT IS CUT.** SPARQL returns a result in whatever order the engine reached
    it, so a `LIMIT` over one is a pick by internal layout — the trap `beliefs.py` records,
    where a bare `LIMIT 1` read the PLANT for every pick until a load order changed. Ordering
    by the want's own name makes a page mean something, makes `offset` walk the collection
    rather than resample it, and makes `find_want` answer the same way twice.
    """
    #  EVERY GRAPH A WANT MAY LIVE IN, where no family is named: the graphs of wants, and
    #  the records — the ledger writes its debts as wants into its own record.
    #  SAID IN THE TEXT, since a want lives in one graph: which kinds, by the catalogue's
    #  rows — every kind a graph is stands on its row — and which instant, by the period
    #  on the same row. The text is handed no default graph; it names what it reads.
    #
    #  AND WHOSE, where the CALLER said so: a reader that means its own says whose, which
    #  is what `graphs_of(engine, …, holder=…)` takes for every read that goes through it.
    #  Rule 4 makes the two the same in a volume — one agent, one store — and they are not
    #  the same in a store built with a whole world in it, where the derivation derives under
    #  every holder's desires and this read would otherwise hand back another agent's wants.
    #  A graph saying no owner is anyone's, and a read told nothing keeps every graph.
    now = (at or clock.now()).isoformat()
    kinds = " ".join(f"<{k}>" for k in (WANT, RECORD))
    #  AND HOW IT ARRIVED, where the caller said: the derivation's wants are the graphs of
    #  wants it wrote, and a world's ratified want is a graph of wants the sovereign wrote.
    #  One axis each, asked separately, because they ARE separate.
    came = f"    ?g orexis:arrivedBy <{arrival}> .\n" if arrival else ""
    mine = (f'    OPTIONAL {{ ?g orexis:beliefsOf ?owner }}\n'
            f'    FILTER(!BOUND(?owner) || ?owner = <{holder}>)'
            if holder else "")
    rows = bindings(query(store, f"""
SELECT ?w ?desire ?label ?holdsAt ?since ?side WHERE {{
  GRAPH ?g {{
    {where}
    OPTIONAL {{ ?w prov:wasDerivedFrom ?desire }}
    OPTIONAL {{ ?w rdfs:label ?label }}
    OPTIONAL {{ ?w orexis:holdsAt ?holdsAt }}
    OPTIONAL {{ ?w prov:generatedAtTime ?since }}
    OPTIONAL {{ ?w orexis:violationIs ?side }}
  }}
  GRAPH ?catalogue {{
    ?catalogue a orexis:CatalogueGraph .
    ?g a ?kind . VALUES ?kind {{ {kinds} }}
{came}{mine}
    OPTIONAL {{ ?g dcterms:temporal ?period . OPTIONAL {{ ?period orexis:start ?start }} OPTIONAL {{ ?period orexis:end ?end }} }} }}
  FILTER(!BOUND(?start) || ?start <= "{now}"^^xsd:dateTime)
  FILTER(!BOUND(?end) || ?end > "{now}"^^xsd:dateTime)
}} ORDER BY ?w LIMIT {int(limit)} OFFSET {int(offset)}""", ()))
    return [Want(uri=r["w"], desire=r.get("desire"),
                 label=r.get("label", ""), holds_at=_instant(r.get("holdsAt")),
                 derived_at=_instant(r.get("since")), side=r.get("side"))
            for r in rows]


