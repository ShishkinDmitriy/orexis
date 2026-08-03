"""A belief base in memory.

The genesis Turtle is loaded into an rdflib Dataset and queried with the *same* SPARQL the
production code sends to Fuseki — so these tests exercise the real queries against the real
ratified world, with no triplestore running. If a query and the world drift apart, the tests
notice.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import rdflib

from agora import store
from agora.config import PROJECT_ROOT
from agora.ontology import MODULE_FILES, ONTOLOGY_GRAPH, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
from agora.seed import agent_id_of

REPO_ROOT = PROJECT_ROOT.parent
GENESIS_DIR = REPO_ROOT / "genesis"
ONTOLOGY_DIR = REPO_ROOT / "ontology"
RULES_DIR = REPO_ROOT / "rules"
SHAPES_DIR = REPO_ROOT / "shapes"


def genesis_dataset(readings: dict[str, float] | None = None,
                    result_time: datetime | None = None) -> rdflib.Dataset:
    """The seeded belief base — including the DERIVATION step.

    The rules are applied exactly as `agora-seed` applies them, so tests see the capabilities
    the world actually implies rather than a hand-written list.
    """
    ds = rdflib.Dataset()
    for name in MODULE_FILES:
        ds.graph(rdflib.URIRef(ONTOLOGY_GRAPH)).parse(ONTOLOGY_DIR / f"{name}.ttl", format="turtle")
    ds.graph(rdflib.URIRef(WORLD_GRAPH)).parse(GENESIS_DIR / "world.ttl", format="turtle")
    for path in sorted(GENESIS_DIR.glob("beliefs-*.ttl")):
        graph = rdflib.URIRef(beliefs_graph(agent_id_of(path)))
        ds.graph(graph).parse(path, format="turtle")
    for rule in sorted(RULES_DIR.glob("*.ru")):
        ds.update(rule.read_text())

    if readings:
        ts = (result_time or datetime.now(timezone.utc)).isoformat()
        sensed = ds.graph(rdflib.URIRef(SENSED_GRAPH))
        sensed.parse(data="\n".join(
            f"""@prefix agora: <http://example.org/agora#> .
                @prefix sosa: <http://www.w3.org/ns/sosa/> .
                @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
                agora:obs_{pid} a sosa:Observation ;
                  sosa:hasFeatureOfInterest agora:{pid} ;
                  sosa:hasSimpleResult "{value}"^^xsd:decimal ;
                  sosa:resultTime "{ts}"^^xsd:dateTime ."""
            for pid, value in readings.items()
        ), format="turtle")
    return ds


def query_fn(ds: rdflib.Dataset):
    """A QueryFn over the in-memory dataset — prefixed exactly as Store.query prefixes."""

    def query(sparql: str) -> dict:
        return json.loads(ds.query(store.PREFIXES + sparql).serialize(format="json"))

    return query


@pytest.fixture
def query():
    return query_fn(genesis_dataset())


@pytest.fixture
def query_with_readings():
    """Build a query fn over the world plus the given fresh readings."""

    def build(readings, result_time=None):
        return query_fn(genesis_dataset(readings, result_time))

    return build
