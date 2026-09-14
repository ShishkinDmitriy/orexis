"""An agent's own belief base — an embedded quad store, private by construction.

There is no shared triplestore. Each agent holds one store containing the world as of the
version it booted with, the vocabulary, its own beliefs and its own readings. Nothing else can
reach it: it is a file inside that agent's container, not a service on a network.

That is the whole of the isolation. Before this, privacy was *enforced* — per-agent credentials
and a per-graph access registry over one shared server — and the enforcement had to be
configured, generated and reloaded, which meant a restart every time a principal was added, and
made twenty worlds depend on one process. Now an agent's store contains only what it may see,
so there is nothing left to enforce. See knowledge/decisions/where-the-belief-base-lives.md.

Two kinds of knowledge live here, and their lifetimes differ:

- **public** — the T-Box and the world. Not the agent's to keep: replaced from the ratified
  files on every start, so an agent that restarts picks up an amended world.
- **private** — its beliefs, and what it has sensed. Written at birth, and the agent's
  thereafter. Start and stop must never touch them.
"""

from __future__ import annotations

import io
import re
import json
from datetime import datetime, timezone
from . import clock
from pathlib import Path
from typing import Callable

import pyoxigraph as ox

from assembly import loader
from .ontology import OREXIS, CLASSIFICATION_GRAPH, ONTOLOGY_GRAPH, PUBLIC_GRAPH, PERIODS_GRAPH

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against,
# unchanged from when this was an HTTP client, so nothing above here knows the difference.
QueryFn = Callable[[str], dict]

# Which graphs are public — ASKED, not listed. A graph IRI is an instance, and code that named
# five of them was doing what rule 1 forbids everywhere else; `orexis:PublicGraph` is the term, the
# instances are declared in the kernel's `agent/ontology.ttl`, and adding one is a vocabulary edit
# that touches no Python.
#
# `rdfs:subClassOf*` rather than a bare type, because this runs BEFORE the closure — it is what
# tells the loader where to put the closure. The one graph named here is the bootstrap root: the
# T-Box has to be loaded somewhere before it can be asked anything, exactly as an agent is handed
# its own id before it can discover anything else.
_DISCOVER = f"""
SELECT ?g WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{
  ?g a ?class . ?class rdfs:subClassOf* <{PUBLIC_GRAPH}> .
}} }}"""

#  THE AGENT'S OWN GRAPHS — what a plan must carry into its imaginarium and a validation must
#  read beside the state. Two sources, because a graph is classified wherever it can be: a
#  package declares its own in its ontology (sensing's instruments graph, and the kernel does
#  not know its name), while a PER-AGENT graph cannot be declared in a T-Box at all — it does
#  not exist until its agent does — so the agent types its own at boot into the classification
#  graph (genesis.classify_own_graphs).
#
#  BOTH of those are named here, and both are the bootstrap root rather than a reader
#  enumerating: they are where a graph says what it IS, and there is nowhere else to ask.
#
#  What is EXCLUDED and why, because each was a real answer this query gave before:
#    public       — the world declares every agent's belief graph by name, so city's store can
#                   see that `beliefs/fern` exists. A name is not content, but carrying it
#                   would be carrying somebody else's;
#    possible     — the deliberation trace is a record of a pass, not a fact about the world,
#                   and a hypothesis has no place in a hypothesis;
#    another store's — the intention ledger is classified here and held elsewhere, so the
#                   result is intersected with what this store actually has.
_OWN = f"""
SELECT DISTINCT ?g WHERE {{
  {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ ?g a ?class }} }}
  UNION
  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?g a ?class ; orexis:arrivedBy ?arrival }} }}
  ?class rdfs:subClassOf* orexis:Graph .
  #  ASKED OF THE GRAPH AND NOT OF THE CLASS THAT MATCHED: `graph/classification` is typed
  #  both public and belief, so a filter on one binding lets it through on the other. Both
  #  run in the DEFAULT graph, which `query` unions from the public ones — inside a GRAPH
  #  block pyoxigraph evaluates the NOT EXISTS before the UNION binds `?g`, and every row
  #  is dropped.
  FILTER NOT EXISTS {{ ?g a ?any . ?any rdfs:subClassOf* <{PUBLIC_GRAPH}> }}
  FILTER NOT EXISTS {{ ?g a ?hyp . ?hyp rdfs:subClassOf* orexis:PossibleGraph }}
  #  A WORKING GRAPH is the agent's and not carried (#448): a reviewer's scratch, a summary, a
  #  record of decisions — classified so a volume knows it from litter, left out of what a
  #  plan imagines from and a validation reads beside the state. A filter of its own, and
  #  not a VALUES over both classes inside one: measured at 600 ms against 2 ms for the two
  #  filters — the engine evaluates a VALUES-bound path end for every candidate rather than
  #  once, and this query runs at the start of every pass.
  FILTER NOT EXISTS {{ ?g a ?work . ?work rdfs:subClassOf* orexis:WorkingGraph }}
  #  A PREDICTION is a kind of its own (#642): what a package expects a reading to be during a
  #  window, handed by `query_at` at the instant asked about and never a record of the agent's.
  FILTER NOT EXISTS {{ ?g a ?guess . ?guess rdfs:subClassOf* orexis:PredictionGraph }}
}}"""

#  THE PREDICTIONS — every graph the classification types as a prediction, holding or not; the
#  door filters by period like every other list here.
_PREDICTIONS = f"""
SELECT DISTINCT ?g WHERE {{
  GRAPH <{CLASSIFICATION_GRAPH}> {{ ?g a ?class }}
  ?class rdfs:subClassOf* orexis:PredictionGraph }}"""

