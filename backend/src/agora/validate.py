"""SHACL validation of the belief base.

Pulls the attested + structure graphs from Fuseki and validates them against
ontology/shapes.ttl (with the T-Box for type resolution). This is the constitution's
"checked by code, not persuasion" applied to the *shape* of the record: an attested
observation must be complete, gateway-signed, and world-versioned; the structure must be
well-formed. Exits non-zero on any violation.

  agora-validate
"""

from __future__ import annotations

import logging
import sys

import rdflib
import requests
from pyshacl import validate as shacl_validate

from . import config
from .config import PROJECT_ROOT
from .ontology import ATTESTED_GRAPH, STRUCTURE_GRAPH

log = logging.getLogger("validate")

ONT_DIR = PROJECT_ROOT.parent / "ontology"


def _fetch_graph(data_url: str, graph_iri: str) -> str:
    resp = requests.get(
        data_url,
        params={"graph": graph_iri},
        headers={"Accept": "text/turtle"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.text


def validate() -> bool:
    fuseki = config.env("FUSEKI_URL", "http://localhost:3030/ds")
    data_url = fuseki.rstrip("/") + "/data"

    data = rdflib.Graph()
    for graph_iri in (ATTESTED_GRAPH, STRUCTURE_GRAPH):
        data.parse(data=_fetch_graph(data_url, graph_iri), format="turtle")

    ontology = rdflib.Graph().parse(str(ONT_DIR / "agora.ttl"), format="turtle")
    shapes = rdflib.Graph().parse(str(ONT_DIR / "shapes.ttl"), format="turtle")

    conforms, _, report = shacl_validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="rdfs"
    )
    print(report.strip())
    return conforms


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(0 if validate() else 1)


if __name__ == "__main__":
    main()
