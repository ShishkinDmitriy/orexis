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

from orexis_agent_deliberation.judge import crossed, judge

from orexis_agent_progression.store import Store


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
    return ontology, shapes


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
#  The report filter that dropped want results (`_without_wants`) WAS HERE and is gone with
#  the severity it matched (#472): a want's met-test enters no validation pass at all — the
#  metWhen linkage below keeps it out — so there is nothing to hide from a person any more.
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
    #  The judge is rudof, through judge.py — SPARQL-based targets resolved there, which is
    #  how a shape scopes itself to the agents that composed its capability. No ont_graph:
    #  the ontology is already inside `data`, and passing it twice only ever meant handing
    #  the previous engine a second chance to disagree with itself.
    #  CARVED FIRST, CROSSED AFTER. `cbd` recurses through blank nodes only, so a graph
    #  skolemized before the carve stops at the first property shape and drops its authored
    #  message — the verdict right, the report gutted. The two sides still agree because
    #  `judge` names a blank node after its own id on both.
    border = crossed(data)                    # once, however many verdicts share it
    violated, report = _judged(border, shapes, focus=focus)
    #  The shapes that agent holds, unfocused, over no others: ownership is `orexis:holds`, so
    #  every result is about the asker by construction — which is the guarantee the focus
    #  filter was supposed to give and, for these shapes, did not under pySHACL (the
    #  qualifiedValueShape wrong answers the comment above records). The judge takes no focus
    #  at all, so the pass survives as a guarantee of aboutness rather than a bug shelter.
    if focus and (mine := _shapes_held_by(data, focus)):
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


def _shapes_held_by(data: rdflib.Graph, agent_uri: str) -> rdflib.Graph:
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