#  THE PERIOD EACH GRAPH HOLDS DURING — read from the one place that says so, which is named here
#  for the same reason the two above are: this is the bootstrap root asking what to merge, not a
#  reader narrowing itself to a graph instance. Absent bounds mean always, which is what every
#  graph meant before the term existed.
_PERIODS = f"""
SELECT ?g ?start ?end WHERE {{ GRAPH <{PERIODS_GRAPH}> {{
  ?g dcterms:temporal ?period .
  OPTIONAL {{ ?period orexis:start ?start }}
  OPTIONAL {{ ?period orexis:end ?end }}
}} }}"""


# Sent with every query. This is the ONLY set a query may use — some engines silently pre-bind
# common prefixes and others do not, so relying on that works in one and fails in another.
# `test_store.py` holds the codebase to this list.
#
# Three sources, and none of them is a registry. The KERNEL'S OWN external vocabularies are
# the six it speaks itself — RDF, RDFS, OWL, XSD, SHACL, PROV — stable, standardised, and the
# language a BDI engine's structure is written in (a want is a shape, a graph says who put a
# fact there). Every OTHER external vocabulary — `sosa:`, `ssn-system:`, `unit:`, `schema:`,
# `dcterms:` — is DISCOVERED, read off the `@prefix` lines of whichever ontology declares it,
# exactly as every namespace under this project's own base is: `sosa:` reaches a query because
# sensing's ontology says so, not because the kernel knows what a reading looks like (#378).
# What keeps a discovered label honest is `agent.loader`'s refusal of one label bound to two
# IRIs anywhere in the tree — which is the whole of what the old "an external vocabulary is not
# a package's to bind" argument needed, and it holds without the kernel naming the vocabulary.
# `orexis:` arrives the discovered way too, from the kernel's own `agent/ontology.ttl`.
#
# Assembled eagerly, at import. A malformed or missing ontology is then an error the moment the
# store is imported rather than the first time a query runs, which is the failure that used to
# arrive in production — see the module docstring of `tests/test_store.py`.
_KERNEL = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    #  Queried, not just validated against, since a desire became a shape: what an agent
    #  pursues is SHACL, so reading its numbers is an ordinary query over ordinary triples.
    "sh": "http://www.w3.org/ns/shacl#",
    "prov": "http://www.w3.org/ns/prov#",
    #  The kernel says TEMPORAL COVERAGE in Dublin Core's words, as it says provenance in
    #  PROV's: `dcterms:temporal` on a graph, pointing at a `dcterms:PeriodOfTime`. It was
    #  bound already — a part's ontology declares it — and a kernel term that depended on a
    #  DHT11 driver being installed is not bound at all.
    "dcterms": "http://purl.org/dc/terms/",
}

for _label, _iri in loader.external_prefixes().items():
    if _KERNEL.get(_label, _iri) != _iri:
        raise RuntimeError(f"prefix {_label!r} is the kernel's, bound to <{_KERNEL[_label]}>, "
                           f"and an ontology binds it to <{_iri}>")

NAMESPACES = {**loader.external_prefixes(), **_KERNEL, **loader.prefixes()}

_XSD = "http://www.w3.org/2001/XMLSchema#"
_XSD_ANY_URI = _XSD + "anyURI"

#  The header as TEXT, for the readers that parse rather than run: rdflib in `relevance.py`,
#  and any tool that wants a query to stand alone. The store itself hands the engine
#  `NAMESPACES` as a dictionary (#500), so no query text carries a header it did not write.
PREFIXES = "\n" + "\n".join(
    f"PREFIX {label}: <{iri}>" for label, iri in sorted(NAMESPACES.items())
) + "\n"

DECLARED = frozenset(NAMESPACES)

#  THE SAME DICTIONARY AS SHACL SPELLS IT (#508). A `sh:select` inside a shape may use a
#  prefixed name only if the constraint says `sh:prefixes <node>` and that node carries one
#  `sh:declare` per prefix — so every shape in the tree points at ONE node, `orexis:` itself,
#  and this is what stands there. ASSEMBLED, like `NAMESPACES`, never authored: a kernel
#  ontology listing every package's prefix would be the kernel knowing the packages. The judge
#  appends it to every shapes text it crosses to rudof, and the assembled shapes graph carries
#  it for pySHACL; neither engine is handed a shape whose dictionary is missing.
DECLARATION = "\n".join(
    [f"<{NAMESPACES['orexis']}> <{NAMESPACES['sh']}declare> ["
     f" <{NAMESPACES['sh']}prefix> \"{label}\" ;"
     f" <{NAMESPACES['sh']}namespace> \"{iri}\"^^<{_XSD_ANY_URI}> ] ."
     for label, iri in sorted(NAMESPACES.items())]
) + "\n"



def _terms(values: dict | None) -> dict | None:
    """A caller's substitutions as the engine's: name -> term. A Python string is an IRI —
    every parameter the kernel binds this way is one — a number or a bool a typed literal,
    and an engine term passes through; a string LITERAL is passed as `ox.Literal`."""
    if not values:
        return None
    out = {}
    for name, value in values.items():
        if isinstance(value, (ox.NamedNode, ox.BlankNode, ox.Literal)):
            term = value
        elif isinstance(value, bool):
            term = ox.Literal("true" if value else "false", datatype=ox.NamedNode(_XSD + "boolean"))
        elif isinstance(value, int):
            term = ox.Literal(str(value), datatype=ox.NamedNode(_XSD + "integer"))
        elif isinstance(value, float):
            term = ox.Literal(repr(value), datatype=ox.NamedNode(_XSD + "double"))
        elif isinstance(value, str):
            term = ox.NamedNode(value)
        else:
            raise TypeError(f"cannot bind ?{name} to {value!r}")
        out[ox.Variable(name)] = term
    return out


