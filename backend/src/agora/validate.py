"""SHACL validation of the belief base.

Pulls the world, each agent's beliefs, and the sensed graph from Fuseki and validates them
against every package's shapes (with the T-Box for type resolution). This is the
constitution's "checked by code, not persuasion", and because capabilities are declared, the
checks are capability-aware: a shape applies to an agent only if that agent composed the
capability it belongs to. An agent that claims ag:Subscribing with no sensor or no interval fails
here — before it fails at 3am. Exits non-zero on any violation.

  agora-validate [world]

Each world has its own isolated dataset, so this validates exactly one.
"""

from __future__ import annotations

import logging
import sys

import rdflib
from pyshacl import validate as shacl_validate

from . import config, loader, store
from .ontology import SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
from .seed import DEFAULT_WORLD, worlds
from .store import bindings

log = logging.getLogger("validate")

# Who has a beliefs graph is itself stated in the world — discovered, never listed here.
_AGENTS_Q = f"""
SELECT ?agentId WHERE {{ GRAPH <{WORLD_GRAPH}> {{ ?a a ag:Agent ; ag:localId ?agentId }} }}"""


def validate(world: str = DEFAULT_WORLD) -> bool:
    st = store.from_env(config.env, world=world)

    graphs = [WORLD_GRAPH, SENSED_GRAPH]
    graphs += [beliefs_graph(r["agentId"]) for r in bindings(st.query_all(_AGENTS_Q))]

    data = rdflib.Graph()
    for graph_iri in graphs:
        data.parse(data=st.get_graph(graph_iri), format="turtle")

    # The T-Box goes into the DATA as well as being the inference source: shapes target
    # capability families ("anything that perceives"), and which family a capability belongs
    # to is a fact stated in the vocabulary.
    ontology = rdflib.Graph()
    shapes = rdflib.Graph()
    for path in loader.ontology_files():
        ontology.parse(str(path), format="turtle")
    for path in loader.shapes_files():
        shapes.parse(str(path), format="turtle")

    # advanced=True enables SPARQL-based targets, which is how a shape scopes itself to the
    # agents that composed its capability.
    data += ontology
    conforms, _, report = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="rdfs", advanced=True
    )
    print(report.strip())
    return conforms


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-validate",
        description="Validate one world's belief base against every package's shapes.",
    )
    p.add_argument("world", nargs="?", default=DEFAULT_WORLD,
                   help=f"which world (default: {DEFAULT_WORLD}). Available: "
                        + ", ".join(worlds()))
    sys.exit(0 if validate(p.parse_args().world) else 1)


if __name__ == "__main__":
    main()
