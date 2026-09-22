"""Reading and writing a store, as functions handed the engine.

**A store is a `pyoxigraph.Store` and nothing is wrapped around it.** That is the whole
difference between this module and the `store.py` it succeeds, and it is the reason this
package exists rather than an edit to that one. Progression handed every caller a `Store`
class that owned the engine, cached the catalogue as a Python index, cached a class hierarchy
and cached whatever a caller asked it to remember — and then had to drop all four on every
write, because a wrapper cannot see a write it did not make. Handing the engine out
(`Store.engine`) dropped them too, which is how a function over the store came to be the
thing that made the wrapper forget.

So there is no class here. A reader is handed the engine and says what it is reading:

    rows(store, text, graphs_of(store, PUBLIC))

and every question the class answered as a method is answered here as a function of the same
name, taking the engine first. Nothing is kept between calls, so nothing can go stale.

**What is cached is cached by whoever owns the lifetime.** A rule text, a step template and
the domain's class definitions cost more to re-read than a pass can afford — measured at 140
ms per fork for the definitions alone — and they can change only by a write that a pass does
not make. That is a fact about the PASS, not about the store, so the pass owns the memo: a
`Memo` is made by the caller that knows how long its answers are good for and handed down.
A store that quietly remembered for you is exactly what this module does not do.

There is still no shared triplestore and the isolation is unchanged: one agent, one volume,
a file inside that agent's container and not a service on a network. See
knowledge/decisions/where-the-belief-base-lives.md and
knowledge/decisions/an-agent-is-four-things.md.
"""

from __future__ import annotations

import io
import re
import json
from datetime import datetime
from . import clock
from pathlib import Path
import pyoxigraph as ox

from .ontology import OREXIS, PUBLIC

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

#  EVERY NAMESPACE THIS TREE DECLARES, found by looking at the tree — never listed, and never
#  asked of anything outside it. `orexis/**/ontology.ttl` is where a word of ours is declared:
#  `orexis/agent/ontology.ttl` for the kernel's and `orexis/agent/planning/ontology.ttl` for
#  the layer's, and a subtree that arrives as its own distribution brings its own.
#
#  IT USED TO ASK A LOADER THAT SCANNED SOMEWHERE ELSE. The 1.0 assembly walks `packages/` and
#  merges whatever it finds there; this tree is not under it, so every query speaking
#  `planning:` or `execution:` would have read a prefix nobody declared — which pyoxigraph
#  refuses loudly, and which is the only reason this was noticed before the move landed.
#  Reading its own tree is also what makes the tree a thing that can be lifted whole.
#
#  ONE LABEL, ONE IRI, across every ontology there is, refused otherwise. It would be the
#  quietest possible bug — one package's query silently reading another's terms — and both
#  spellings are valid SPARQL, so no engine could report it.
#
#  `orexis:` IS DECLARED BY THE LAYERS RATHER THAN BY ITS OWN FILE, and that is a gap rather
#  than a design: `orexis/agent/` has no `.ttl`, because the one that sat there turned out to
#  declare twenty-seven `execution:` terms and not one `orexis:` one, and went to the layer
#  whose words they are. The kernel's own T-Box — what `orexis:WantGraph` IS, what it is
#  beneath — is not in this tree at all yet; it arrives with genesis, and until then a case
#  declares the axioms it needs. So the label survives here only because both layers' files
#  bind it in their own `@prefix` lines. True today, and nothing would say so if a layer
#  stopped.
_ROOT = Path(__file__).resolve().parents[2]
_ANY_PREFIX = re.compile(r"@prefix\s+([A-Za-z][\w.-]*):\s*<([^>]*)>")


def _declared() -> dict[str, str]:
    out: dict[str, str] = {}
    origin: dict[str, Path] = {}
    for path in sorted((_ROOT / "orexis").rglob("*.ttl")):
        for label, iri in _ANY_PREFIX.findall(path.read_text()):
            if (prior := out.get(label)) is not None and prior != iri:
                raise RuntimeError(
                    f"prefix {label!r} means <{prior}> in {origin[label]} and <{iri}> in "
                    f"{path}. One label, one namespace — a query cannot mean both.")
            out.setdefault(label, iri)
            origin.setdefault(label, path)
    return out


