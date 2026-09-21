"""Holding a graph to the shapes every package declares — the one SHACL verdict.

THREE CALLERS AND ONE JUDGE. The search holds each candidate world to the shapes to score it
(`planner.py`, beside this file); an agent holds its own beliefs to them at boot
(`agent/validate.py`); the sovereign holds the ratified world to them at onboarding
(`onboarding/validate.py`). The verdict must be the same function in all three, or a world
would conform for the operator and fail for the agent — which is why it lived in one file
when everything was `agent/`. The layer split (#452) put it here, in deliberation, by the rule
that put `act.py` in progression: a thing goes to the lowest place its importers stand. The
search may not reach up into the container for it, and the container and the operator's
tools reach down into deliberation for everything else about a belief already.

It DECIDES nothing about an agent — it answers a question about a graph — and it holds no
shape of its own: the shapes are read off the loader, package by package, exactly as the
stores read the packages' namespaces.
"""

from __future__ import annotations

import functools

import rdflib

from assembly import loader

import io
import json
import re
from typing import NamedTuple

import pyoxigraph as ox
from pyrudof import (RDFFormat, ResultShaclValidationFormat, Rudof, RudofConfig, ShaclFormat,
                     ShaclValidationMode)

from orexis_agent_progression import violation
from orexis_agent_progression.store import DECLARATION, NAMESPACES, Store


@functools.cache
def _shapes_and_vocabulary() -> tuple[rdflib.Graph, rdflib.Graph]:
    """Every package's shapes, and the T-Box they are written against.

    The vocabulary goes into the DATA as well as being the inference source: shapes target
    capability FAMILIES ("anything that perceives"), and which family a capability belongs to
    is a fact stated in the vocabulary.

    CACHED, and safe to be: the files cannot change inside a process, every caller treats
    both graphs as read-only (`data += ontology` and `shapes + held` build new graphs), and
    the planner pays this on every candidate world it judges — measured at a quarter of what
    `conforms` cost before the cache.
    """
    ontology, shapes = rdflib.Graph(), rdflib.Graph()
    for path in loader.ontology_files():
        ontology.parse(str(path), format="turtle")
    for path in loader.shapes_files():
        shapes.parse(str(path), format="turtle")
    #  Both graphs carry the store's dictionary as SHACL declares it (#508): a `sh:select`
    #  in prefixed names resolves through `sh:prefixes orexis:`, and pySHACL — still the
    #  engine of two tests — looks the declaration up in whichever graph it was handed.
    for graph in (ontology, shapes):
        graph.parse(data=DECLARATION, format="turtle")
    return ontology, shapes


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_MET_WHEN = rdflib.URIRef("http://example.org/orexis#metWhen")


def conforms(data: rdflib.Graph, focus: str | None = None) -> tuple[bool, str]:
    """Validate, optionally about ONE node only. True means nothing was VIOLATED.

    `focus` matters for an agent checking itself. A capability shape targets every agent the
    world declares, but an agent holds only its own beliefs — so without it, fern would report
    tomato as missing a band it was never entitled to see. Scoping the focus asks the question
    the agent can actually answer: *am I* what my capabilities require me to be.

    **The severity split is ours, not SHACL's.** The spec defines conformance as *no results at
    all*, so pySHACL reports `conforms: False` for a `sh:Warning` exactly as it does for a
    violation — which makes writing a warning pointless: it stops the world from onboarding and
    the agent from starting, and the only thing `sh:Warning` changes is the word in the report.
    A rig that is legal but worth a second look has to be sayable, so violations decide the
    verdict here and everything else is printed and passed over.

    Nothing is hidden by this. The full report, warnings included, is what the caller prints.

    **`inference` is off, and that is the point rather than an economy.** It used to be `"rdfs"`,
    which let pyshacl entail what the vocabulary implies — and the runtime entailed nothing, so a
    world could satisfy a shape about a relationship the code would never observe. That is now
    asserted once, into the store, by `orexis/inference.py`, and the caller passes the graph that
    holds it. Two engines, one closure, and `tests/test_inference.py` fails if they ever diverge.

    The caller must therefore include the ONTOLOGY graph in `data`. Adding the files on top is
    harmless — the materialised graph is a superset of them — and it keeps this correct for a
    caller that has not been updated, which is worth more here than saving a union.
    """
    ontology, shapes = _shapes_and_vocabulary()
    data += ontology
    return _conforms(crossed(data), data, focus)   # once, however many verdicts share it


