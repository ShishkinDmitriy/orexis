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
import sys

import rdflib
from pyshacl import validate as shacl_validate

from . import genesis, loader
from .ontology import SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
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


def _conforms(data: rdflib.Graph, focus: str | None = None) -> tuple[bool, str]:
    """Validate, optionally about ONE node only.

    `focus` matters for an agent checking itself. A capability shape targets every agent the
    world declares, but an agent holds only its own beliefs — so without it, fern would report
    tomato as missing a band it was never entitled to see. Scoping the focus asks the question
    the agent can actually answer: *am I* what my capabilities require me to be.
    """
    ontology, shapes = _shapes_and_vocabulary()
    data += ontology
    # advanced=True enables SPARQL-based targets, which is how a shape scopes itself to the
    # agents that composed its capability.
    conforms, _, report = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="rdfs", advanced=True,
        **({"focus_nodes": [focus]} if focus else {}),
    )
    return conforms, report.strip()


def _graph_from(st: Store, *graph_iris: str) -> rdflib.Graph:
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
    data = _graph_from(st, WORLD_GRAPH, beliefs_graph(agent_id), SENSED_GRAPH)
    conforms, report = _conforms(data, focus=agent_uri)
    if not conforms:
        raise BeliefsInvalid(
            f"{agent_id} will not start: its beliefs do not satisfy the shapes for the "
            f"capabilities the world derived for it.\n{report}"
        )
    log.info("%s: beliefs satisfy the shapes for %d capability(ies)",
             agent_id, len(capabilities))


# --- the sovereign's check, over the ratified files -------------------------------------------

def validate_world(world: str) -> bool:
    """Check a whole ratified world, from its files, without running anything.

    Builds exactly what an agent would build — the vocabulary, the world, the derivation and
    every agent's opening beliefs — and validates the lot. This is what genesis is checked
    with, and it needs no store, no server and no credentials.
    """
    path = genesis.world_dir(world)
    st = Store()  # in memory: built, read, thrown away
    genesis.refresh_public(st, path)

    everyone = [genesis.agent_id_of(p) for p in sorted(path.glob(genesis.BELIEFS_GLOB))]
    for agent_id in everyone:
        genesis.birth(st, path, agent_id)

    data = _graph_from(st, WORLD_GRAPH, *(beliefs_graph(a) for a in everyone))
    conforms, report = _conforms(data)
    print(report)

    for agent_id, caps in genesis.derived(st):
        marker = "" if agent_id in everyone else "   (no opening beliefs authored)"
        log.info("  %-10s %s%s", agent_id, caps, marker)
    return conforms


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-validate",
        description="Validate one ratified world and the opening beliefs it authors.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(genesis.worlds()))
    sys.exit(0 if validate_world(p.parse_args().world) else 1)


if __name__ == "__main__":
    main()
