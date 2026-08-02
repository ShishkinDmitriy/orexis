"""Genesis (v1, hand-authored): write the ratified world into the belief base.

Loads the shared T-Box and materializes the sovereign-authored *structure* — the world
version, topology (servedBy / suppliedBy), charters (targets), and the typed graph catalog —
into Fuseki. This is the "infra writes the ratified draft" step of genesis; agents read it,
never author it. Re-run (after bumping world_version + editing config) to re-seed.

  agora-seed

See knowledge/decisions/genesis.md.
"""

from __future__ import annotations

import logging

import requests

from . import config
from .config import PROJECT_ROOT
from .ontology import ATTESTED_GRAPH, ONTOLOGY_GRAPH, STRUCTURE_GRAPH

log = logging.getLogger("seed")

ONTOLOGY_TTL = PROJECT_ROOT.parent / "ontology" / "agora.ttl"


def _put_graph(data_url: str, graph_iri: str, ttl: str, auth) -> None:
    """Replace a named graph with the given Turtle (GSP PUT)."""
    resp = requests.put(
        data_url,
        params={"graph": graph_iri},
        data=ttl.encode("utf-8"),
        headers={"Content-Type": "text/turtle"},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()


def _local(uri: str) -> str:
    return uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def build_structure_ttl(cfg: dict) -> str:
    """Turtle for the sovereign-authored structure graph, from config."""
    v = int(cfg.get("world_version", 1))
    sup = cfg["supplier"]
    lines = [
        "@prefix agora: <http://example.org/agora#> .",
        "",
        "# world + current version",
        f"agora:world a agora:World ; agora:currentVersion agora:version_{v} .",
        f"agora:version_{v} a agora:WorldVersion ; agora:versionNumber {v} .",
        "",
        "# typed graph catalog (graphs are resources, not magic strings)",
        f"<{ONTOLOGY_GRAPH}> a agora:OntologyGraph .",
        f"<{STRUCTURE_GRAPH}> a agora:StructureGraph .",
        f"<{ATTESTED_GRAPH}> a agora:AttestedGraph ; agora:witness agora:gateway .",
        "",
        "# supplier + sources (topology)",
        f"agora:{sup['id']} a agora:Supplier .",
    ]
    for s in cfg.get("sources", []):
        lines.append(f"agora:{s['id']} a agora:WaterSource ; agora:suppliedBy agora:{s['supplier']} .")
    lines.append("")
    lines.append("# plants: charter desire + which source waters them")
    for p in cfg["plants"]:
        lines.append(
            f"<{p['uri']}> a agora:Plant ; "
            f"agora:servedBy agora:{p['source']} ; "
            f"agora:hasTarget {p['target']} ; "
            f"agora:underWorldVersion {v} ."
        )
    return "\n".join(lines) + "\n"


def seed() -> None:
    cfg = config.load_plants()
    fuseki = config.env("FUSEKI_URL", "http://localhost:3030/ds")
    data_url = fuseki.rstrip("/") + "/data"
    auth = ("admin", config.env("FUSEKI_PASSWORD", "admin"))

    ontology_ttl = ONTOLOGY_TTL.read_text()
    _put_graph(data_url, ONTOLOGY_GRAPH, ontology_ttl, auth)
    log.info("loaded T-Box -> %s", ONTOLOGY_GRAPH)

    _put_graph(data_url, STRUCTURE_GRAPH, build_structure_ttl(cfg), auth)
    log.info(
        "seeded structure (world v%s, %d plants, %d source(s)) -> %s",
        cfg.get("world_version", 1), len(cfg["plants"]), len(cfg.get("sources", [])), STRUCTURE_GRAPH,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    seed()


if __name__ == "__main__":
    main()