@functools.lru_cache(maxsize=8)
def legality_selects(focus: str) -> dict:
    """The packages' shapes about ONE agent, each compiled to the select whose rows are its
    violations (#548) — what the search holds a candidate world to, in the imaginarium, in
    place of the judge. Cached by focus: the files cannot change inside a process, and a
    planner is built per pass. The shapes the agent HOLDS are not here; they arrive in the
    data, are carved per pass by `held_shapes` and compiled beside these by the planner.
    A shape the compiler cannot say refuses at the first pass, never at the gates alone.
    """
    _, shapes = _shapes_and_vocabulary()
    return violation.report_selects(shapes, focus_node=rdflib.URIRef(focus))


def _conforms(border: str, data: rdflib.Graph, focus: str | None) -> tuple[bool, str]:
    _, shapes = _shapes_and_vocabulary()
    #  The shapes an agent HOLDS are shapes too (a-desire-is-a-shape). They arrive in the data
    #  because a derivation writes them there, and a validator reading only the files would see
    #  them as inert triples — so anything in the data typed `sh:NodeShape` joins the shapes
    #  graph, EXCEPT a want's met-test, which the metWhen linkage keeps out (#472): it carries
    #  no severity, so validated it would report at pySHACL's default, `sh:Violation`, and
    #  refuse a boot for a dry pot. Its state is the measure's job and the planner validates
    #  it directly. Of what joins, the severity decides: a violation refuses, a warning shows.
    #
    #  Only when nobody focused, though. A shape a desire compiles to reaches its readings
    #  through `sh:qualifiedValueShape`, and pySHACL answers those WRONG under `focus_nodes` —
    #  measured both ways round: the operating region returned nothing where a gap was plainly
    #  there, and the survival envelope fired on a plant merely dry. A focused caller is one
    #  agent asking about itself, and it gets its own held shapes in the second pass below,
    #  unfocused. So a data-borne shape is checked exactly once, and never under a focus filter.
    if not focus:
        held = rdflib.Graph()
        met = set(data.objects(None, _MET_WHEN))
        for shape in set(data.subjects(rdflib.RDF.type, _SH.NodeShape)) - met:
            held += data.cbd(shape)      # the shape and everything hanging off it
        if held:
            shapes = shapes + held
    #  The judge is rudof, through conformance.py — SPARQL-based targets resolved there, which is
    #  how a shape scopes itself to the agents that composed its capability. No ont_graph:
    #  the ontology is already inside `data`, and passing it twice only ever meant handing
    #  the previous engine a second chance to disagree with itself.
    #  CARVED FIRST, CROSSED AFTER. `cbd` recurses through blank nodes only, so a graph
    #  skolemized before the carve stops at the first property shape and drops its authored
    #  message — the verdict right, the report gutted. The two sides still agree because
    #  `judge` names a blank node after its own id on both.
    violated, report = _judged(border, shapes, focus=focus)
    #  The shapes that agent holds, unfocused, over no others: ownership is `orexis:holds`, so
    #  every result is about the asker by construction — which is the guarantee the focus
    #  filter was supposed to give and, for these shapes, did not under pySHACL (the
    #  qualifiedValueShape wrong answers the comment above records). The judge takes no focus
    #  at all, so the pass survives as a guarantee of aboutness rather than a bug shelter.
    if focus and (mine := held_shapes(data, focus)):
        own_violated, own_report = _judged(border, mine)
        violated = violated or own_violated
        report = report.strip() + "\n" + own_report.strip()
    return not violated, report.strip()