_FOUND = _declared()
for _label, _iri in _FOUND.items():
    if _KERNEL.get(_label, _iri) != _iri:
        raise RuntimeError(f"prefix {_label!r} is the kernel's, bound to <{_KERNEL[_label]}>, "
                           f"and an ontology binds it to <{_iri}>")

NAMESPACES = {**_FOUND, **_KERNEL}

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


#  --- reading the catalogue over the ENGINE ------------------------------------------------
#
#  What a function over the store asks, where there is no `Store` to ask. The derivation's three
#  functions are handed `pyoxigraph.Store` itself (judge-desires-then-derive-wants), so the
#  lookups the class above offers as methods are offered here as functions over the engine:
#  the same questions, the same catalogue, no wrapper and no policy. A reader still states the
#  kinds it reads and the instant it stands at (a-reader-states-the-kinds-it-reads); these add
#  nothing to that and hide nothing from it.

_XSD_DATETIME = ox.NamedNode(_XSD + "dateTime")

#  WHICH GRAPHS, asked of the catalogue in one text: those of any of the kinds named — every
#  row carries every kind its class is beneath, so no path is walked — the holder's or
#  nobody's where a holder is named, and holding at the instant where one is given. A record
#  is handed as it stands at the present whatever instant is asked about (#645), which is the
#  one thing the kind means.
_GRAPHS_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph .
    ?g a ?kind . FILTER(isIRI(?g)) VALUES ?kind { $kinds }
    $owned
    $holding } }
ORDER BY ?g"""

_OWNED = """OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder)"""

_HOLDING = """OPTIONAL { ?g dcterms:temporal ?period .
               OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
    BIND(IF(EXISTS { ?g a orexis:RecordGraph }, $now, $at) AS ?when)
    FILTER(!BOUND(?start) || ?when >= ?start) FILTER(!BOUND(?end) || ?when < ?end)"""


def instant(at: datetime) -> ox.Literal:
    """An instant as the term a query compares it as."""
    return ox.Literal(at.isoformat(), datatype=_XSD_DATETIME)


def catalogue_of(store) -> str | None:
    """The graph that describes every graph and itself — `Store.catalogue` as a function over
    the engine, and the same answer, asked rather than kept.

    The class caches it because nothing moves it and it is asked on every read; a function
    over the engine holds nothing, so a caller that asks in a loop should keep what it got.
    None for a store nobody has told anything to. Two is refused, as it is there: a store with
    two catalogues has two truths about what its graphs are.
    """
    found = sorted(str(row["g"].value) for row in store.query(_CATALOGUES, prefixes=NAMESPACES))
    if len(found) > 1:
        raise RuntimeError(f"two graphs describe themselves as the catalogue: {', '.join(found)}")
    return found[0] if found else None


def answer(store, sparql: str, graphs=(), **values) -> dict:
    """`sparql` read over `graphs` as its default graph, as SPARQL-JSON — `Store.query` as a
    function over the engine, with `$tokens` bound by the one binder. A text that names its
    own graphs is handed none, and reads them through its `GRAPH` clauses."""
    out = io.BytesIO()
    store.query(bind(sparql, **values) if values else sparql, prefixes=NAMESPACES,
                default_graph=[ox.NamedNode(g) for g in graphs]).serialize(
        output=out, format=ox.QueryResultsFormat.JSON)
    return json.loads(out.getvalue())


def rows(store, sparql: str, graphs=(), **values) -> list[dict]:
    """`answer`, flattened to {var: value-string} — what a reader wanting values takes. A
    reader that needs the TERMS a row holds takes `pyoxigraph`'s own `query` and reads the
    solutions, as the judging does to read a met-test's own terms."""
    return bindings(answer(store, sparql, graphs, **values))


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]



#  ── what the catalogue says ────────────────────────────────────────────────────────────────
#
#  Every one of these was a method on the class that held the engine, answered out of a Python
#  index it had read once and dropped on every write. They are SPARQL now, asked each time.
#  That is not a regression: the index existed because four separate texts each walked a
#  subclass path and carried the NOT EXISTS traps this file's history records, and the fix for
#  those was to write the closure onto every catalogue row (`entry` below). With the rows
#  closed, a membership question is a `VALUES ?kind` join and there is nothing left to cache.

