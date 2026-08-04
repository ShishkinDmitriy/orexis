"""Generate the store's access control from the world — the ACL is derived, like everything else.

Who exists, and therefore who needs a credential and which graphs they may read, is stated in
`genesis/world.ttl`. Hand-maintaining a second list in a Fuseki config would be exactly the
drift this architecture removes, so the config is generated:

  agora-acl        writes infra/fuseki/config.ttl and keys/fuseki/*

It authorises EVERY world in genesis/ at once, because the config defines one isolated dataset
per world (`/ds-<world>`). Re-run it after adding a world or an agent, and restart Fuseki.

Two doors over one store, because Jena's data access control is **read-only**:

  /ds/sparql     secured. Each agent authenticates as itself and can read the world, the
                 ontology, the sensed graph, and its OWN beliefs. Another agent's beliefs
                 come back empty — not as an error, as absence.
  /ds-rw         the plain store. `update` is open to every agent (each writes its own
                 readings), `data` and `sparql` are admin-only, for seeding and validation.

What this does and does not buy: **reads are enforced**, so privacy stops being a convention.
Writes are not graph-scoped — Jena cannot do that — so an agent could in principle write into
another's graph. That is the same integrity-of-self-report assumption trusted-agent mode
already accepts (see knowledge/decisions/trusted-agent-mode.md); the gap that was open was
*reading*, and this closes it.

See knowledge/decisions/belief-base-isolation.md.
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

import rdflib

from .config import PROJECT_ROOT
from .ontology import AG, ONTOLOGY_GRAPH, SENSED_GRAPH, WORLD_GRAPH, beliefs_graph
from .seed import world_dir, worlds

log = logging.getLogger("acl")

REPO_ROOT = PROJECT_ROOT.parent
CONFIG_OUT = REPO_ROOT / "infra" / "fuseki" / "config.ttl"
SECRETS_DIR = REPO_ROOT / "keys" / "fuseki"  # gitignored, like the signing keys

# Everything an agent may read besides its own beliefs. All public by design.
SHARED_GRAPHS = (ONTOLOGY_GRAPH, WORLD_GRAPH, SENSED_GRAPH)


def agent_ids(world: str) -> list[str]:
    """Who exists, according to the world itself."""
    g = rdflib.Graph().parse(world_dir(world) / "world.ttl", format="turtle")
    q = f"SELECT ?id WHERE {{ ?a a <{AG}Agent> ; <{AG}localId> ?id }}"
    return sorted({str(row.id) for row in g.query(q)})


def read_or_make_secret(agent_id: str, secrets_dir: Path = SECRETS_DIR) -> str:
    """One credential per agent, kept next to the signing keys and never committed.

    Stable across regeneration: rotating every agent's password because a new plant was
    added would be a needless outage.
    """
    secrets_dir.mkdir(parents=True, exist_ok=True)
    path = secrets_dir / f"{agent_id}.pw"
    if path.exists():
        return path.read_text().strip()
    secret = secrets.token_urlsafe(24)
    path.write_text(secret + "\n")
    path.chmod(0o600)
    return secret


def _world_block(world: str, ids: list[str]) -> tuple[str, str]:
    """One world's two services and its own store. Returns (service refs, the block).

    A dataset per world is the whole of multi-world support: a world IS a belief base, and
    `.env` already says the environment's only job is to name where the belief base is. So
    selecting a world is pointing at a different dataset — no graph is renamed, no agent
    learns anything new, and two worlds cannot overwrite each other because they share nothing.
    """
    entries = "\n".join(
        f'    access:entry [ access:user "{a}" ; access:graphs (\n'
        + "".join(f"        <{g}>\n" for g in (*SHARED_GRAPHS, beliefs_graph(a)))
        + "    ) ] ;"
        for a in ids
    ).rstrip(";") + "."
    updaters = " ".join(f'"{a}"' for a in ("admin", *ids))
    w = world
    block = f"""
#################  world: {w}  #################

<#secured-{w}> rdf:type fuseki:Service ;
    fuseki:name "ds-{w}" ;
    fuseki:endpoint [ fuseki:operation fuseki:query ; fuseki:name "sparql" ] ;
    fuseki:dataset <#access-{w}> .

