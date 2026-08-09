"""SHACL validation, in the two places it belongs.

The constitution is "checked by code, not persuasion", and the checks are **capability-aware**:
a shape applies to an agent only if that agent derived the capability it belongs to. An agent
that holds ag:Subscribing with no sensor or no interval fails — before it fails at 3am.

Where each check lives follows from who owns the data:

- **an agent's own beliefs** are checked by that agent, at startup, and it refuses to run if
  they do not hold. The check sits where the data is, it happens *before the agent acts*
  rather than when an operator remembers to run a command, and refusing to start is not
  self-report — the consequence is not running, not a claim to be fine.
- **the ratified world** is checked centrally, against the files, because there is one world
  and it is public. That is the sovereign's check on their own authorship.

  agora-validate [world]

See knowledge/decisions/where-the-belief-base-lives.md.
"""

from __future__ import annotations

import logging

import rdflib
from pyshacl import validate as shacl_validate

from . import genesis, loader
from .ontology import ONTOLOGY_GRAPH, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
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
    asserted once, into the store, by `agora/inference.py`, and the caller passes the graph that
    holds it. Two engines, one closure, and `tests/test_inference.py` fails if they ever diverge.

    The caller must therefore include the ONTOLOGY graph in `data`. Adding the files on top is
    harmless — the materialised graph is a superset of them — and it keeps this correct for a
    caller that has not been updated, which is worth more here than saving a union.
    """
    ontology, shapes = _shapes_and_vocabulary()
    data += ontology
    # advanced=True enables SPARQL-based targets, which is how a shape scopes itself to the
    # agents that composed its capability.
    _, results, report = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="none", advanced=True,
        **({"focus_nodes": [focus]} if focus else {}),
    )
    violated = any(
        results.value(result, _SH.resultSeverity) == _SH.Violation
        for result in results.subjects(rdflib.RDF.type, _SH.ValidationResult)
    )
    return not violated, report.strip()


def graph_from(st: Store, *graph_iris: str) -> rdflib.Graph:
    data = rdflib.Graph()
    for iri in graph_iris:
        ttl = st.get_graph(iri)
        if ttl.strip():
            data.parse(data=ttl, format="turtle")
    return data


# --- the agent's own check, at startup --------------------------------------------------------

def validate_agent(st: Store, agent_id: str, agent_uri: str, capabilities) -> None:
    """Hold ONE agent to the shapes of the capabilities it derived. Raises if it fails.

    Checked against its own store, which holds the world it booted with and its own beliefs —
    everything a capability-scoped shape needs, and nothing belonging to anyone else.
    """
    if not capabilities:
        return
    # ONTOLOGY first: it carries the entailments materialised at genesis, and a shape's
    # SPARQL asks about them literally. Leave it out and the shapes go quiet rather than
    # failing — see agora/inference.py.
    data = graph_from(st, ONTOLOGY_GRAPH, WORLD_GRAPH, beliefs_graph(agent_id), SENSED_GRAPH)
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
