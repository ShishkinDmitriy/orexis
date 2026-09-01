"""The judge in Rust — one door to rudof, with the two gaps it ships closed on our side.

pySHACL was the judge because it is the complete SHACL engine Python has, and it only speaks
rdflib — which is most of why rdflib survives in this kernel at all. rudof (pyrudof) is the
same verdict computed in Rust, and `knowledge/runbooks/measure-the-search.md` holds the
numbers and the criteria that let it in. Probed at 0.3.16, it evaluates every SHACL feature
these packages' shapes use — `sh:SPARQLConstraint` included — with exactly two gaps, and both
are closed HERE rather than worked around at each caller:

**Gap 1: `sh:SPARQLTarget` binds nothing, silently** — the empty-result trap in a new coat: a
shape family would simply stop applying and no test would go red on the engine's account. So
this module resolves SPARQL targets ITSELF, on our own engine, and hands rudof the explicit
`sh:targetNode`s. That is not a workaround so much as the house rule: a target select is a
query, and queries here run on pyoxigraph.

**Gap 2: a shape's `sh:severity` is ignored** — `sh:Warning` comes back `sh:Violation`. Not
closed here, because the CALLERS that care already split by severity before asking (the law
graph in `planner._violation_shapes` is Violation-only by construction; `conformance` splits
its shapes) and the callers that do not care are severity-blind on purpose. A result's
`sh:resultSeverity` from this judge is therefore NOT evidence of the shape's declared force —
read the shape, not the report, if force matters.

The door's shape is pySHACL's: (results graph, report text), so a caller swaps engines
without relearning what a verdict looks like. No `focus_nodes` — rudof has none, and the one
caller that scoped by focus now filters RESULTS by their `sh:focusNode`, which pySHACL's
pre-filter made equal anyway and without pySHACL's measured wrong answers for
`sh:qualifiedValueShape` under focus (see conformance.py, the second-pass comment).
"""

from __future__ import annotations

import functools

import pyoxigraph as ox
import rdflib
from pyrudof import (RDFFormat, ResultShaclValidationFormat, Rudof, RudofConfig, ShaclFormat,
                     ShaclValidationMode)

_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


#  Where a blank node goes at the border. `urn:` because these names are private to one
#  crossing and must never be mistaken for anything a world declares.
_SKOLEM = "urn:orexis:blank:"


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
    return _skolemized(data).serialize(format="turtle")


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
    r.read_data(data_ttl, format=RDFFormat.Turtle)
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


def _resolved_ttl(shapes: rdflib.Graph, data_ttl: str) -> tuple[str, rdflib.Graph]:
    """The shapes at the border with every `sh:SPARQLTarget` made explicit — as Turtle, the
    shape text serialized ONCE per shapes graph and the resolved targets appended per world.

    The select runs against the DATA — that is what a SPARQL-based target means — on a
    pyoxigraph store of its own, which is the engine every other query here already answers
    to. The original `sh:target` node stays in the text: rudof ignores it, and removing it
    would make the crossing lie about what the author wrote. The selects these packages hold
    spell every IRI in full (no `sh:prefixes` anywhere in the tree, and the prefix discipline
    in `tests/test_store.py` keeps it that way), so the text runs as written.

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
    store = ox.Store()
    store.load(data_ttl.encode(), format=ox.RdfFormat.TURTLE)
    additions = []
    for shape, select in targets:
        for row in store.query(select):
            node = row["this"]
            if isinstance(node, ox.NamedNode):        # a blank target could not survive the
                additions.append(                     # border crossing; nothing here mints one
                    f"<{shape}> <{_SH.targetNode}> <{node.value}> .")
    return base_ttl + "\n" + "\n".join(additions), named


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
    return shapes.serialize(format="turtle"), tuple(targets), shapes