#  ── binding a rule TEXT ────────────────────────────────────────────────────────────────────
#
#  A rule text a package ships — a precondition, an effect, an estimate, a pattern — takes its
#  parameters as `$name` tokens, and they are bound by TEXT, deliberately (#500). The engine's
#  own parameter mechanism (SEP-0007 substitution, above) reaches only a variable the query
#  projects at its top level: measured, it cannot reach a subquery that does not project it,
#  nor an aggregate at all unless the variable is grouped — and an estimate is an aggregate
#  over a subquery reading `GRAPH $state`. A token reaches every scope. What this binder adds
#  over a chain of `.replace` is the three things a chain got wrong: it matches a WHOLE token
#  (`$this` never touches `$thisOther`), it renders a value as the term it is, and it REFUSES
#  a text that still carries a token nobody bound — the loud direction, where a chain left
#  `$state` in the text for the engine to parse as a variable named `state` and match every
#  graph at once.

_TOKEN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\b")
_IRI = re.compile(r"^(https?://|urn:|mailto:|file:)\S*$")


class Raw(str):
    """A value spliced in verbatim: a VALUES block, a USING list, a variable name — text that
    is not a term. The only way to put unrendered text through `bind`, and it says so."""


class Unbound(ValueError):
    """A rule text still carries `$tokens` after binding. Named, so the package can add the
    parameter or the caller can bind it; never left for the engine to read as a variable."""


_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  A class defined as an INTERSECTION (#576), read flat: per class, the named classes it
#  intersects, the values it pins by `owl:hasValue`, and the facets of a datatype restriction
#  it holds a property's value to. One row per part; `entail` assembles them. Read once per
#  store, because a definition changes only when genesis or an amendment writes one.
#  THE PREAMBLE REPEATED IN EVERY BRANCH, which is the engine's rule and not tidiness: a
#  FILTER or a BIND inside a UNION branch does not see a variable the surrounding pattern
#  bound (AGENTS.md's trap). Stated once with `{ FILTER(isIRI(?part)) BIND(?part AS ?base) }`
#  as the first branch, `?base` came back unbound for every class — so every definition
#  intersected NO named class, and a node of any type satisfied that vacuously.
_DEFINITIONS_Q = """
SELECT ?cls ?base ?pinP ?pinV ?pinVt ?rangeP ?facet ?bound WHERE {
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?base . FILTER(isIRI(?base)) }
  UNION
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?part .
    ?part owl:onProperty ?pinP ; owl:hasValue ?pin .
    BIND(IF(isIRI(?pin), STR(?pin), "") AS ?pinV)
    BIND(IF(isIRI(?pin), "", STR(?pin)) AS ?pinVt) }
  UNION
  { ?cls owl:equivalentClass/owl:intersectionOf ?list .
    ?list rdf:rest*/rdf:first ?part .
    ?part owl:onProperty ?rangeP ; owl:someValuesFrom/owl:withRestrictions ?facets .
    ?facets rdf:rest*/rdf:first ?f . ?f ?facet ?bound . FILTER(?facet != rdf:type) }
}"""


def _named(text: str) -> ox.NamedNode:
    """One node as a term, from what a caller writes: `<iri>`, a bare IRI, or a PREFIXED name
    in the store's own dictionary — which sensing's writer hands over, and which the engine
    used to expand when this was a query. Unexpanded it is a node nothing is written about,
    silently: a reading kept the band it was written with."""
    text = text.strip("<>")
    if "://" not in text and ":" in text:
        prefix, _, local = text.partition(":")
        if prefix in NAMESPACES:
            return ox.NamedNode(NAMESPACES[prefix] + local)
    return ox.NamedNode(text)


def _instant(text: str | None) -> datetime | None:
    """A bound as the instant it is, or None where the graph states none — which means always,
    on that side. An unparseable bound is None for the same reason a missing horizon is
    maximal: a graph whose period nobody can read is not one to drop silently."""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _term_of(row: dict, iri_key: str, text_key: str):
    """A pinned value as the engine's term: an IRI where the definition names one, else the
    literal it wrote — read back as the lexical form the row carries."""
    if row.get(iri_key):
        return ox.NamedNode(row[iri_key])
    return ox.Literal(row.get(text_key, ""))


def _within(values, facets) -> bool:
    """Does some value satisfy every facet of a datatype restriction? Numeric, as XSD reads
    them; a value that is not a number satisfies nothing, and no value at all is not within."""
    for v in values:
        try:
            n = float(v.value)
        except (AttributeError, TypeError, ValueError):
            continue
        if all((n < b if f == "maxExclusive" else n <= b if f == "maxInclusive" else
                n > b if f == "minExclusive" else n >= b if f == "minInclusive" else True)
               for f, b in facets):
            return True
    return False


def render(value) -> str:
    """One value as the SPARQL text of the term it is."""
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, ox.NamedNode):
        return f"<{value.value}>"
    if isinstance(value, ox.Literal):
        return str(value)                                   # its N-Triples form
    if isinstance(value, str):
        #  A bare IRI is wrapped; anything else that arrives as a string — `<…>`, `"…"`, a
        #  number's repr — is text already rendered and passes as written: a capability's
        #  Python and the tests still hand terms over rendered, and wrapping twice is the
        #  failure this must not add.
        if _IRI.match(value):
            return f"<{value}>"
        return value
    raise TypeError(f"cannot render {value!r} into a query")