_SUBCLASSES_Q = """
SELECT DISTINCT ?super WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }
  GRAPH ?vocabulary { $cls rdfs:subClassOf ?super . FILTER(isIRI(?super)) } }"""


def closed(store, graph_class: str) -> list[str]:
    """`graph_class` and every class the vocabulary puts it beneath, sorted.

    ONE `rdfs:subClassOf` STEP IS EVERY STEP: the closure is materialised into the store at
    genesis (one-graph-both-engines-read), so a class already carries each of its ancestors
    and nothing here walks a path. Where the vocabulary is absent — a bare store, a case
    written by hand — the answer is the class itself, which is what a row said before the
    rows were closed at all.
    """
    supers = {row["super"] for row in rows(store, bind(_SUBCLASSES_Q, cls=graph_class))}
    return sorted({graph_class} | supers)


def entry(store, graph: str, graph_class: str, arrival: str, owner: str | None = None,
          start: datetime | str | None = None, end: datetime | str | None = None) -> str:
    """What the catalogue says of a graph, as the `GRAPH … { … }` block a writer puts beside
    the graph's own in ONE update — so a graph and its description land together or not at
    all. The writer names nothing: the catalogue is found, never spelled."""
    catalogue = catalogue_of(store)
    if catalogue is None:
        raise RuntimeError("no graph describes itself as the catalogue — nothing has said what the graphs are")
    whose = f" ; orexis:beliefsOf <{owner}>" if owner else ""
    stamp = lambda t: t if isinstance(t, str) else t.isoformat()
    when = ""
    if start is not None or end is not None:
        bounds = "".join(f' ; orexis:{k} "{stamp(v)}"^^xsd:dateTime'
                         for k, v in (("start", start), ("end", end)) if v is not None)
        when = f" ; dcterms:temporal [ a dcterms:PeriodOfTime{bounds} ]"
    #  EVERY KIND THE GRAPH IS, on the row, so a text that joins the catalogue asks
    #  `?g a orexis:WantGraph` and walks no path across two graphs. This is what lets every
    #  read above be one query instead of an index.
    kinds = " , ".join(f"<{c}>" for c in closed(store, graph_class))
    return (f"GRAPH <{catalogue}> {{ <{graph}> a {kinds} ; orexis:arrivedBy <{arrival}>"
            f"{whose}{when} . }}")


def classify(store, graph: str, graph_class: str, arrival: str, owner: str | None = None,
             start: datetime | str | None = None, end: datetime | str | None = None) -> None:
    """Say what a graph IS, how it arrived, WHOSE it is and WHEN it holds — by its owner, when
    it creates the graph. A name is for eyes; every reader asks the catalogue.

    IDEMPOTENT, INCLUDING THE PERIOD, which it was not. A period is a blank node
    (`dcterms:temporal [ a dcterms:PeriodOfTime … ]`) and a blank node in an `INSERT DATA` is a
    NEW node every time, so saying this twice of one graph gave it two periods — and a reader
    joining through `dcterms:temporal` then saw every row twice. It did not show while every
    graph had one writer and one subject; it showed the day a graph came to be shared by
    everything in trouble over one stretch, as three wants in one graph read as nine.

    So the period is written only where the graph has none. Saying a DIFFERENT period of a
    graph that already has one is not an update and is not silently applied: a graph's stretch
    is fixed when it is created, and a writer that means another stretch means another graph.
    """
    block = entry(store, graph, graph_class, arrival, owner, start, end)
    if start is None and end is None:
        update(store, f"INSERT DATA {{ {block} }}")
        return
    catalogue = catalogue_of(store)
    update(store, f"""
INSERT {{ {block} }}
WHERE  {{ GRAPH <{catalogue}> {{ }}
          FILTER NOT EXISTS {{ GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal ?period }} }} }}""")


_ROWS_Q = """
SELECT ?g ?class WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?class . FILTER(isIRI(?g)) } }"""