def _judged(data: str, shapes: rdflib.Graph, focus: str | None = None) -> tuple[bool, str]:
    """One shapes graph judged, and the VIOLATIONS among the results decide.

    There is no severity split here, and there nearly was. rudof looked at first as though it
    flattened every result to `sh:Violation`; measured properly it honours `sh:severity`
    exactly where pySHACL does, which is exactly where this repo's shapes declare it — DOWN on
    the property shape for a declarative constraint, UP on the node shape for a `sh:sparql`
    one ([a-desire-is-a-shape](knowledge/decisions/a-desire-is-a-shape.md) measured that rule
    into existence against the previous engine, and the new one obeys the same one). The
    engines agree, so the verdict is what it always was: a result at `sh:Violation` refuses,
    anything softer is printed and passed over.

    With `focus`, only results ABOUT that node decide — the same set pySHACL's `focus_nodes`
    pre-filter produced, filtered after instead of before.
    """
    results, report = judge(data, shapes)
    violated = any(
        results.value(r, _SH.resultSeverity) == _SH.Violation
        and (focus is None or str(results.value(r, _SH.focusNode)) == focus)
        for r in results.subjects(rdflib.RDF.type, _SH.ValidationResult))
    return violated, report


def held_shapes(data: rdflib.Graph, agent_uri: str) -> rdflib.Graph:
    """The shapes this agent holds, with everything hanging off them.

    Ownership is `orexis:holds`, so this asks the graph rather than trusting a filter: a shape an
    agent holds is a shape about that agent, which is the guarantee focus filtering was being
    used for and does not actually give.
    """
    held = rdflib.Graph()
    for thing in data.objects(rdflib.URIRef(agent_uri),
                              rdflib.URIRef("http://example.org/orexis#holds")):
        held += data.cbd(thing)
        #  The `orexis:metWhen` hop is deliberately NOT taken since #472: a want's met-test is
        #  the planner's to validate and carries no severity, so walking to it here would
        #  report every unmet want at pySHACL's default severity and refuse the boot this
        #  check exists to allow. A held DESIRE contributes its own cbd — which pySHACL
        #  ignores, not being a shape — and a held bare shape (the envelope, an asserted
        #  root) contributes itself, force and all.
    #  A graph carved out of another keeps its spellings. pySHACL renders the report through
    #  the shapes graph's namespaces, so without this the second pass printed a severity as a
    #  full IRI where the first printed the prefixed form — one severity in two spellings, in
    #  one report, for no reason a reader could see.
    for prefix, namespace in data.namespaces():
        held.bind(prefix, namespace)
    return held


def graph_from(st: Store, *graph_iris: str) -> rdflib.Graph:
    data = rdflib.Graph()
    for iri in graph_iris:
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    return data

# --- THE ENGINE: one door to rudof ------------------------------------------------------
#
#  The judge in Rust — one door to rudof, with the two gaps it ships closed on our side.
#
#  pySHACL was the judge because it is the complete SHACL engine Python has, and it only speaks
#  rdflib — which is most of why rdflib survives in this kernel at all. rudof (pyrudof) is the
#  same verdict computed in Rust, and `knowledge/runbooks/measure-the-search.md` holds the
#  numbers and the criteria that let it in. Probed at 0.3.16, it evaluates every SHACL feature
#  these packages' shapes use — `sh:SPARQLConstraint` included — with exactly two gaps, and both
#  are closed HERE rather than worked around at each caller:
#
#  **Gap 1: `sh:SPARQLTarget` binds nothing, silently** — the empty-result trap in a new coat: a
#  shape family would simply stop applying and no test would go red on the engine's account. So
#  this module resolves SPARQL targets ITSELF, on our own engine, and hands rudof the explicit
#  `sh:targetNode`s. That is not a workaround so much as the house rule: a target select is a
#  query, and queries here run on pyoxigraph.
#
#  **Gap 2: a shape's `sh:severity` is ignored** — `sh:Warning` comes back `sh:Violation`. Not
#  closed here, because the CALLERS that care already split by severity before asking (the law
#  graph in `planner._violation_shapes` is Violation-only by construction; `conformance` splits
#  its shapes) and the callers that do not care are severity-blind on purpose. A result's
#  `sh:resultSeverity` from this judge is therefore NOT evidence of the shape's declared force —
#  read the shape, not the report, if force matters.
#
#  The door's shape is pySHACL's: (results graph, report text), so a caller swaps engines
#  without relearning what a verdict looks like. No `focus_nodes` — rudof has none, and the one
#  caller that scoped by focus now filters RESULTS by their `sh:focusNode`, which pySHACL's
#  pre-filter made equal anyway and without pySHACL's measured wrong answers for
#  `sh:qualifiedValueShape` under focus (see conformance.py, the second-pass comment).