<#plain-{w}> rdf:type fuseki:Service ;
    fuseki:name "ds-{w}-rw" ;
    fuseki:endpoint [ fuseki:operation fuseki:update ; fuseki:name "update" ;
                      fuseki:allowedUsers ( {updaters} ) ] ;
    fuseki:endpoint [ fuseki:operation fuseki:gsp-rw ; fuseki:name "data" ;
                      fuseki:allowedUsers ( "admin" ) ] ;
    fuseki:endpoint [ fuseki:operation fuseki:query ; fuseki:name "sparql" ;
                      fuseki:allowedUsers ( "admin" ) ] ;
    fuseki:dataset <#store-{w}> .

<#access-{w}> rdf:type access:AccessControlledDataset ;
    access:registry <#registry-{w}> ;
    access:dataset  <#store-{w}> .

<#store-{w}> rdf:type tdb2:DatasetTDB2 ;
    tdb2:location "/fuseki-data/tdb2-{w}" .

<#registry-{w}> rdf:type access:SecurityRegistry ;
{entries}
"""
    return f"<#secured-{w}> <#plain-{w}>", block


def build_config(worlds_and_ids: dict[str, list[str]], passwd_path: str) -> str:
    """The Fuseki assembler: one isolated store per world, each with two doors."""
    refs, blocks = [], []
    for world, ids in worlds_and_ids.items():
        ref, block = _world_block(world, ids)
        refs.append(ref)
        blocks.append(block)
    return f"""# GENERATED by `agora-acl` from genesis/*/world.ttl — do not edit by hand.
#
# Who may read what is derived from who exists in each world, so the two cannot drift apart.
# Regenerate after any change to the agents in any world.
#
# ONE ISOLATED STORE PER WORLD. A world is a belief base: seeding one cannot overwrite
# another, readings stay with the world they were observed in, and two worlds can be up at
# once. Selecting a world is pointing FUSEKI_URL at its dataset — nothing in the graphs or in
# any agent changes, because an agent is still told only its own id and where the store is.
#
# Two doors per world, because Jena's access control is read-only:
#   /ds-<world>     secured  — an agent sees the shared graphs and its own beliefs, nothing else
#   /ds-<world>-rw  plain    — update for every agent (its own readings), read/GSP for admin
#
# See knowledge/decisions/belief-base-isolation.md, knowledge/domain/world.md.

@prefix fuseki:  <http://jena.apache.org/fuseki#> .
@prefix ja:      <http://jena.hpl.hp.com/2005/11/Assembler#> .
@prefix access:  <http://jena.apache.org/access#> .
@prefix tdb2:    <http://jena.apache.org/2016/tdb#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix :        <#> .

[] rdf:type fuseki:Server ;
   fuseki:passwd "{passwd_path}" ;
   fuseki:services ( {" ".join(refs)} ) .
{"".join(blocks)}"""


def generate(admin_password: str = "admin") -> None:
    """Authorise EVERY world at once — the config is one file serving one dataset per world.

    Credentials are per agent *id*, not per world: `fern` in two worlds is the same principal
    with the same password, and it is the per-dataset registry that decides which beliefs it
    may read where. So adding a world never rotates anybody's password.
    """
    per_world = {w: agent_ids(w) for w in worlds()}
    per_world = {w: ids for w, ids in per_world.items() if ids}
    if not per_world:
        raise SystemExit("no worlds with agents in genesis/ — nothing to authorise")

    every_agent = sorted({a for ids in per_world.values() for a in ids})
    lines = [f"admin={admin_password}"]
    for agent_id in every_agent:
        lines.append(f"{agent_id}={read_or_make_secret(agent_id)}")
    passwd = SECRETS_DIR / "passwd"
    passwd.write_text("\n".join(lines) + "\n")
    passwd.chmod(0o600)

    CONFIG_OUT.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_OUT.write_text(build_config(per_world, "/fuseki-secrets/passwd"))

    for world, ids in per_world.items():
        log.info("  /ds-%-10s %d agent(s): %s", world, len(ids), ", ".join(ids))
    log.info("authorised %d agent(s) across %d world(s)", len(every_agent), len(per_world))
    log.info("  config      -> %s   (restart Fuseki to load it)", CONFIG_OUT)
    log.info("  credentials -> %s/  (gitignored; each agent reads its own)", SECRETS_DIR)


def main() -> None:
    import argparse
    import os

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argparse.ArgumentParser(
        prog="agora-acl",
        description="Generate the store's access control — one isolated dataset per world.",
    ).parse_args()
    generate(os.environ.get("FUSEKI_PASSWORD", "admin"))


if __name__ == "__main__":
    main()
