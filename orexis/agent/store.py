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

**THE THIN ONES ARE ERGONOMIC, AND ONE OF THEM IS ONLY THAT.** `update` is
`store.update(text, prefixes=NAMESPACES)` and nothing else — it is why no query text in this
project carries a prefix header, and it saves nineteen call sites an import and an argument.
It does not save them from anything: measured, a text using `orexis:` without the dictionary
raises `SyntaxError` at the prefix, and so does a prefix the dictionary does not declare. The
hazard of a silently pre-bound prefix is rdflib's against a remote endpoint, not this engine's.

The others earn more than a line. `construct` is the prefixes PLUS building a default graph
out of a list of IRI STRINGS plus rendering substitutions as terms — three conversions a
caller would otherwise repeat. `query` is handed the kinds a reader means and never guesses.
`quads` and `clear_graph` wrap a string in a `NamedNode`; `add_quads` is a loop. A caller
hands strings and prefix-less SPARQL and gets terms and a dictionary built for it, which is
the contract.

What is NOT thin, and is what the module is actually for: `graphs_of` answers which graphs are
of a kind AT an instant, by asking the catalogue — 28 callers and the most-used function here;
`bind` fills `$tokens` and REFUSES a leftover; `classify` says what a graph is, guarding the
period against a blank node minted twice; `close_catalogue` materialises every kind a row is
beneath; `rdflib_view` crosses to the other engine. None of those is pyoxigraph's.
"""

from __future__ import annotations

import io
import logging
import re
import json
from datetime import datetime
from pathlib import Path
import pyoxigraph as ox

from .ontology import OREXIS

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

#  The header as TEXT, for the readers that parse rather than run: rdflib in `touches.py`,
#  and any tool that wants a query to stand alone. The store itself hands the engine
#  `NAMESPACES` as a dictionary (#500), so no query text carries a header it did not write.
PREFIXES = "\n" + "\n".join(
    f"PREFIX {label}: <{iri}>" for label, iri in sorted(NAMESPACES.items())
) + "\n"

DECLARED = frozenset(NAMESPACES)

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


def copy_graph(store, parent: str, name: str) -> str:
    """Everything `parent` holds, under `name` as well. The name, for chaining.

    THE COPY IS THE ENGINE'S, not a Python loop over quads. The loop cost 4.75 ms per fork on
    a 1,000-triple world against 3.29 ms this way, and 59 ms against 44 at 10,000 — a quarter,
    all of it the interpreter's overhead per quad rather than the store's. Blank node identity
    survives it, measured: a bnode matched in the WHERE is the same term when inserted, which
    matters because a held shape IS a blank node.

    Two callers fork a world this way — a search taking a step, and a boundary applying the
    predictions that begin at an instant — and what they do to the copy afterwards is their
    own. Here because it is the store's: copying a graph under another name says nothing
    about why.
    """
    update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                  f"WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}")
    return name


#  ── forking a graph ────────────────────────────────────────────────────────────────────────
#
#  Everything a parent holds under a new name, less what each retraction takes, plus what was
#  added — the world one change past another. THE ORDER IS THE WHOLE OF IT: copy, every
#  delete, then the adds, because a construct reuses the very node its retraction names, and
#  because the predictions beginning at one instant supersede in parallel. Two acts of the
#  planning package make a world out of the world before it — a candidate being taken, and the
#  boundary a prediction makes — and a primitive two acts share is the store's, not either's.
#  What is added goes in by TERM, never as text: a serialise-and-reparse relabels blank nodes.

#  `PREFIX name: <iri>` as SPARQL writes it, the empty name included.
_PREFIX_LINE = re.compile(r"^\s*PREFIX\s+([A-Za-z][\w.\-]*)?\s*:\s*<([^>]*)>[ \t]*\n?", re.I | re.M)


def fork(store, parent: str, name: str, added, retracts: list[str]) -> str:
    """`parent`'s facts under `name`, less what each retraction takes, plus `added`. The name.

    A RETRACTION THAT WILL NOT RUN RETRACTS NOTHING, LOUDLY. A text the engine refuses would
    otherwise leave the old value standing beside the new one, and a shape holding over every
    value would still see the old — the exact failure a retraction exists to close, arriving
    by another door. It is a package's bug and must not take an agent down; the copy is made
    on its own so that the fork exists either way.

    `retracts` are UPDATE texts already bound, because what `$state` means is the caller's:
    an action's retraction is bound to the world the step MAKES, a prediction's to the ground
    the boundary makes.
    """
    copy = f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}"
    try:
        for text in _joined(copy, *retracts):
            update(store, text)
    except Exception as exc:                                        # noqa: BLE001
        #  A JOINED TEXT FAILS WHOLE, so a retraction the engine refuses would take the copy
        #  with it and the fork would hold only the adds — a world missing everything it
        #  stood on, measured by `test_fork` the day the fallback was dropped. The copy is made
        #  on its own, then each retraction on its own, so the one that will not run is the
        #  only one that retracts nothing.
        logging.getLogger("store").error("a retraction would not run, so it retracts nothing: %s", exc)
        update(store, copy)
        for text in retracts:
            try:
                update(store, text)
            except Exception:                                       # noqa: BLE001
                pass
    add_quads(store, (ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(name))
                      for q in added))
    return name


def _joined(*texts: str) -> list[str]:
    """The update texts as ONE text where they can be, in order — their `PREFIX` lines hoisted
    to the head, since the engine takes a prologue only there and refuses one after a `;`,
    which is where a package's retraction carries its own. Measured: every retraction in a
    joined text was skipped with "expected one of CREATE, DELETE, INSERT", and every fork kept
    the reading it was meant to replace.

    Two texts spelling one name two ways cannot share a head, so they run apart — each with
    its own — which is the correct answer at the cost of the batch."""
    declared: dict[str, str] = {}
    bodies = []
    for text in texts:
        for label, iri in _PREFIX_LINE.findall(text):
            if declared.setdefault(label, iri) != iri:
                return [t for one in texts for t in _joined(one)] if len(texts) > 1 else [text]
        bodies.append(_PREFIX_LINE.sub("", text))
    head = "".join(f"PREFIX {label}: <{iri}>\n" for label, iri in declared.items())
    return [head + " ;\n".join(bodies)]


def forget_graph(store, graph_iri: str) -> None:
    """Empty one graph AND take back everything the catalogue said of it.

    A row pointing at a graph that no longer exists is litter every reader asking by class
    would still be handed. Two acts because `clear_graph` has callers that mean to empty a
    graph they are about to refill, and this one means it is gone.

    THE PERIOD GOES WITH THE ROW. A graph's period is a BLANK NODE hanging off it, so taking
    `<graph> ?p ?o` alone leaves `_:b a dcterms:PeriodOfTime ; orexis:start …` standing with
    nothing pointing at it — litter that no reader asks for and nothing would ever remove. It
    costs one more clause and the alternative is a store that grows for ever.
    """
    clear_graph(store, graph_iri)
    catalogue = catalogue_of(store)
    if catalogue is not None:
        update(store, f"""