def close_catalogue(store) -> None:
    """Say on every row each kind the vocabulary puts its class beneath — what `entry` writes
    on a new row, said again of every row there is: a volume written when a row said one
    class, a case written by hand. Idempotent, and a write like any other.

    What it makes true is the thing every read above depends on: a text that joins the
    catalogue asks `?g a orexis:WantGraph` and walks no subclass path to get an answer.
    """
    catalogue = catalogue_of(store)
    if catalogue is None:
        return
    held: dict = {}
    for row in rows(store, _ROWS_Q):
        held.setdefault(row["g"], set()).add(row["class"])
    lines = []
    for graph, classes in sorted(held.items()):
        kinds = sorted({k for c in classes for k in closed(store, c)})
        lines.append(f"  <{graph}> a {' , '.join(f'<{k}>' for k in kinds)} .")
    if lines:
        rows_ = "\n".join(lines)
        update(store, f"INSERT DATA {{ GRAPH <{catalogue}> {{\n{rows_} }} }}")


_PERIODS_Q = """
SELECT ?g ?start ?end WHERE {
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph .
    ?g dcterms:temporal ?period . FILTER(isIRI(?g))
    OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } } }"""


def periods(store) -> dict:
    """The period each graph holds during: IRI -> (start, end), either end None for open.
    A bound nobody can parse reads as open, for the reason `_instant` gives — a graph whose
    period cannot be read is not one to drop silently."""
    return {row["g"]: (_instant(row.get("start")), _instant(row.get("end")))
            for row in rows(store, _PERIODS_Q)}


_OUTDATED_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph .
    ?g dcterms:temporal/orexis:end ?end . FILTER(isIRI(?g)) FILTER(?end <= $when)
    FILTER NOT EXISTS { ?g a orexis:PublicGraph }
    $owned } }