#  The one token that may survive binding: SHACL's own `$this`, pre-bound by the judge and
#  not by us, which a derivation legitimately writes INTO a shape's `sh:select` string — the
#  freshness rule builds one with CONCAT — and which is therefore not a parameter of the
#  rule the string sits in. A caller that does bind it (a pattern run by the planner) gets it
#  replaced like any other.
_SHACLS_OWN = {"this"}


def bind(text: str, **values) -> str:
    """The rule text with every `$name` replaced by the term its value is, refusing leftovers.

    Tokens the text does not carry are ignored — a rule that ignores `$via` loses nothing —
    and tokens the caller did not bind raise `Unbound` with their names, `$this` excepted.
    """
    rendered = {name: render(value) for name, value in values.items()}
    out = _TOKEN.sub(lambda m: rendered.get(m.group(1), m.group(0)), text)
    left = sorted(set(_TOKEN.findall(out)) - _SHACLS_OWN)
    if left:
        raise Unbound(f"unbound in a rule text: {', '.join('$' + n for n in left)}")
    return out


# How many decimal places a derived number is written with. Well under the eighteen the store's
# fixed-point xsd:decimal can hold, and far more than a statistic deserves.
#
# This is not tidiness. A Python float divided out to full precision produces lexical forms like
# `0.0039920159680638745` — nineteen fractional digits — which the store accepts, returns, and
# reports the datatype of quite happily, and then FAILS TO COMPARE: every `=` and `>` against it
# raises, and a SPARQL `BIND` whose expression raises leaves its variable unbound while keeping
# the row. So a rule silently produced a solution binding nothing instead of an error, which is
# the most expensive shape a bug can take. Round on the way in and the whole class is gone.
PLACES = 6


def decimal(value: float) -> str:
    """A derived number as a SPARQL literal the store can actually do arithmetic on."""
    return f'"{value:.{PLACES}f}"^^xsd:decimal'


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]