_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


#  Where a blank node goes at the border. `urn:` because these names are private to one
#  crossing and must never be mistaken for anything a world declares.
_SKOLEM = "urn:orexis:blank:"

#  What a verdict says, as strings — the four things any hot caller reads off a result and
#  nothing a person would. `value` is the lexical form, or "" where the result states none.
VIOLATION = str(_SH.Violation)


class Verdict(NamedTuple):
    severity: str
    focus: str
    source: str
    value: str




def crossed(data: rdflib.Graph) -> str:
    """The data at the border, once: skolemized and serialized. A caller judging one world
    against several shapes graphs pays this ONE time — the first cut of this file crossed per
    verdict, and hanoi's solve measured the difference at once.

    SKOLEMIZED, and not as a nicety. rudof pre-binds a sh:sparql constraint's $this by
    injecting a VALUES clause, and a blank node is illegal in VALUES — so a shape whose
    target is blank (a held envelope in belief data) was a parse error, "expected UNDEF".
    And a SPARQL target RESOLVING to a blank could not cross the serialisation border as
    itself at all. Skolem IRIs survive both, and the verdict logic never compares them to
    anything but each other.

    DETERMINISTICALLY, which rdflib's own `skolemize` is not, and the difference is the whole
    reason this function exists. A caller carves its data-borne shapes out of the graph with
    `cbd`, and cbd recurses through BLANK nodes only — so skolemizing before the carve stops
    it at the first property shape and silently drops every nested constraint and its authored
    message. Both sides must therefore be skolemized SEPARATELY and agree, which they do here
    because a blank node's identity is its rdflib id: the same node names itself the same way
    in the data and in a graph carved out of it.
    """
    #  N-TRIPLES, not Turtle, and the reason is one-sided: rdflib's Turtle WRITER is the cost
    #  (85 ms against 12 ms for the same 2,400 triples, because it groups by subject and hunts
    #  for prefixes), while rudof's reader costs the same either way. The text is four times
    #  larger and nobody reads it.
    return _skolemized(data).serialize(format="nt")


#  A blank node stands at the start of a line (subject) or right after the predicate's `>`
#  (object) and nowhere else in N-Triples, which is what keeps a `_:` inside a literal as text.
_BLANK = re.compile(r"(?m)(?:^|(?<=> ))_:([A-Za-z0-9_.-]+)")


def crossed_text(nt: str) -> str:
    """A world already at the border as N-Triples — the store's own dump — skolemized the way
    `crossed` skolemizes a graph, by the same scheme and without a graph in between (#485).

    The planner holds every candidate world as text since #481, and the legality check used
    to parse it into rdflib to hand it to `conforms`, which serialised it straight back — a
    full circle costing more than the verdict. A blank node's label in the store's dump is
    its identity, so naming it after that label is deterministic within one crossing, which
    is all the judge needs: a blank focus node is legal in rudof's VALUES pre-binding, and
    no shape carries a data blank node by identity. Only a subject or object position is
    rewritten; a `_:` inside a literal is left as the text it is.
    """
    return _BLANK.sub(lambda m: f"<{_SKOLEM}{m.group(1)}>", nt)