ORDER BY ?g"""


def outdated(store, *, holder: str | None = None, at: datetime | None = None) -> list[str]:
    """Every graph whose period has ENDED by `at` — what a reader is already handed none of,
    and what one sweep drops (#645, a-root-holds-always-and-an-outdated-graph-is-dropped).
    Never a public graph: a period the world states is the world's to end. `holder` keeps it
    to that holder's and to what nobody owns, as every other read does."""
    return [row["g"] for row in rows(
        store, bind(_OUTDATED_Q, when=instant(at or clock.now()),
                    owned=Raw(bind(_OWNED, holder=holder) if holder is not None else "")))]


def drop_graph(store, graph: str) -> None:
    """Drop one graph whole — its triples and everything the catalogue says of it. One update,
    so a graph goes entire or not at all."""
    catalogue = catalogue_of(store)
    about = "" if catalogue is None else f"""
  GRAPH <{catalogue}> {{ <{graph}> ?cp ?co . }}
  GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }}"""
    union = "" if catalogue is None else f"""
  UNION {{ GRAPH <{catalogue}> {{ <{graph}> ?cp ?co }} }}
  UNION {{ GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }}"""
    update(store, f"""
DELETE {{
  GRAPH <{graph}> {{ ?s ?p ?o }}{about} }}
WHERE  {{
  {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}{union} }}""")


def graphs_of(store, *kinds: str, at: datetime | None = None,
              holder: str | None = None, now: datetime | None = None) -> list[str]:
    """Every graph the catalogue types under any of `kinds` — subclasses included, the rows
    having been closed when they were written — holding at `at` where an instant is given.

    THE ONE LOOKUP A READER TAKES, and it is ONE (a-reader-states-the-kinds-it-reads). The
    reader says which kinds it means and, if it stands at an instant, which; this answers with
    graphs and decides nothing else. No clock is read: a reader meaning *now* says so.

    It was two doors for a while — this and a `graphs_holding` taking its kinds as a sequence
    rather than varargs, which this delegated to — and a calling convention is not a reason
    for a second public name: half the readers took one and half the other, for one question.

    `holder` is the one thing the predecessor's wrapper knew and a function cannot: which
    agent's store this is. Passed, the answer is that holder's graphs and those nobody owns;
    omitted, every graph of the kinds — which is right for a store holding one agent's world,
    and is what makes rule 4 (one agent, one volume) structural rather than remembered.
    """
    text = bind(_GRAPHS_Q, kinds=Raw(" ".join(f"<{k}>" for k in kinds)),
                owned=Raw(bind(_OWNED, holder=holder) if holder is not None else ""),
                holding=Raw(bind(_HOLDING, at=instant(at), now=instant(now or at))
                            if at is not None else ""))
    return [str(row["g"].value) for row in store.query(text, prefixes=NAMESPACES)]


#  ── reading ────────────────────────────────────────────────────────────────────────────────


def query(store, sparql: str, graphs, substitutions: dict | None = None) -> dict:
    """Read `sparql` with `graphs` merged as its default graph, as SPARQL-JSON bindings.

    THE READER SAYS WHAT IT READS. `graphs` is the list the caller built — `graphs_of` the
    kinds it means at the instant it stands at, a graph it wrote and reads back by name, a
    possible world in the state's place — and nothing is added to it or taken from it. Every
    named graph stays reachable through a `GRAPH` clause, so a text may instead say for itself
    which graphs it reads and be handed no default at all.

    `answer` above is the same door for a caller binding `$tokens`; this one takes the
    engine's own substitutions, which reach only a variable the query projects at top level.
    """
    out = io.BytesIO()
    store.query(sparql, prefixes=NAMESPACES,
                default_graph=[ox.NamedNode(g) for g in graphs],
                substitutions=_terms(substitutions)).serialize(
        output=out, format=ox.QueryResultsFormat.JSON)
    return json.loads(out.getvalue())


def query_over(store, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
    """`query`, with the graphs as positional names — a writer reading what it wrote."""
    return query(store, sparql, graphs, substitutions)


def query_union(store, sparql: str, substitutions: dict | None = None) -> dict:
    """Read with the default graph as the union of EVERYTHING this store holds.

    For the sovereign's question channel and for a test reading a store back whole. Nothing in
    the kernel reads through it: a reader there says which kinds it means, and the union reads
    every sibling world and next hour's readings as the present."""
    out = io.BytesIO()
    store.query(sparql, prefixes=NAMESPACES, use_default_graph_as_union=True,
                substitutions=_terms(substitutions)).serialize(
        output=out, format=ox.QueryResultsFormat.JSON)
    return json.loads(out.getvalue())


def construct(store, sparql: str, graphs, substitutions: dict | None = None):
    """Run a CONSTRUCT over `graphs` as the default graph and hand back the triples, which are
    not written anywhere — the one thing `query` cannot do, since a CONSTRUCT has a graph and
    not bindings. What a lever would make true is computed and dropped."""
    return list(store.query(sparql, prefixes=NAMESPACES,
                            default_graph=[ox.NamedNode(g) for g in graphs],
                            substitutions=_terms(substitutions)))


def reader(store, *kinds: str, at: datetime | None = None, holder: str | None = None):
    """`query` over the graphs of `kinds` at `at`, as one callable — for a helper handed a way
    to ask rather than a store. The kinds are the caller's, stated where the callable is made.

    It resolves the graphs ONCE, when the callable is made, because that is what a caller
    standing at an instant means; a caller that must see a write it then makes asks again.
    """
    graphs = graphs_of(store, *kinds, at=at, holder=holder)
    return lambda sparql, substitutions=None: query(store, sparql, graphs, substitutions)


#  ── quads, by term rather than by text ─────────────────────────────────────────────────────
#
#  Text is not the way between two stores: a serialise-and-reparse relabels blank nodes, so an
#  observation node would come out the far side unequal to the one a retraction names.


def quads(store, graph_iri: str):
    """One graph's contents as QUADS, for a reader putting them somewhere else."""
    return store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri))


def quads_for_pattern(store, subject=None, predicate=None, obj=None, graph=None):
    """The quads matching a pattern, as terms — None for any. `graph` may be an IRI."""
    return store.quads_for_pattern(
        subject, predicate, obj, ox.NamedNode(graph) if isinstance(graph, str) else graph)


def add_quads(store, quads_) -> None:
    """Write quads straight in, as the TERMS they are — the writing half of `quads`."""
    for quad in quads_:
        store.add(quad)