class Store:
    """One agent's quad store. Persistent when given a path, in memory when not.

    A path is the normal case: beliefs must survive a restart, or every start would be a
    partial re-birth and a belief would be configuration again. In-memory exists for tests, and
    for tools that build a world, read it and throw it away.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = str(path) if path else None
        self._store = ox.Store(self.path) if self.path else ox.Store()
        self._public: list | None = None  # discovered on demand; see public_graphs()
        self._recorded: list | None = None  # likewise; see recorded_graphs()
        self._predictions = None
        self._periods: dict | None = None  # graph -> (start, end); see periods()
        self._memo: dict = {}             # what only a write can change; see remember()

    # --- what counts as public, according to the store itself ---

    def recorded_graphs(self, at: datetime | None = None) -> list[str]:
        """The agent's own graphs — what a plan carries into its imaginarium and a validation
        reads beside the state. Asked, never listed.

        NAMED WHETHER OR NOT THE GRAPH EXISTS YET, which is deliberate and was learned by
        intersecting with `graph_names()` and watching every world fail to boot: `sensed` has
        no graph until the first reading, and a validation that stopped naming it lost the
        state its shapes are written against. A graph that is not there contributes nothing —
        which is exactly how sensing's instruments graph behaved before it had ever been
        written — so the tolerant list is also the correct one.

        The intention ledger is named here and held in a store of its own; asking this store
        for it yields nothing, for the same reason.
        """
        if self._recorded is None:
            self._recorded = sorted(row["g"] for row in bindings(self.query(_OWN)))
        return self._holding_at(self._recorded, at)

    def prediction_graphs(self, at: datetime | None = None) -> list[str]:
        """Every prediction holding at `at` — a graph a package's drift wrote for a window, typed
        `orexis:PredictionGraph` in the classification (#642). Asked, never listed, and cached
        like the others: a write drops the answer."""
        if self._predictions is None:
            self._predictions = sorted(row["g"] for row in bindings(self.query(_PREDICTIONS)))
        return self._holding_at(self._predictions, at)

    def public_graphs(self, at: datetime | None = None, *, ever: bool = False) -> list[str]:
        """Every graph the vocabulary types as an `orexis:PublicGraph`, and still worth believing.

        Cached because it is asked before every query and the answer only moves when something
        is written. Any write drops the cache rather than trying to work out whether it mattered
        — the query is small and a stale answer here is an empty result rather than an error,
        which is the failure mode this whole design keeps having to guard against.

        Empty until a T-Box is loaded, and that is correct: a store nobody has told anything to
        has no public knowledge. Naming a graph explicitly still reads it, so the tools that
        build a bare store and query one graph are unaffected.
        """
        if self._public is None:
            rows = self._store.query(_DISCOVER, prefixes=NAMESPACES)
            self._public = sorted(str(row["g"].value) for row in rows)
        #  `ever`: every public graph whatever its period — for a copy that will be asked at
        #  instants of its own (the imaginarium, #619), which must hold a forecast for a period
        #  the copier has not reached, and filter by its own clock at each door.
        return list(self._public) if ever else self._holding_at(self._public, at)

    def periods(self) -> dict:
        """The period each graph holds during: IRI -> (start, end), either end None for open.

        Read from `graph/periods` and remembered until a write, like everything else here.
        The TABLE is remembered rather than a filtered list, because the answer to *which
        graphs now* depends on when it is asked and the table does not: filtering a handful of
        bounds in Python costs nothing, and a memo keyed by an instant would miss on every call.
        """
        if self._periods is None:
            self._periods = {
                str(row["g"].value): (_instant(row["start"] and row["start"].value),
                                      _instant(row["end"] and row["end"].value))
                for row in self._store.query(_PERIODS, prefixes=NAMESPACES)}
        return self._periods

    def _holding_at(self, graphs: list[str], at: datetime | None) -> list[str]:
        """`graphs`, less whatever is outside its own period at `at`.

        THE CLOCK IS READ HERE AND NOWHERE A RULE CAN REACH IT (#598,
        a-graph-holds-during-a-stretch): a graph is a scope a reader is handed, so the
        door drops what is not worth believing and every rule reads triples and asks nothing.
        `at` is None for *now*, and a caller with a clock of its own — a planning pass, which
        reads one clock at its root and would otherwise watch a graph expire between two forks
        — says which instant it means.
        """
        bounds = self.periods()
        if not bounds:
            return graphs           # nothing states a period: the store it always was
        when = at or clock.now()
        kept = []
        for graph in graphs:
            begins, ends = bounds.get(graph, (None, None))
            if begins is not None and when < begins:
                continue            # a forecast, before the period it holds during
            if ends is not None and when >= ends:
                continue            # said, and no longer holding
            kept.append(graph)
        return kept

    # --- reading ---

    def query(self, sparql: str, substitutions: dict | None = None) -> dict:
        """Read. There is no privileged variant: it is all yours, and only yours.

        An unqualified pattern reads **public knowledge** — the vocabulary, the world, and what
        the rules and the RDFS closure made of them, merged. That is what almost every caller
        wants, and stating it once here is what keeps the five public graphs from leaking into
        sixty queries.

        A `GRAPH <x>` clause still reads exactly `x`, private graphs included. So the two forms
        say different things on purpose: *what does the society know* versus *what is written
        precisely here* — and a review's write boundary is checkable because the second exists.
        """
        out = io.BytesIO()
        public = [ox.NamedNode(g) for g in self.public_graphs()]
        self._store.query(sparql, prefixes=NAMESPACES, default_graph=public,
                          substitutions=_terms(substitutions)).serialize(
            output=out, format=ox.QueryResultsFormat.JSON
        )
        return json.loads(out.getvalue())

    def query_at(self, sparql: str, substitutions: dict | None = None, *,
                 at: datetime | None = None) -> dict:
        """Read as a RULE reads: public knowledge AND this agent's own graphs, at an instant.

        `query` reads public alone, and a rule's SELECT has always been run through the
        construct door instead (`effects._select`, #472) because a premise may be a record.
        A round is now a graph of the agent's own holding during its period (#620), so what
        an availability select or a measure asks about a venue depends on WHEN it asks: the
        afforder and the urgency choir take this door with the instant a node stands at, and
        a round that will have closed by then is not there. JSON bindings, as `query`."""
        out = io.BytesIO()
        #  AND THE PREDICTIONS HOLDING THEN (#642): a reader standing at an instant is handed what
        #  a package expects the world to be then, beside what it knows.
        graphs = [ox.NamedNode(g) for g in (*self.public_graphs(at), *self.recorded_graphs(at),
                                            *self.prediction_graphs(at))]
        self._store.query(sparql, prefixes=NAMESPACES, default_graph=graphs,
                          substitutions=_terms(substitutions)).serialize(
            output=out, format=ox.QueryResultsFormat.JSON)
        return json.loads(out.getvalue())

    def construct(self, sparql: str, substitutions: dict | None = None,
                  at: datetime | None = None):
        """Run a CONSTRUCT and hand back the triples, which are not written anywhere.

        The one thing `query` cannot do: it serialises results as JSON bindings, and a
        CONSTRUCT has none — it has a graph. Added for effect rules (#238), where the answer to
        "what would this lever make true" is a set of triples nobody has asserted and nobody
        should: a possible world is computed and dropped, so the only honest return here is the
        triples themselves.

        Reads the public graphs AND this agent's own, so a rule sees the world it is asked
        about — never another agent's, because there is no such graph in this store to see.

        The agent's own were added when the obligations ledger stopped being the kernel's: a
        rule that must name `GRAPH $owed` to reach a record is a rule whose graph somebody
        outside the package has to know, and the planner was substituting it. Widening the
        union lets a package's rule match its own record by the premises it wrote (its claim) without
        anyone naming a graph — which is rule 1 for graph IRIs, applied to the one road that
        had been exempt.
        """
        #  AT WHICH INSTANT (#589): a rule asked about a world the agent has not reached is
        #  asked about the graphs that hold THEN, not the ones holding now — which is how a
        #  forecast reaches a step landing inside it and no rule has to know the time.
        public = [ox.NamedNode(g) for g in (*self.public_graphs(at), *self.recorded_graphs(at))]
        return list(self._store.query(sparql, prefixes=NAMESPACES, default_graph=public,
                                      substitutions=_terms(substitutions)))

    # Kept so callers written against the old two-door store still read: with one private store
    # per agent, the distinction it drew — "as myself" versus "as admin" — has no meaning.
    query_all = query

    def query_over(self, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
        """Read with the default graph being EXACTLY these graphs, merged.

        For a text that carries no `GRAPH` clause and no `$state` — a compiled violation
        select (`violation.py`) — asked about one world: public knowledge, this agent's
        records and ONE readings graph, which is the same view the judge is handed as a flat
        text. The caller names the readings graph, because in the imaginarium every node of
        a search has one and an unqualified union would read every sibling world at once.
        """
        out = io.BytesIO()
        self._store.query(sparql, prefixes=NAMESPACES,
                          default_graph=[ox.NamedNode(g) for g in graphs],
                          substitutions=_terms(substitutions)).serialize(
            output=out, format=ox.QueryResultsFormat.JSON)
        return json.loads(out.getvalue())

    def query_union(self, sparql: str, substitutions: dict | None = None) -> dict:
        """Read with the default graph as the union of EVERYTHING this store holds.

        For two callers. The sovereign's question channel (packages/orexis-capability-reporting/sovereign.py): an
        agent answering its sovereign answers about its WHOLE self — beliefs, record,
        evidence, revisions — not only the public knowledge an ordinary query reads, and
        making the sovereign spell each private graph IRI would be rule 1's own trap
        (a graph IRI is an instance). And the desires store's build (desire.py, beside this file), whose
        question — what are this store's graphs — is about the whole store for the same
        reason. Still read-only by construction: this is the same
        query API, which structurally cannot execute an update.
        """
        out = io.BytesIO()
        self._store.query(sparql, prefixes=NAMESPACES, use_default_graph_as_union=True,
                          substitutions=_terms(substitutions)).serialize(
            output=out, format=ox.QueryResultsFormat.JSON
        )
        return json.loads(out.getvalue())

    def get_graph(self, graph_iri: str) -> str:
        """A graph's contents as Turtle, or empty if it does not exist yet.

        A graph nobody has written to is not an error: `:sensed` is absent until the first
        reading, and a caller should be able to say so rather than crash.
        """
        out = io.BytesIO()
        self._store.dump(
            output=out, format=ox.RdfFormat.TURTLE, from_graph=ox.NamedNode(graph_iri)
        )
        return out.getvalue().decode()

    def dump_nt(self, *graph_iris: str) -> str:
        """Several graphs as ONE N-Triples text, written by the store's own engine.

        N-Triples because it CONCATENATES — every line stands alone, so several graphs join
        with `+` and nothing has to be re-parsed to merge them — and because the writer is the
        cost at a border: rdflib spends 86 ms on 2,400 triples of Turtle where N-Triples takes
        12, since Turtle groups by subject and hunts for prefixes. Four times the bytes, and
        nobody reads them. See knowledge/runbooks/measure-the-search.md.

        A graph nobody has written to contributes nothing, exactly as `get_graph` allows.
        """
        out = io.BytesIO()
        for iri in graph_iris:
            self._store.dump(output=out, format=ox.RdfFormat.N_TRIPLES,
                             from_graph=ox.NamedNode(iri))
        return out.getvalue().decode()

    def quads(self, graph_iri: str):
        """One graph's contents as QUADS, for a reader that is going to put them somewhere else.

        `get_graph` says the same thing in Turtle, and going through text is what a copy must
        not do: a serialise-and-reparse relabels blank nodes, so an observation node would come
        out the far side unequal to the one a retraction names. It is also the same trap
        `effects._triple` exists for, one layer up — a term crossing a boundary as text stops
        being that term. The one caller is `orexis_agent_deliberation.imaginarium`, which is filling a second store
        with what this one holds.
        """
        return self._store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri))

    def has_graph(self, graph_iri: str) -> bool:
        """Whether anything has been written here — how birth knows it already happened."""
        return any(self._store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri)))

    # --- writing ---

    def entail(self, graph_iri: str, of=(), among: str = "") -> list:
        """Assert in `graph_iri` what the vocabulary entails of the nodes there: membership
        under every class defined as an `owl:intersectionOf` a named class, `owl:hasValue`
        restrictions and a datatype restriction with `owl:withRestrictions` facets — the
        second OWL construct this store honours by materialising it, beside the closure's
        `owl:hasValue` (agent/inference.py, rule 5). Deliberation is on triples, and a number
        is not special: what a reading IS is decided inside the domain as classes and
        asserted here, where a step's precondition can then say it as a triple (#576).

        THE DEFINITIONS ARE READ AS DATA AND EVALUATED HERE, which is the compiler's bargain
        one layer over (`violation.py`): the domain owns the declaration, the kernel owns how
        it is answered. As one SPARQL question — every class, then three "for all" clauses
        walking its list by property path per candidate — it cost 300 ms a call however
        narrowed, and a pass forks tens of worlds. Read once per store and evaluated against a
        node's own triples, a fork's question is a dictionary lookup. What is asserted is
        exactly what the OWL says, and an outside reasoner would say the same.

        `of` narrows the question to some NAMED nodes — the reading just written — as rendered
        terms; `among` to the nodes a pattern picks out inside the graph, which is how a fork's
        observation is named, being a blank node no `VALUES` can reach. Neither given, every
        node in the graph is asked. Returns the memberships asserted, as `(node, class)` pairs
        of engine terms, and asserts through the term API rather than an INSERT: a blank node
        written back as text is a new blank node.
        """
        graph = ox.NamedNode(graph_iri)
        nodes = self._nodes_in(graph_iri, of, among)
        defs, supers, keyed = self._definitions()
        out = []
        for node in nodes:
            held = {q.predicate: set() for q in ()}
            values, types = {}, set()
            for q in self._store.quads_for_pattern(node, None, None, graph):
                if q.predicate == _RDF_TYPE:
                    types.add(q.object)
                values.setdefault(q.predicate, set()).add(q.object)
            for cls, (bases, pinned, ranges) in defs.items():
                if cls in types or not bases <= types:
                    continue
                if any(v not in values.get(p, ()) for p, v in pinned):
                    continue
                if all(_within(values.get(p, ()), facets) for p, facets in ranges):
                    out.append((node, cls))
                    types.add(cls)
            #  AND THE FAMILIES (#579): every class the node is now typed with, closed upward
            #  by `rdfs:subClassOf`, so a shape's `sh:class sensing:BelowRegion` and a
            #  measure's `?obs a sensing:InRegion` read what a reading IS without walking a
            #  subclass path, which is the closure's one rule. STOPPING AT A KEYED CLASS: a
            #  reading gains its bands' families and never what sits above `sosa:Observation`,
            #  which every reading has alike and which the signature would read as a fact.
            stop = {s for k in types & keyed for s in supers.get(k, ())} | (types & keyed)
            for cls in list(types):
                for sup in supers.get(cls, ()):
                    if sup not in types and sup not in stop:
                        out.append((node, sup))
                        types.add(sup)
        for node, cls in out:
            self._store.add(ox.Quad(node, _RDF_TYPE, cls, graph))
        #  NOTHING IS FORGOTTEN. Every other write drops what was learned by asking, because
        #  it may have moved it; this one asserts a class on a node in one graph and can move
        #  none of it — which graphs are public, which the agent's own, a rule's text, the
        #  definitions themselves. Forgetting here re-read the definitions once per fork, 140
        #  ms each, and a pass forks tens of worlds.
        return out

    def _nodes_in(self, graph_iri: str, of, among: str) -> list:
        """The nodes to ask about: those named, those a pattern picks out, or all of them."""
        if of and not among:
            return [_named(x) if isinstance(x, str) else x for x in of]
        if among:
            text = f"SELECT DISTINCT ?x WHERE {{ GRAPH <{graph_iri}> {{ {among} }} }}"
            return [r["x"] for r in self._store.query(
                text, prefixes=NAMESPACES, named_graphs=[ox.NamedNode(graph_iri)])]
        seen, graph = [], ox.NamedNode(graph_iri)
        for q in self._store.quads_for_pattern(None, _RDF_TYPE, None, graph):
            if q.subject not in seen:
                seen.append(q.subject)
        return seen

    def _definitions(self):
        """The domain's class definitions, read once per store: class -> (named classes it
        intersects, the values it pins, the ranges it holds a value to); the subclass closure;
        and which classes some package declared `orexis:keyedBy`. Dropped on every write with
        the rest of `remember`, since a genesis or an amendment may mint more."""
        return self.remember(("definitions",), self._read_definitions)

    def _read_definitions(self):
        rows = bindings(self.query(_DEFINITIONS_Q))
        defs: dict = {}
        for r in rows:
            cls = ox.NamedNode(r["cls"])
            bases, pinned, ranges = defs.setdefault(cls, (set(), set(), {}))
            if r.get("base"):
                bases.add(ox.NamedNode(r["base"]))
            if r.get("pinP"):
                pinned.add((ox.NamedNode(r["pinP"]), _term_of(r, "pinV", "pinVt")))
            if r.get("rangeP") and r.get("facet"):
                ranges.setdefault(ox.NamedNode(r["rangeP"]), []).append(
                    (r["facet"].rsplit("#", 1)[-1], float(r["bound"])))
        defs = {c: (b, p, tuple(r.items())) for c, (b, p, r) in defs.items()}
        supers: dict = {}
        for r in bindings(self.query(
                "SELECT ?c ?s WHERE { ?c rdfs:subClassOf+ ?s . FILTER(isIRI(?s) && isIRI(?c)) }")):
            supers.setdefault(ox.NamedNode(r["c"]), set()).add(ox.NamedNode(r["s"]))
        keyed = {ox.NamedNode(r["c"]) for r in bindings(self.query(
            "SELECT DISTINCT ?c WHERE { ?c <http://example.org/orexis#keyedBy> ?p }"))}
        return defs, supers, keyed

    def update(self, sparql: str) -> None:
        self._store.update(sparql, prefixes=NAMESPACES)
        self._forget()
        for listener in list(self.__dict__.get("_listeners", ())):
            listener()

    def _forget(self) -> None:
        """Every write drops what was learned by asking: which graphs are public, which are
        the agent's own, and whatever `remember` holds. Dropping rather than working out
        whether the write mattered, because a stale answer here is an empty result rather
        than an error — the failure this design keeps having to guard against."""
        self._public = None
        self._recorded = None
        self._periods = None
        self._predictions = None
        self._memo.clear()

    def remember(self, key, compute):
        """A per-store memo of something only a write can change — a rule text read off
        public knowledge, say — computed once and handed back until the next write through
        this store (#552: the effect door was fetching the same rule text on every fork, for
        three callers, and asking which graphs are the agent's own on every construct — half
        of a hanoi solve's store calls, and none of them could have answered differently).
        A caller that writes around the store (`_store.add` at construction) writes before
        anything is remembered, and the imaginarium's forks are graphs nothing here lists."""
        if key not in self._memo:
            self._memo[key] = compute()
        return self._memo[key]

    def on_write(self, listener) -> None:
        """Be told after every update — the one event the store itself emits (#512).

        For the keeper: an intention held until a condition on the world re-asks its
        condition when the world changes, and the world changes by a write. Called on the
        writer's thread, after the write, with nothing: the listener asks the store what it
        wants to know. Progression's own hook, so the layer above the store learns of a
        belief landing without the kernel naming any package's event.
        """
        self.__dict__.setdefault("_listeners", []).append(listener)

    def put_graph(self, graph_iri: str, ttl: str, dataset: bool = False) -> None:
        """Replace a graph with the given Turtle. Public knowledge only — see the module note.

        `dataset=True` parses **TriG** instead, which is Turtle plus `GRAPH <iri> { … }` blocks.
        Every existing `.ttl` is valid TriG unchanged — Turtle is a syntactic subset — and
        `to_graph` is the destination for the document's *default* graph only, so a file with no
        `GRAPH` block behaves exactly as it did. A file that grows one puts those triples where
        it says — which is how a world states a root desire (#298): a named block, and beside
        it the typing that makes the catalog call the graph what it is.

        **A graph the file names is REPLACED, exactly as the named one is.** The first draft
        cleared only `graph_iri` and said so; the day a world actually declared a block, that
        gap became an amendment bug — a ratification that dropped a desire would have left it
        readable forever, because loading is additive and a quad store keeps what nobody
        removes. So the document is parsed apart first, and every graph it names is cleared
        before its quads land: what a world's files say is what the store holds, for the named
        blocks as for the world graph itself.
        """
        graph = ox.NamedNode(graph_iri)
        if dataset:
            parsed = ox.Store()
            parsed.load(ttl, format=ox.RdfFormat.TRIG)
            for named in parsed.named_graphs():
                self._store.remove_graph(named)
            self._store.remove_graph(graph)
            for quad in parsed:
                self._store.add(quad if not isinstance(quad.graph_name, ox.DefaultGraph)
                                else ox.Quad(quad.subject, quad.predicate, quad.object, graph))
        else:
            self._store.remove_graph(graph)
            self._store.load(ttl, format=ox.RdfFormat.TURTLE, to_graph=graph)
        self._forget()

    def endow_graph(self, graph_iri: str, ttl: str) -> list[str]:
        """Add whatever the Turtle authors that the graph has NEVER held. Touch nothing held.

        The amendment half of birth (#202): a world may grant an agent a new capability, and
        the capability's opening beliefs must reach a volume that already exists — but a
        belief the agent holds is the agent's, revisions included, so the unit of novelty is
        the TERM: a predicate the graph holds is skipped whole, whatever its value, and one
        it has never held is added with its blank-node closure (an aim is a structure, not a
        triple). The term and not the (subject, predicate) pair, measured rather than
        assumed: a beliefs graph has one owner, in whatever spelling its era wrote — a
        volume from before the worlds-own-their-individuals sweep says `orexis:fern_agent` where
        today's files say the world's name — and pair-keying read that drift as novelty,
        doubling a migrated belief the first time the two met. Returns the terms added, so
        the caller can say what the amendment endowed; empty means the volume already holds
        everything authored, which is every boot but the first after an amendment.
        """
        graph = ox.NamedNode(graph_iri)
        held = {q.predicate
                for q in self._store.quads_for_pattern(None, None, None, graph)}
        authored = list(ox.parse(ttl, format=ox.RdfFormat.TURTLE))
        by_subject: dict = {}
        for t in authored:
            by_subject.setdefault(t.subject, []).append(t)

        added: list[str] = []
        queue: list = []
        for t in authored:
            if isinstance(t.subject, ox.BlankNode):
                continue  # reached only through the pair that owns it
            if t.predicate in held:
                continue
            queue.append(t)
            added.append(t.predicate.value)
        seen_bnodes: set = set()
        i = 0
        while i < len(queue):
            t = queue[i]
            i += 1
            self._store.add(ox.Quad(t.subject, t.predicate, t.object, graph))
            if isinstance(t.object, ox.BlankNode) and t.object not in seen_bnodes:
                seen_bnodes.add(t.object)
                queue.extend(by_subject.get(t.object, []))
        if added:
            self._forget()
        return sorted(set(added))

    def graph_names(self) -> list[str]:
        """Every named graph actually present, whatever anyone still declares."""
        return [str(g.value) for g in self._store.named_graphs()]

    def clear_graph(self, graph_iri: str) -> None:
        """Empty one graph. For the computed ones, which are written by update rather than
        loaded from a file and so have no `put_graph` to replace them wholesale."""
        self._store.remove_graph(ox.NamedNode(graph_iri))
        self._forget()

    def load_file(self, path: str | Path, graph_iri: str) -> None:
        """Read a ratified file straight into a graph, without going through a string."""
        self._store.load(path=str(path), format=ox.RdfFormat.TURTLE,
                         to_graph=ox.NamedNode(graph_iri))
        self._forget()

    def optimize(self) -> None:
        """Compact the store. Blocking, and worth it only when something says it is needed.

        The belief base is an LSM tree, and every reading is a DELETE followed by an INSERT — so
        each one appends a new version plus a tombstone, and the old versions are reclaimed only
        by compaction. Compaction is size-triggered, and a few hundred triples never approach
        any threshold: the file grows for ever while the triple count does not move. Nothing
        reclaimed here is data, so nothing is lost by asking for it explicitly.

        See knowledge/decisions/a-belief-is-a-pick-within-a-range.md and issue #45.
        """
        self._store.optimize()

    def __len__(self) -> int:
        return len(self._store)