def _carriers_named(shapes: rdflib.Graph) -> rdflib.Graph:
    """The same shapes with every blank CONSTRAINT CARRIER named — the objects of `sh:property`
    and `sh:sparql`, which are what a result cites as its source. Everything else keeps its
    blank nodes, path expressions and RDF lists above all, because their structure IS their
    meaning. A carrier is never itself part of a path, so the two sets do not meet."""
    carriers = {node for link in (_SH.property, _SH.sparql)
                for node in shapes.objects(None, link) if isinstance(node, rdflib.BNode)}
    if not carriers:
        return shapes
    named = rdflib.Graph()
    for prefix, ns in shapes.namespaces():
        named.bind(prefix, ns)
    for s, p, o in shapes:
        named.add((rdflib.URIRef(_SKOLEM + str(s)) if s in carriers else s, p,
                   rdflib.URIRef(_SKOLEM + str(o)) if o in carriers else o))
    return named


def _prose_restored(results: rdflib.Graph, shapes: rdflib.Graph) -> None:
    """Put the author's `sh:message` back where the engine wrote its own.

    rudof honours `sh:message` for most constraints and overrides it for some — a qualified
    max-count came back "QualifiedValueShape: 1 nodes conform to shape _:c4d3…, which is
    grater than maxCount: 0", where the shape said "SoilMoisture is below 0.2 — past what
    fern survives, not merely uncomfortable". The generated line is about the constraint; the
    authored one is about the plant, and a report is read by whoever has to act. So where the
    shape that produced a result states a message, that message IS the result's message.

    Correlation is by `sh:sourceShape`, which is why the shapes cross skolemized. A result
    whose source states nothing keeps whatever the engine said.
    """
    for result in results.subjects(rdflib.RDF.type, _SH.ValidationResult):
        source = results.value(result, _SH.sourceShape)
        if source is None:
            continue
        authored = list(shapes.objects(source, _SH.message))
        if not authored:
            continue
        results.remove((result, _SH.resultMessage, None))
        for message in authored:
            results.add((result, _SH.resultMessage, message))


def _skolemized(graph: rdflib.Graph) -> rdflib.Graph:
    """The same graph with every blank node replaced by a name derived from its own id."""
    out = rdflib.Graph()
    for prefix, ns in graph.namespaces():        # a carved graph keeps its spellings, and the
        out.bind(prefix, ns)                     # report is rendered through them
    for triple in graph:
        out.add(tuple(rdflib.URIRef(_SKOLEM + str(t)) if isinstance(t, rdflib.BNode) else t
                      for t in triple))
    return out


def judge(data: rdflib.Graph | str, shapes: rdflib.Graph) -> tuple[rdflib.Graph, str]:
    """One verdict: `data` held to `shapes`, targets resolved, report as a graph and as text.

    Serialisation is the border crossing, both ways — rdflib graph to Turtle for rudof, the
    report's Turtle back into an rdflib graph for the caller — and it is cheaper than it
    reads: the Turtle writer and rudof's parser are each a fraction of what pySHACL spent
    CLONING the same graphs before it would look at them. `data` as a STRING is a graph
    already crossed (`crossed` above); pass that when several verdicts share one world.
    """
    data_ttl = data if isinstance(data, str) else crossed(data)
    shapes_ttl, named = _resolved_ttl(shapes, data_ttl)
    r = Rudof(RudofConfig())
    r.read_data(data_ttl, format=RDFFormat.NTriples)
    r.read_shacl(shapes_ttl, format=ShaclFormat.Turtle)
    r.validate_shacl(mode=ShaclValidationMode.Native)
    report = r.serialize_shacl_validation_results(format=ResultShaclValidationFormat.Turtle)
    results = rdflib.Graph()
    results.parse(data=report, format="turtle")
    #  RENDERED THROUGH THE SHAPES' OWN PREFIXES. rudof's report binds `sh:` and nothing else,
    #  so a constraint about `sensing:monitors` printed a full IRI where every other report
    #  here prints the prefixed form — the difference a person reads, and one a test rightly
    #  greps for. The prose in `sh:resultMessage` is rudof's or the author's: it honours
    #  `sh:message` where a shape states one, and generates its own where none is stated.
    for prefix, ns in shapes.namespaces():
        results.bind(prefix, ns)
    _prose_restored(results, named)
    #  The first line is the verdict in words, kept from the pySHACL era: callers print this
    #  for a person, and tests legitimately grep it. The Turtle below is the full report.
    conforms = (None, _SH.conforms, rdflib.Literal(True)) in results
    return results, f"Conforms: {conforms}\n" + results.serialize(format="turtle")


