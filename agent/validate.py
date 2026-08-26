"""SHACL validation, in the two places it belongs.

The constitution is "checked by code, not persuasion", and the checks are **capability-aware**:
a shape applies to an agent only if that agent derived the capability it belongs to. An agent
that holds sensing:Subscribing with no sensor or no interval fails — before it fails at 3am.

Where each check lives follows from who owns the data:

- **an agent's own beliefs** are checked by that agent, at startup, and it refuses to run if
  they do not hold. The check sits where the data is, it happens *before the agent acts*
  rather than when an operator remembers to run a command, and refusing to start is not
  self-report — the consequence is not running, not a claim to be fine.
- **the ratified world** is checked centrally, against the files, because there is one world
  and it is public. That is the sovereign's check on their own authorship.

  orexis-validate [world]

See knowledge/decisions/where-the-belief-base-lives.md.
"""

from __future__ import annotations

import logging
import re

import rdflib
from pyshacl import validate as shacl_validate

from agent import genesis

from assembly import loader
from .ontology import STATE_GRAPH, beliefs_graph
from .store import Store

log = logging.getLogger("validate")


class BeliefsInvalid(RuntimeError):
    """An agent's beliefs do not satisfy the shapes of the capabilities it derived."""


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


# --- the agent's own check, at startup --------------------------------------------------------

def validate_agent(st: Store, agent_id: str, agent_uri: str, capabilities,
                   desires=None) -> None:
    """Hold ONE agent to the shapes of the capabilities it derived. Raises if it fails.

    Checked against its own store, which holds the world it booted with and its own beliefs —
    everything a capability-scoped shape needs, and nothing belonging to anyone else. Since
    #312 the wants are not in that store: the desire modality derives them, so a caller with
    one passes it and its quads join the data graph — sensing's `DesirerShape` demands a region and
    `AimShape` holds the aim to it, and both would fire falsely against a store that
    rightly no longer holds either. `None` stays legal for the world-level caller, which
    builds the modality itself per agent.
    """
    if not capabilities:
        return
    # Every public graph, flattened. pyshacl gets one graph and no reasoner, so anything the
    # vocabulary merely IMPLIES has to arrive already asserted — leave the entailed graphs out
    # and the shapes go quiet rather than failing, which is the worst way to be wrong. Passing
    # Asking the store which graphs are public, rather than naming them, means a sixth can never
    # be forgotten — and that nothing here has to know what the five happen to be called.
    #  INSTRUMENTS too, because the freshness want reads the horizon this agent published for
    #  its own sensors (#240). Leave it out and that shape binds nothing, fires never, and says
    #  so to no one — the silent direction to be wrong, which this file has met before.
    #  The pick record travels THROUGH the modality when one is given, never beside it: the
    #  flatten serialises and re-parses, which relabels blank nodes, so a record arriving by
    #  both roads splits every aim into two nodes — and AimShape rightly calls two aims for
    #  one property not steering.
    recorded = st.recorded_graphs()   # sensing's instruments graph, asked rather than named
    private = [STATE_GRAPH, *recorded] if desires is not None else \
        [beliefs_graph(agent_id), STATE_GRAPH, *recorded]
    data = graph_from(st, *st.public_graphs(), *private)
    if desires is not None:
        from agent import effects
        for triple in desires.construct(
                "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
            data.add(effects._triple(triple))
    ok, report = conforms(data, focus=agent_uri)
    if not ok:
        raise BeliefsInvalid(
            f"{agent_id} will not start: its beliefs do not satisfy the shapes for the "
            f"capabilities the world derived for it.\n{report}"
        )
    log.info("%s: beliefs satisfy the shapes for %d capability(ies)",
             agent_id, len(capabilities))


# `conforms` and `graph_from` are public because onboarding's world-wide check runs the same
# machinery over the same graphs. What is NOT here is that check itself: it is the sovereign's,
# runs before anything starts, and an agent has no use for it. See onboarding/validate.py.
