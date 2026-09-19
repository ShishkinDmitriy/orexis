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
from .ontology import OREXIS, PUBLIC

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
#  THE CATALOGUE — the one graph that says what every graph IS: its class, whose it is, how
#  it arrived, when it holds, and the PROV account of the load that made it (one-catalogue-
#  describes-every-graph-and-itself). It DESCRIBES ITSELF, which is what lets a store find it
#  without knowing its name: the one graph that says of itself `a orexis:CatalogueGraph`.
#  Nothing else about graphs is named anywhere a reader stands — the bootstrap root used to be
#  two named graphs, the ontology's instances and the classification, with the periods in a
#  third and the provenance in a fourth; a writer names the catalogue when it creates it, and
#  a migration names what it migrates from.
#
#  NOT PUBLIC, deliberately: a rule reads triples and never learns what a graph is, whose it
#  is, or when it holds — the door decides all three, structurally, by handing the rule a
#  dataset (a-graph-holds-during-a-stretch). Every door here reads the catalogue by the IRI
#  it discovered, and nothing else does.
CATALOGUE = OREXIS + "CatalogueGraph"
_CATALOGUES = f"SELECT ?g WHERE {{ GRAPH ?g {{ ?g a <{CATALOGUE}> }} }}"

#  THE INDEX of the catalogue: one row per graph and class, with the owner, the arrival and
#  the period beside — read with one query, the class hierarchy with a second, and kept
#  until a write. Which graphs are public, the agent's own, predictions or records is then a
#  question of set membership in Python rather than four SPARQL texts with the NOT EXISTS
#  traps this file used to carry (a VALUES-bound path end evaluated per candidate, a NOT
#  EXISTS evaluated before a UNION binds).
def _entries(catalogue: str) -> str:
    return f"""
SELECT ?g ?class ?owner ?arrival ?period ?start ?end WHERE {{
  GRAPH <{catalogue}> {{
    ?g a ?class . FILTER(isIRI(?g))          # a period's blank node is typed here too, and is no graph
    OPTIONAL {{ ?g orexis:beliefsOf ?owner }}
    OPTIONAL {{ ?g orexis:arrivedBy ?arrival }}
    OPTIONAL {{ ?g dcterms:temporal ?period .
               OPTIONAL {{ ?period orexis:start ?start }} OPTIONAL {{ ?period orexis:end ?end }} }} }} }}"""


def _supers(ontologies: list[str]) -> str:
    """The class hierarchy, from the graphs the catalogue types as the vocabulary's: every
    `rdfs:subClassOf` there, closed in Python. Small — the graph classes are a few dozen."""
    return ("SELECT DISTINCT ?c ?s WHERE { GRAPH ?onto { ?c rdfs:subClassOf ?s } FILTER(isIRI(?c) && isIRI(?s)) VALUES ?onto { "
            + " ".join(f"<{g}>" for g in ontologies) + " } }")