def remove_quads(store, quads_) -> None:
    """Take quads out, by term. The mirror of `add_quads`."""
    for quad in quads_:
        store.remove(quad)


def copy_graphs(store, source, *graph_iris: str) -> None:
    """Copy whole graphs in from ANOTHER store, under their own names — the reader's half and
    the writer's half of one act, which every caller was otherwise pairing by hand."""
    add_quads(store, (quad for iri in graph_iris for quad in quads(source, iri)))


def nodes_of(store, graph_iri: str) -> dict:
    """Everything one graph holds, as triples grouped by subject — the graph's NODES."""
    out: dict = {}
    for q in quads(store, graph_iri):
        out.setdefault(q.subject, []).append(ox.Triple(q.subject, q.predicate, q.object))
    return out


def get_graph(store, graph_iri: str) -> str:
    """A graph's contents as Turtle, or empty if it does not exist yet. A graph nobody has
    written to is not an error."""
    out = io.BytesIO()
    store.dump(output=out, format=ox.RdfFormat.TURTLE, from_graph=ox.NamedNode(graph_iri))
    return out.getvalue().decode()


def rdflib_view(store, *graph_iris: str):
    """These graphs as ONE rdflib graph — the crossing out of the store, for a reader that
    walks RDF STRUCTURE rather than answers a query.

    There is exactly one thing that needs it and it needs it twice over: a SHAPE. Compiling one
    to a select walks it, and carving one out of a store means its blank-node closure
    (`cbd`) — and a shape is a structure of blank nodes, which this engine has quads for and no
    walker. So the store's own API cannot answer, and the graphs cross.

    N-TRIPLES AND NOT TURTLE, which is the whole reason this is one function and not two: it
    CONCATENATES, so several graphs join with no re-parse, and rdflib reads it in a fraction of
    Turtle's time (12 ms against 86 on 2,400 triples, because Turtle groups by subject and
    hunts for prefixes). A caller that crossed with Turtle was paying seven times over for a
    readability nobody was there to read.

    IT IS THE CALLER'S TO KEEP. Crossing is the expensive part — #711 measured the whole belief
    base parsed into rdflib at half a second for a closure of forty triples — so whoever knows
    how long the answer is good for holds it, exactly as with `Memo`. Nothing is cached here.
    """
    import rdflib
    out = rdflib.Graph()
    text = dump_nt(store, *graph_iris)
    if text.strip():
        out.parse(data=text, format="nt")
    return out


def dump_nt(store, *graph_iris: str) -> str:
    """Several graphs as ONE N-Triples text, written by the engine itself.

    N-Triples because it CONCATENATES — every line stands alone, so several graphs join with
    `+` and nothing is re-parsed to merge them — and because the writer is the cost at a
    border: rdflib spends 86 ms on 2,400 triples of Turtle where N-Triples takes 12."""
    out = io.BytesIO()
    for iri in graph_iris:
        store.dump(output=out, format=ox.RdfFormat.N_TRIPLES, from_graph=ox.NamedNode(iri))
    return out.getvalue().decode()


def contains_graph(store, graph_iri: str) -> bool:
    """Whether the named graph EXISTS — a graph forked and then emptied still does."""
    return store.contains_named_graph(ox.NamedNode(graph_iri))


def has_graph(store, graph_iri: str) -> bool:
    """Whether anything has been written here — how birth knows it already happened."""
    return any(store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri)))


def graph_names(store) -> list[str]:
    """Every named graph actually present, whatever anyone still declares."""
    return [str(g.value) for g in store.named_graphs()]


#  ── writing ────────────────────────────────────────────────────────────────────────────────


def update(store, sparql: str) -> None:
    """Write. There is no `forget=` here and nothing to forget: nothing between calls is kept,
    which is the whole point of this module. The predecessor's flag was an assertion by the
    caller that a write could not stale the wrapper's index, and a wrong one left an EMPTY
    RESULT rather than an error."""
    store.update(sparql, prefixes=NAMESPACES)


def clear_graph(store, graph_iri: str) -> None:
    """Empty one graph — for the computed ones, written by update rather than loaded."""
    store.remove_graph(ox.NamedNode(graph_iri))