def verdicts(data: str, *shapes: rdflib.Graph) -> list[frozenset]:
    """One world at the border, judged by several shapes graphs, each answered as a set of
    `Verdict`s — and no rdflib graph on the way. Built as the search's door (#547); since
    #548 the search reads compiled selects instead, and this is the ORACLE those selects
    are held to by parity (`tests/test_legality.py`), the way the inference closure is held
    to pyshacl. It stays exactly what the gates compute, so the parity means something.

    READ ONCE. rudof's `read_data` costs a fixed ~75 ms before it has looked at a triple
    (measured on two triples and on 3,500 alike), and it keeps its data across `reset_shacl`,
    so a caller with two shapes graphs to hold the same world to pays that floor once instead
    of twice. It drops its shapes on `reset_data`, so the other way round — one shapes graph
    held over many worlds — is not available, and each world is a fresh read.

    THE REPORT IS READ BY THE STORE'S OWN PARSER, as N-Triples: a result is a dozen triples
    and the four a caller keys on are read straight off them. `judge` below still returns
    the full report as a graph and as text, with the author's prose restored, because the
    gates print it for a person; nothing on the search path reads a message.

    An empty shapes graph answers an empty set without troubling the engine, which refuses
    to validate with no shapes loaded.
    """
    r = Rudof(RudofConfig())
    r.read_data(data, format=RDFFormat.NTriples)
    out = []
    for i, graph in enumerate(shapes):
        if not graph:
            out.append(frozenset())
            continue
        shapes_ttl, _ = _resolved_ttl(graph, data)
        if i:
            r.reset_shacl()
            r.reset_validation_results()
        r.read_shacl(shapes_ttl, format=ShaclFormat.Turtle)
        r.validate_shacl(mode=ShaclValidationMode.Native)
        report = r.serialize_shacl_validation_results(format=ResultShaclValidationFormat.NTriples)
        out.append(_verdicts_in(report))
    return out


_RESULT = str(_SH.ValidationResult)
_FIELDS = {str(_SH.resultSeverity): "severity", str(_SH.focusNode): "focus",
           str(_SH.sourceShape): "source", str(_SH.value): "value"}


def _verdicts_in(report_nt: str) -> frozenset:
    """The `Verdict`s a report states, read off its N-Triples by pyoxigraph."""
    rows: dict = {}
    results = set()
    for quad in ox.parse(report_nt.encode(), ox.RdfFormat.N_TRIPLES):
        key = quad.subject.value
        if quad.predicate.value == _RDF_TYPE and quad.object.value == _RESULT:
            results.add(key)
        elif (field := _FIELDS.get(quad.predicate.value)) is not None:
            rows.setdefault(key, {})[field] = quad.object.value
    return frozenset(Verdict(row.get("severity", ""), row.get("focus", ""),
                             row.get("source", ""), row.get("value", ""))
                     for key, row in rows.items() if key in results)


_RDF_TYPE = str(rdflib.RDF.type)