class _Entry:
    """What the catalogue says of one graph."""

    __slots__ = ("classes", "owner", "arrival", "timed", "start", "end")

    def __init__(self):
        self.classes: set = set()
        self.owner = self.arrival = self.start = self.end = None
        self.timed = False                  # says a period, readable or not


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
        self._catalogue: str | None = None      # the graph that describes itself; see `catalogue`
        self._catalogue_index: dict | None = None   # what it says of every graph; see `_index`
        self._supers: dict = {}                  # the vocabulary's class hierarchy, as `_index` read it
        self._memo: dict = {}             # what only a write can change; see remember()
        #  WHOSE STORE THIS IS, told by the belief base when it is built over the store — the
        #  agent the world declares under the id the process was handed. None until told: a
        #  bare store answers for every classified graph. See `agent_uri` below.
        self._agent_uri: str | None = None

    @property
    def agent_uri(self) -> str | None:
        """The agent whose store this is, or None where nothing has said. What a list of the
        agent's OWN graphs is kept to (`_mine`): the classification says whose each graph is,
        by the owner that wrote it, and a reader that means its own asks the class and gets
        this agent's. Told, the store forgets what it learned by asking, since the answer to
        which graphs are its own has moved."""
        return self._agent_uri

    @agent_uri.setter
    def agent_uri(self, uri: str | None) -> None:
        self._agent_uri = uri
        self._forget()

    # --- what counts as public, according to the store itself ---

    @property
    def catalogue(self) -> str | None:
        """The graph that describes every graph and itself — found by asking every graph for
        the one that says of itself `a orexis:CatalogueGraph`, once, and kept: nothing moves
        it. None for a store nobody has told anything to, which then has no public knowledge,
        no own graphs and no periods — the store it always was. Two is refused: a store with
        two catalogues has two truths about what its graphs are."""
        if self._catalogue is None:
            found = sorted(str(row["g"].value) for row in self._store.query(_CATALOGUES, prefixes=NAMESPACES))
            if len(found) > 1:
                raise RuntimeError(f"two graphs describe themselves as the catalogue: {', '.join(found)}")
            self._catalogue = found[0] if found else None
        return self._catalogue

    def _index(self) -> dict:
        """Every graph the catalogue describes, with its classes CLOSED over the vocabulary's
        `rdfs:subClassOf` — so a membership test asks what a graph IS and walks nothing."""
        if self._catalogue_index is not None:
            return self._catalogue_index
        catalogue = self.catalogue
        entries: dict = {}
        if catalogue is not None:
            for row in self._store.query(_entries(catalogue), prefixes=NAMESPACES):
                e = entries.setdefault(str(row["g"].value), _Entry())
                e.classes.add(str(row["class"].value))
                for name in ("owner", "arrival"):
                    if row[name] is not None:
                        setattr(e, name, str(row[name].value))
                if row["period"] is not None:
                    e.timed = True                  # a bound nobody can read reads as open, and the graph stays
                for name in ("start", "end"):
                    if row[name] is not None:
                        setattr(e, name, _instant(row[name].value))
            ontologies = [g for g, e in entries.items() if OREXIS + "OntologyGraph" in e.classes]
            supers: dict = {}
            if ontologies:
                for row in self._store.query(_supers(ontologies), prefixes=NAMESPACES):
                    supers.setdefault(str(row["c"].value), set()).add(str(row["s"].value))
            self._supers = supers
            for e in entries.values():
                e.classes = self._closed(e.classes)
        self._catalogue_index = entries
        return entries

    def _closed(self, classes) -> set:
        """`classes` with every superclass the vocabulary states, walked in Python over the
        table `_index` read — so a row written by hand with one class still reads as every
        kind it is beneath. The table is `_index`'s to fill; a caller outside it asks the
        index first."""
        todo, seen = list(classes), set()
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            seen.add(c)
            todo.extend(self._supers.get(c, ()))
        return seen

    def _mine(self, graph: str, entry) -> bool:
        """A graph saying whose it is must say it is this agent's; one saying nothing is
        anyone's — a volume written before owners were said, a case's hand-written roots.
        Every graph, where the store has been told no owner (rule 4: one agent, one volume)."""
        return self.agent_uri is None or entry.owner is None or entry.owner == self.agent_uri

    def graphs_of(self, *kinds: str, at: datetime | None = None) -> list[str]:
        """Every graph the catalogue types under any of `kinds` — subclasses included, the
        index having closed them — and this agent's where the store has been told whose it
        is; holding at `at` where an instant is given, whatever its period where none is.

        THE ONE LOOKUP A READER TAKES (a-reader-states-the-kinds-it-reads). A reader says
        which kinds it means and, if it stands at an instant, which; the store answers with
        graphs and decides nothing else — no kind is carried or hidden by a rule of the
        store's, and no clock is read here. A reader meaning *now* says so with the clock it
        holds. Naming a graph is what rule 1 forbids and what a rename would break; a reader
        that must (a writer reading what it wrote) hands `query` the name itself."""
        wanted = set(kinds)
        found = sorted(g for g, e in self._index().items() if e.classes & wanted and self._mine(g, e))
        return found if at is None else self._holding_at(found, at)

    def windows_of(self, *kinds: str) -> list[tuple[str, datetime | None, datetime | None]]:
        """Every graph of these kinds with the period it holds during, earliest start first —
        what a crossing is read off (#643): the start of the earliest window at which a root
        reads unmet. A graph stating no period is listed with none."""
        index = self._index()
        out = [(g, index[g].start, index[g].end) for g in self.graphs_of(*kinds)]
        return sorted(out, key=lambda w: (w[1] is None, w[1] or datetime.min.replace(tzinfo=timezone.utc)))

    def entry(self, graph: str, graph_class: str, arrival: str, owner: str | None = None,
              start: datetime | str | None = None, end: datetime | str | None = None) -> str:
        """What the catalogue says of a graph, as the `GRAPH … { … }` block a writer puts
        beside the graph's own in ONE update — so a graph and its description land together
        or not at all. The writer names nothing: the catalogue is the store's to find."""
        catalogue = self.catalogue
        if catalogue is None:
            raise RuntimeError("no graph describes itself as the catalogue — nothing has said what the graphs are")
        self._index()
        whose = f" ; orexis:beliefsOf <{owner}>" if owner else ""
        stamp = lambda t: t if isinstance(t, str) else t.isoformat()
        when = ""
        if start is not None or end is not None:
            bounds = "".join(f' ; orexis:{k} "{stamp(v)}"^^xsd:dateTime' for k, v in (("start", start), ("end", end)) if v is not None)
            when = f" ; dcterms:temporal [ a dcterms:PeriodOfTime{bounds} ]"
        #  EVERY KIND THE GRAPH IS, on the row: the class the writer names and each class the
        #  vocabulary puts it beneath, so a text that joins the catalogue asks `?g a
        #  orexis:WantGraph` and walks no path across two graphs.
        kinds = " , ".join(f"<{c}>" for c in sorted(self._closed({graph_class})))
        return (f"GRAPH <{catalogue}> {{ <{graph}> a {kinds} ; orexis:arrivedBy <{arrival}>"
                f"{whose}{when} . }}")

    def classify(self, graph: str, graph_class: str, arrival: str, owner: str | None = None,
                 start: datetime | str | None = None, end: datetime | str | None = None) -> None:
        """Say what a graph IS, how it arrived, WHOSE it is and WHEN it holds — by its owner,
        when it creates the graph and at every start, whatever the graph is called. A name is
        for eyes; every reader asks the catalogue. Idempotent for the same statement, so an
        owner may say it at construction without asking whether the graph is new; a writer
        that lands the graph in the same update embeds `entry` instead."""
        self.update(f"INSERT DATA {{ {self.entry(graph, graph_class, arrival, owner, start, end)} }}")

    def close_catalogue(self) -> None:
        """Say on every row each kind the vocabulary puts its class beneath — what `entry`
        writes on a new row, said again of every row there is: a volume written when a row
        said one class, a case written by hand. Idempotent, and a write like any other, so
        the index is read again afterwards. What it makes true: a text that joins the
        catalogue asks `?g a orexis:WantGraph` and a pursued graph answers."""
        catalogue = self.catalogue
        if catalogue is None:
            return
        rows = "\n".join(f"  <{g}> a {' , '.join(f'<{c}>' for c in sorted(e.classes))} ."
                         for g, e in self._index().items() if e.classes)
        if rows:
            self.update(f"INSERT DATA {{ GRAPH <{catalogue}> {{\n{rows} }} }}")

    def drop_graph(self, graph: str) -> None:
        """Drop one graph whole — its triples and everything the catalogue says of it — which
        is how a round closes, a prediction is dropped and the sweep drops what is outdated
        (#645). One update, so a graph goes entire or not at all."""
        catalogue = self.catalogue
        about = ""
        if catalogue is not None:
            about = f"""
  GRAPH <{catalogue}> {{ <{graph}> ?cp ?co . }}
  GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }}"""
        self.update(f"""
DELETE {{
  GRAPH <{graph}> {{ ?s ?p ?o }}{about} }}
WHERE  {{
  {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}""" + (f"""
  UNION {{ GRAPH <{catalogue}> {{ <{graph}> ?cp ?co }} }}
  UNION {{ GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }}""" if catalogue else "") + " }")

    def outdated(self, at: datetime | None = None) -> list[str]:
        """Every graph of this agent's own whose period has ENDED by `at` — what the door
        already hides from every reader and the one sweep drops (#645,
        a-root-holds-always-and-an-outdated-graph-is-dropped): a round, a claim, a cooling
        row, a pursued child, a prediction, whatever its kind. Never a public graph: a period
        the world states is the world's to end."""
        when = at or clock.now()
        index = self._index()
        return sorted(g for g, (_, end) in self.periods().items()
                      if end is not None and when >= end
                      and OREXIS + "PublicGraph" not in index[g].classes and self._mine(g, index[g]))

    def periods(self) -> dict:
        """The period each graph holds during: IRI -> (start, end), either end None for open.
        Read off the catalogue and remembered until a write, like everything else here. The
        TABLE is remembered rather than a filtered list, because the answer to *which graphs
        now* depends on when it is asked and the table does not."""
        return {g: (e.start, e.end) for g, e in self._index().items() if e.timed}

    def _holding_at(self, graphs: list[str], at: datetime | None) -> list[str]:
        """`graphs`, less whatever is outside its own period at `at`.

        A graph is a scope a reader is handed (#598, a-graph-holds-during-a-stretch): what
        is outside its period at the instant the reader stands at is not handed, and every
        rule reads triples and asks nothing about time. The instant is the reader's — a
        planning pass reads one clock at its root and would otherwise watch a graph expire
        between two forks — and no clock is read here for it.
        """
        bounds = self.periods()
        if not bounds:
            return graphs           # nothing states a period: the store it always was
        index = self._index()
        kept = []
        for graph in graphs:
            begins, ends = bounds.get(graph, (None, None))
            #  A RECORD IS HANDED AS IT STANDS, whatever instant is asked about (#645,
            #  `orexis:RecordGraph`): its period says how long it is worth believing, not
            #  when it holds — a debt standing today is an arrival at every later instant.
            when = clock.now() if OREXIS + "RecordGraph" in index[graph].classes else at
            if begins is not None and when < begins:
                continue            # a forecast, before the period it holds during
            if ends is not None and when >= ends:
                continue            # said, and no longer holding
            kept.append(graph)
        return kept

    # --- reading ---

    def query(self, sparql: str, graphs, substitutions: dict | None = None) -> dict:
        """Read `sparql` with `graphs` merged as its default graph, as JSON bindings.

        THE READER SAYS WHAT IT READS (a-reader-states-the-kinds-it-reads). `graphs` is the
        list the caller built — `graphs_of` the kinds it means at the instant it stands at,
        a graph it wrote and reads back by name, a possible world in the state's place — and
        this store adds nothing to it and takes nothing from it. Every named graph stays
        reachable through a `GRAPH` clause, so a text may instead say for itself which
        graphs it reads by joining the catalogue, kind and period included, and be handed
        no default at all. There is no other read: `query_union` is the whole store, for
        the sovereign's question about the whole self and for a dump, and nothing in the
        kernel takes it.
        """
        out = io.BytesIO()
        self._store.query(sparql, prefixes=NAMESPACES,
                          default_graph=[ox.NamedNode(g) for g in graphs],
                          substitutions=_terms(substitutions)).serialize(
            output=out, format=ox.QueryResultsFormat.JSON)
        return json.loads(out.getvalue())

    def reader(self, *kinds: str, at: datetime | None = None):
        """`query` over the graphs of `kinds` at `at`, as one callable — for a helper handed
        a way to ask rather than a store (`load_world`, `regions_of`, `current_reading`).
        The kinds are the caller's, stated where the callable is made."""
        return lambda sparql, substitutions=None: self.query(
            sparql, self.graphs_of(*kinds, at=at), substitutions)

    def construct(self, sparql: str, graphs, substitutions: dict | None = None):
        """Run a CONSTRUCT over `graphs` as the default graph and hand back the triples,
        which are not written anywhere.

        The one thing `query` cannot do: it serialises results as JSON bindings, and a
        CONSTRUCT has none — it has a graph. Added for effect rules (#238), where the answer to
        "what would this lever make true" is a set of triples nobody has asserted and nobody
        should: a possible world is computed and dropped, so the only honest return here is the
        triples themselves. What it reads is the caller's list, exactly as `query`.
        """
        return list(self._store.query(sparql, prefixes=NAMESPACES,
                                      default_graph=[ox.NamedNode(g) for g in graphs],
                                      substitutions=_terms(substitutions)))

    def query_over(self, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
        """`query`, with the graphs as positional names — a writer reading what it wrote."""
        return self.query(sparql, graphs, substitutions)

    def query_union(self, sparql: str, substitutions: dict | None = None) -> dict:
        """Read with the default graph as the union of EVERYTHING this store holds.

        For the sovereign's question channel (packages/orexis-capability-reporting/sovereign.py):
        an agent answering its sovereign answers about its WHOLE self — beliefs, record,
        evidence, revisions — and making the sovereign spell each private graph IRI would be
        rule 1's own trap (a graph IRI is an instance). And for a test reading a store back
        whole. Nothing in the kernel reads through it: a reader there says which kinds it
        means. Still read-only by construction: this is the same query API, which
        structurally cannot execute an update.
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

    def copy_graphs(self, source, *graph_iris: str, forget: bool = True) -> None:
        """Copy whole graphs in from ANOTHER store, under their own names.

        The reader's half and the writer's half of the same act, which every caller was pairing
        by hand — `quads` out of one store, `add_quads` into the next — so a copy between two
        stores was the one place a caller had to think in quads to do something it thought of
        in graphs. It is quads underneath for the reason `quads` gives: text relabels blank
        nodes, and a term that crosses a boundary as text stops being that term.
        """
        self.add_quads((quad for iri in graph_iris for quad in source.quads(iri)), forget=forget)

    def add_quads(self, quads, *, forget: bool = True) -> None:
        """Write quads straight in, as the TERMS they are — the writing half of `quads`.

        A store that can hand out quads and not take them was only half a store: a reader
        copying one graph into another had to reach past this class for the other half, which
        is what let a variant store grow by inheriting the whole of one. Text is not the road
        (`quads` says why): a serialise-and-reparse relabels blank nodes.

        `forget=False` says the caller KNOWS this write cannot change which graphs are public,
        which are the agent's own, or anything `remember` holds — a world written into an
        imaginarium, whose graphs are classified as nothing and hold during no period. It is an
        assertion, not a hint: wrong, it leaves a stale answer standing, and a stale answer here
        is an EMPTY RESULT rather than an error. Measured at 10% of a hanoi solve, which is why
        the escape exists at all rather than being refused on principle.
        """
        for quad in quads:
            self._store.add(quad)
        if forget:
            self._forget()

    def remove_quads(self, quads, *, forget: bool = True) -> None:
        """Take quads out, by term. The mirror of `add_quads`, and the same reason."""
        for quad in quads:
            self._store.remove(quad)
        if forget:
            self._forget()

    def quads_for_pattern(self, subject=None, predicate=None, obj=None, graph=None):
        """The quads matching a pattern, as terms — None for any. `graph` may be an IRI."""
        return self._store.quads_for_pattern(
            subject, predicate, obj,
            ox.NamedNode(graph) if isinstance(graph, str) else graph)

    def contains_graph(self, graph_iri: str) -> bool:
        """Whether the named graph EXISTS. `has_graph` asks whether anything is WRITTEN there,
        which is a different question: a graph forked and then emptied still exists."""
        return self._store.contains_named_graph(ox.NamedNode(graph_iri))

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

    def nodes_of(self, graph_iri: str) -> dict:
        """Everything one graph holds, as triples grouped by subject — the graph's NODES.

        A caller wanting whole nodes had to iterate quads and regroup them, which meant naming
        the store's triple type to do it. The grouping is the store's, and so is the type.
        """
        out: dict = {}
        for q in self.quads(graph_iri):
            out.setdefault(q.subject, []).append(ox.Triple(q.subject, q.predicate, q.object))
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
        rows = bindings(self.query(_DEFINITIONS_Q, self.graphs_of(PUBLIC)))
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
        public = self.graphs_of(PUBLIC)
        for r in bindings(self.query(
                "SELECT ?c ?s WHERE { ?c rdfs:subClassOf+ ?s . FILTER(isIRI(?s) && isIRI(?c)) }", public)):
            supers.setdefault(ox.NamedNode(r["c"]), set()).add(ox.NamedNode(r["s"]))
        keyed = {ox.NamedNode(r["c"]) for r in bindings(self.query(
            "SELECT DISTINCT ?c WHERE { ?c <http://example.org/orexis#keyedBy> ?p }", public))}
        return defs, supers, keyed

    def update(self, sparql: str, *, forget: bool = True) -> None:
        """Write. `forget=False` is the assertion `add_quads` documents: this write cannot
        change the store's shape, so what was learned by asking may stand."""
        self._store.update(sparql, prefixes=NAMESPACES)
        if forget:
            self._forget()
        for listener in list(self.__dict__.get("_listeners", ())):
            listener()

    def _forget(self) -> None:
        """Every write drops what was learned by asking: which graphs are public, which are
        the agent's own, and whatever `remember` holds. Dropping rather than working out
        whether the write mattered, because a stale answer here is an empty result rather
        than an error — the failure this design keeps having to guard against."""
        self._catalogue_index = None
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