def put_graph(store, graph_iri: str, ttl: str, dataset: bool = False) -> None:
    """Replace a graph with the given Turtle. Public knowledge only.

    `dataset=True` parses **TriG** — Turtle plus `GRAPH <iri> { … }` blocks — and EVERY graph
    the document names is replaced, not only the named one: loading is additive and a quad
    store keeps what nobody removes, so a ratification that dropped a desire would otherwise
    leave it readable for ever.
    """
    graph = ox.NamedNode(graph_iri)
    if dataset:
        parsed = ox.Store()
        parsed.load(ttl, format=ox.RdfFormat.TRIG)
        for named in parsed.named_graphs():
            store.remove_graph(named)
        store.remove_graph(graph)
        for quad in parsed:
            store.add(quad if not isinstance(quad.graph_name, ox.DefaultGraph)
                      else ox.Quad(quad.subject, quad.predicate, quad.object, graph))
    else:
        store.remove_graph(graph)
        store.load(ttl, format=ox.RdfFormat.TURTLE, to_graph=graph)


def endow_graph(store, graph_iri: str, ttl: str) -> list[str]:
    """Add whatever the Turtle authors that the graph has NEVER held. Touch nothing held.

    The amendment half of birth (#202): a belief the agent holds is the agent's, revisions
    included, so the unit of novelty is the TERM — a predicate the graph holds is skipped
    whole, whatever its value, and one it has never held arrives with its blank-node closure,
    since an aim is a structure and not a triple. Returns the terms added.
    """
    graph = ox.NamedNode(graph_iri)
    held = {q.predicate for q in store.quads_for_pattern(None, None, None, graph)}
    authored = list(ox.parse(ttl, format=ox.RdfFormat.TURTLE))
    by_subject: dict = {}
    for t in authored:
        by_subject.setdefault(t.subject, []).append(t)
    added: list[str] = []
    queue: list = []
    for t in authored:
        if isinstance(t.subject, ox.BlankNode) or t.predicate in held:
            continue            # a blank node is reached only through the pair that owns it
        queue.append(t)
        added.append(t.predicate.value)
    seen: set = set()
    i = 0
    while i < len(queue):
        t = queue[i]
        i += 1
        store.add(ox.Quad(t.subject, t.predicate, t.object, graph))
        if isinstance(t.object, ox.BlankNode) and t.object not in seen:
            seen.add(t.object)
            queue.extend(by_subject.get(t.object, []))
    return sorted(set(added))


def load_file(store, path: str | Path, graph_iri: str) -> None:
    """Read a ratified file straight into a graph, without going through a string."""
    store.load(path=str(path), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode(graph_iri))


def optimize(store) -> None:
    """Compact the store. Blocking, and worth it only when something says it is needed: the
    belief base is an LSM tree and every reading is a DELETE plus an INSERT, so the file grows
    while the triple count does not. Nothing reclaimed is data."""
    store.optimize()


#  ── the memo the CALLER owns ───────────────────────────────────────────────────────────────


class Memo:
    """What only a write can change, computed once and kept for as long as its OWNER says.

    The predecessor put this on the store (`Store.remember`) and dropped it on every write,
    which made the store a thing that quietly remembered for you and then quietly stopped.
    The lifetime was never the store's to know: a rule text, a step template and the domain's
    class definitions are good for exactly as long as the reader is not writing public
    knowledge, and what knows that is the PASS — so a pass makes one of these and hands it
    down to the effect door, the step door and the entailment.

    Handed None, every caller below simply computes. That is the honest default: a caller
    with no memo has not said how long an answer is good for, so it gets a fresh one.
    """

    __slots__ = ("_kept",)

    def __init__(self):
        self._kept: dict = {}

    def get(self, key, compute):
        if key not in self._kept:
            self._kept[key] = compute()
        return self._kept[key]

    def forget(self) -> None:
        """Drop everything — for an owner that has just written what its answers were read off."""
        self._kept.clear()

    def __len__(self) -> int:
        return len(self._kept)