DELETE {{ GRAPH <{catalogue}> {{ <{graph_iri}> ?p ?o . ?period ?pp ?po }} }}
WHERE  {{ GRAPH <{catalogue}> {{ <{graph_iri}> ?p ?o .
          OPTIONAL {{ <{graph_iri}> dcterms:temporal ?period . ?period ?pp ?po }} }} }}""")


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

    **WHAT IT IS WORTH, MEASURED** on one pass over the plans case — a two-step plan, so the
    smallest search there is — alternated in one session against a memo that keeps nothing:
    13.9 ms against 19.9, and 67 queries against 103. Four keys, and the query counts are
    exact where the timings are within the bench's drift:

        ("dataset", at)          +24 queries forgotten   the graph list per instant
        ("rule", action)         +10                     an action's row
        ("candidates","actions") +2                      the templates the store declares
        ("shapes",)              +0, and 0.58 ms a call  an rdflib view — it SERIALISES
                                                         rather than asks, so a query
                                                         counter cannot see it at all

    Every one of them is a fact the SEARCH cannot change: the graphs at an instant, a rule
    text, the action templates, the shapes a want was minted with. What could change them is a
    write to public knowledge, and a pass makes none — which is why the lifetime is the pass's
    and `forget` exists for the one owner that does write.
    """

    __slots__ = ("_kept",)

    def __init__(self):
        self._kept: dict = {}

    def get(self, key, compute):
        if key not in self._kept:
            self._kept[key] = compute()
        return self._kept[key]

    def put(self, key, value) -> None:
        """Keep `value` under `key` — for an owner that has just computed what it would
        otherwise read back: the pass's mint counter, read once from the store and advanced
        per world made, where reading MAX over the catalogue per world cost a tenth of a
        search on the two-disk bench."""
        self._kept[key] = value

    def forget(self, *heads) -> None:
        """Drop everything — or, given the first elements of keys, only what is kept under
        them — for an owner that has just written what those answers were read off. The
        planning pass keeps its memo across the derivation and forgets the shapes and the
        selects compiled from them, since the derivation writes wants and nothing else the
        memo holds: the rule texts, the action templates and the graph lists per instant are
        as good after it as before."""
        if not heads:
            self._kept.clear()
            return
        for key in [k for k in self._kept if isinstance(k, tuple) and k and k[0] in heads]:
            del self._kept[key]

    def __len__(self) -> int:
        return len(self._kept)


def remember(memo: "Memo | None", key, compute):
    """`memo.get`, or just `compute()` where the caller kept no memo. The one door, so a
    caller passes its memo along without branching on whether it has one."""
    return compute() if memo is None else memo.get(key, compute)


