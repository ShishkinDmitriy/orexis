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

import re

import rdflib
from pyshacl import validate as shacl_validate

from assembly import loader

from orexis_agent_progression.store import Store


def _shapes_and_vocabulary() -> tuple[rdflib.Graph, rdflib.Graph]:
    """Every package's shapes, and the T-Box they are written against.

    The vocabulary goes into the DATA as well as being the inference source: shapes target
    capability FAMILIES ("anything that perceives"), and which family a capability belongs to
    is a fact stated in the vocabulary.
    """
    ontology, shapes = rdflib.Graph(), rdflib.Graph()
    for path in loader.ontology_files():
        ontology.parse(str(path), format="turtle")
    for path in loader.shapes_files():
        shapes.parse(str(path), format="turtle")
    return ontology, shapes


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
#  How pyshacl spells our severity in the text report, which is the only place this is read —
#  the verdict itself is decided on the results GRAPH.
#  Both spellings: a report renders the severity through whatever namespaces its shapes graph
#  carries, and a filter that knew only the short form failed silently the first time a graph
#  arrived without them. `tests/test_gap.py` fails if neither form matches any more.
#  A result begins at one of TWO headings: pySHACL writes "Constraint Violation in ..." for a
#  violation and "Validation Result in ..." for everything else. Knowing only the second put
#  every violation in the report's HEADER, where this dropped it along with the rest — the
#  filter hid exactly the results it exists to preserve, and four tests caught it.
_RESULT = re.compile(r"(?=(?:Constraint Violation|Validation Result) in )")
_SHOULD_BECOME_FORMS = ("Severity: ag:ShouldBecome",
                        "Severity: <http://example.org/orexis#ShouldBecome>")


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
    #  The shapes an agent HOLDS are shapes too (a-desire-is-a-shape). They arrive in the data
    #  because a derivation writes them there, and a validator reading only the files would see
    #  a want as inert triples — so anything in the data typed `sh:NodeShape` joins the shapes
    #  graph, and the severity decides which kind it is: a violation refuses, a want does not.
    #
    #  Only when nobody focused, though. A shape a desire compiles to reaches its readings
    #  through `sh:qualifiedValueShape`, and pySHACL answers those WRONG under `focus_nodes` —
    #  measured both ways round: the operating region returned nothing where a gap was plainly
    #  there, and the survival envelope fired on a plant merely dry. A focused caller is one
    #  agent asking about itself, and it gets its own held shapes in the second pass below,
    #  unfocused. So a data-borne shape is checked exactly once, and never under a focus filter.
    if not focus:
        held = rdflib.Graph()
        for shape in set(data.subjects(rdflib.RDF.type, _SH.NodeShape)):
            held += data.cbd(shape)      # the shape and everything hanging off it
        if held:
            shapes = shapes + held
    # advanced=True enables SPARQL-based targets, which is how a shape scopes itself to the
    # agents that composed its capability.
    _, results, report = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="none", advanced=True,
        **({"focus_nodes": [focus]} if focus else {}),
    )
    violated = _violated(results)
    #  The shapes that agent holds, unfocused, over no others: ownership is `ag:holds`, so
    #  every result is about the asker by construction — which is the guarantee the focus
    #  filter was supposed to give and, for these shapes, does not.
    if focus and (mine := _shapes_held_by(data, focus)):
        #  No `ont_graph`: the ontology is already inside `data`, and passing it twice only
        #  ever meant handing pySHACL a second chance to disagree with itself.
        _, own, own_report = shacl_validate(
            data, shacl_graph=mine, inference="none", advanced=True)
        violated = violated or _violated(own)
        report = report.strip() + "\n" + own_report.strip()
    return not violated, _without_wants(report)


def _without_wants(report: str) -> str:
    """Drop the `ag:ShouldBecome` results from what a person is shown.

    A want is a shape and an unmet want is a result, so once desires compiled to SHACL every
    report grew one block per property nobody has read yet — which at genesis is all of them.
    `orexis-validate` printed forty lines about a world it was accepting. The gap is not a
    finding about the world: it is the state of one, and `gap.rq` is where to ask for it.

    Violations and warnings stay, header and all. The count is rewritten so it agrees with
    what follows it, and a report left with nothing to say says so.
    """
    head, *blocks = _RESULT.split(report)
    if not blocks:
        return report.strip()
    kept = [b for b in blocks if not any(form in b for form in _SHOULD_BECOME_FORMS)]
    if not kept:
        return "Validation Report\nConforms: True"
    head = re.sub(r"Results \(\d+\):", f"Results ({len(kept)}):", head)
    return (head + "".join(kept)).strip()


def _violated(results: rdflib.Graph) -> bool:
    return any(results.value(r, _SH.resultSeverity) == _SH.Violation
               for r in results.subjects(rdflib.RDF.type, _SH.ValidationResult))


def _shapes_held_by(data: rdflib.Graph, agent_uri: str) -> rdflib.Graph:
    """The shapes this agent holds, with everything hanging off them.

    Ownership is `ag:holds`, so this asks the graph rather than trusting a filter: a shape an
    agent holds is a shape about that agent, which is the guarantee focus filtering was being
    used for and does not actually give.
    """
    held = rdflib.Graph()
    for thing in data.objects(rdflib.URIRef(agent_uri),
                              rdflib.URIRef("http://example.org/orexis#holds")):
        held += data.cbd(thing)
        #  A held DESIRE is a node carrying its shape (a-desire-states-its-own-measure), so
        #  the met-test is one `ag:metWhen` hop further and a cbd of the desire alone would
        #  hand pySHACL a graph with no actual shape in it — silently, which is how this
        #  file has been wrong before. The desire's own cbd stays in too: pySHACL ignores a
        #  node it does not recognise as a shape, and the measure text rides along unread.
        for shape in data.objects(thing,
                                  rdflib.URIRef("http://example.org/orexis#metWhen")):
            held += data.cbd(shape)
    #  A graph carved out of another keeps its spellings. pySHACL renders the report through
    #  the shapes graph's namespaces, so without this the second pass printed
    #  `<http://example.org/orexis#ShouldBecome>` where the first printed `ag:ShouldBecome` —
    #  one severity in two spellings, in one report, for no reason a reader could see.
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