def remember(memo: "Memo | None", key, compute):
    """`memo.get`, or just `compute()` where the caller kept no memo. The one door, so a
    caller passes its memo along without branching on whether it has one."""
    return compute() if memo is None else memo.get(key, compute)


def definitions(store, memo: Memo | None = None):
    """The domain's class definitions: class -> (the named classes it intersects, the values
    it pins, the ranges it holds a value to); the subclass closure; and which classes some
    package declared `orexis:keyedBy`.

    Read off public knowledge, and worth a memo: as one SPARQL question it cost 300 ms a call
    however narrowed, and a pass forks tens of worlds.
    """
    return remember(memo, ("definitions",), lambda: _read_definitions(store))


def _read_definitions(store):
    public = graphs_of(store, PUBLIC)
    defs: dict = {}
    for r in rows(store, _DEFINITIONS_Q, public):
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
    for r in rows(store, "SELECT ?c ?s WHERE { ?c rdfs:subClassOf+ ?s . FILTER(isIRI(?s) && isIRI(?c)) }", public):
        supers.setdefault(ox.NamedNode(r["c"]), set()).add(ox.NamedNode(r["s"]))
    keyed = {ox.NamedNode(r["c"]) for r in rows(
        store, "SELECT DISTINCT ?c WHERE { ?c <http://example.org/orexis#keyedBy> ?p }", public)}
    return defs, supers, keyed


def _nodes_in(store, graph_iri: str, of, among: str) -> list:
    """The nodes to ask about: those named, those a pattern picks out, or all of them."""
    if of and not among:
        return [_named(x) if isinstance(x, str) else x for x in of]
    if among:
        text = f"SELECT DISTINCT ?x WHERE {{ GRAPH <{graph_iri}> {{ {among} }} }}"
        return [r["x"] for r in store.query(text, prefixes=NAMESPACES,
                                            named_graphs=[ox.NamedNode(graph_iri)])]
    seen, graph = [], ox.NamedNode(graph_iri)
    for q in store.quads_for_pattern(None, _RDF_TYPE, None, graph):
        if q.subject not in seen:
            seen.append(q.subject)
    return seen


def entail(store, graph_iri: str, of=(), among: str = "", memo: Memo | None = None) -> list:
    """Assert in `graph_iri` what the vocabulary entails of the nodes there: membership under
    every class defined as an `owl:intersectionOf` a named class, `owl:hasValue` restrictions
    and a datatype restriction's facets — the second OWL construct materialised rather than
    reasoned about at read time. Deliberation is on triples and a number is not special: what
    a reading IS is decided inside the domain as classes and asserted here, where a step's
    precondition can then say it as a triple (#576).

    THE DEFINITIONS ARE READ AS DATA AND EVALUATED HERE, which is the same bargain the shape
    compiler strikes: the domain owns the declaration, the kernel owns how it is answered.
    `of` narrows to some NAMED nodes as rendered terms; `among` to the nodes a pattern picks
    out inside the graph, which is how a fork's observation is named, being a blank node no
    `VALUES` can reach. Returns the memberships asserted, as `(node, class)` term pairs, and
    asserts through the term API — a blank node written back as text is a new blank node.
    """
    graph = ox.NamedNode(graph_iri)
    nodes = _nodes_in(store, graph_iri, of, among)
    defs, supers, keyed = definitions(store, memo)
    out = []
    for node in nodes:
        values, types = {}, set()
        for q in store.quads_for_pattern(node, None, None, graph):
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
        #  AND THE FAMILIES (#579): every class the node is now typed with, closed upward, so
        #  a shape's `sh:class` reads what a reading IS without walking a subclass path.
        #  STOPPING AT A KEYED CLASS: a reading gains its bands' families and never what sits
        #  above `sosa:Observation`, which every reading has alike and which the signature
        #  would read as a fact.
        stop = {s for k in types & keyed for s in supers.get(k, ())} | (types & keyed)
        for cls in list(types):
            for sup in supers.get(cls, ()):
                if sup not in types and sup not in stop:
                    out.append((node, sup))
                    types.add(sup)
    for node, cls in out:
        store.add(ox.Quad(node, _RDF_TYPE, cls, graph))
    return out