def _resolved_ttl(shapes: rdflib.Graph, data_ttl: str) -> tuple[str, rdflib.Graph]:
    """The shapes at the border with every `sh:SPARQLTarget` made explicit — as Turtle, the
    shape text serialized ONCE per shapes graph and the resolved targets appended per world.

    The select runs against the DATA — that is what a SPARQL-based target means — on a
    pyoxigraph store of its own loaded from the text, which is the engine every other query
    here already answers to — handed the store's dictionary, exactly as `Store.query` hands
    it (#500, #508), so a select written in prefixed names runs here as it runs there. Only a
    NAMED target is kept: a blank one could not survive the border crossing, and nothing
    here mints one. The original `sh:target` node stays in the text: rudof ignores it, and
    removing it would make the crossing lie about what the author wrote. (A resolver over
    the imaginarium sat here between #547 and #548; the search now compiles the target into
    its own select and nothing else held a world to resolve against.)

    The split matters because the shape text is world-independent: a planner judging many
    candidate worlds against one shapes graph re-pays only the target selects and a string
    concatenation, not a serialization of every shape it has already crossed. Only a shape
    that is itself a blank node cannot take its targets by appended reference; none such
    carries a SPARQL target today, and one that did would fail loudly below rather than lose
    its targets.
    """
    base_ttl, targets, named = _prepared(shapes)   # skolemized there, as the data was
    if not targets:
        return base_ttl, named
    query = _over_text(data_ttl)
    additions = []
    for shape, select in targets:
        for row in query(select).get("results", {}).get("bindings", []):
            node = row.get("this", {})
            if node.get("type") == "uri":
                additions.append(f"<{shape}> <{_SH.targetNode}> <{node['value']}> .")
    return base_ttl + "\n" + "\n".join(additions), named


def _over_text(data_ttl: str):
    """A resolver over the text alone: the world loaded once into a store of its own."""
    store = ox.Store()
    store.load(data_ttl.encode(), format=ox.RdfFormat.N_TRIPLES)   # what `crossed` writes

    def query(select: str) -> dict:
        out = io.BytesIO()
        store.query(select, prefixes=NAMESPACES).serialize(
            output=out, format=ox.QueryResultsFormat.JSON)
        return json.loads(out.getvalue())
    return query


@functools.lru_cache(maxsize=8)
def _prepared(shapes: rdflib.Graph) -> tuple[str, tuple[tuple[str, str], ...]]:
    """One shapes graph made border-ready: its Turtle, and its SPARQL targets as
    (shape IRI, select) pairs. Cached by GRAPH IDENTITY — an rdflib graph hashes by identity,
    which is exactly right here: the cached file-shapes graphs are built once per process and
    never mutated, and a fresh per-call graph simply misses. A blank shape carries its targets
    fine, being named at the border like everything else."""
    #  Named where a name is needed and NOWHERE else, which is the whole of this line's
    #  design. A result points at its `sh:sourceShape`, and a blank one crosses back as a
    #  fresh anonymous node correlating with nothing — so the constraint carriers are named.
    #  Skolemizing the whole shapes graph is what a first cut did, and SHACL forbids it: a
    #  property PATH is a blank-node structure (`[ sh:inversePath … ]`, a sequence as an RDF
    #  list), so naming those turned every path into a plain IRI predicate matching nothing —
    #  fifty shapes reporting minCount violations against beliefs that were perfectly good.
    shapes = _carriers_named(shapes)
    targets = []
    for shape, target in shapes.subject_objects(_SH.target):
        if (target, rdflib.RDF.type, _SH.SPARQLTarget) in shapes:
            select = shapes.value(target, _SH.select)
            if select is None:
                continue
            targets.append((str(shape), str(select)))
    #  THE DICTIONARY TRAVELS WITH THE SHAPES. A constraint's `sh:prefixes orexis:` resolves
    #  only through `sh:declare` triples in the graph rudof is handed, and no shapes file
    #  carries them (store.DECLARATION says why) — so every crossing appends the one
    #  assembled declaration, whether the shapes came from files, from a carved belief or
    #  from a world's own law.
    return shapes.serialize(format="turtle") + "\n" + DECLARATION, tuple(targets), shapes
