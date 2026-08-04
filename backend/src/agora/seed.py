"""Genesis (v1, hand-authored): load one ratified world into the belief base.

  agora-seed society     the full example — plants, a market, a supplier, valves
  agora-seed sensing     the smallest one that produces a working agent

`genesis/<name>/` is one complete world, not a fragment: seeding it replaces the T-Box, the
world and every agent's beliefs. Which world is in the store is what decides what each agent
becomes, so the same flashed board is a bidder in one and a watcher in another.

The sovereign authors a world directly in the vocabulary the agents read — Turtle — and this
just PUTs each file into its graph. No translation layer, one language end to end:

  */ontology.ttl                    -> :ontology          the T-Box, one file per package
  genesis/<w>/world.ttl             -> :world             hardware + wiring, public
  */rules.ru                        -> :world             DERIVES each agent's capabilities
  genesis/<w>/beliefs-<agent>.ttl   -> :beliefs/<agent>   that agent's private parameters

The packages are not listed anywhere: `agora.loader` finds them by looking, so seeding a
build that has gained a capability needs no edit here. See decisions/capability-packages.md.

The derivation step is what keeps abilities honest: the sovereign never writes down what an
agent can do, only what it is wired to. Capability follows from hardware and connections —
a scheduled sensor gives its agent an interval to state, a push-mode one does not — so the two
can never drift apart. Change the wiring, re-run genesis, and abilities follow.

Re-run after editing (bump agora:versionNumber in world.ttl on a structural change).

See knowledge/domain/world.md, knowledge/decisions/genesis.md,
knowledge/decisions/world-graph.md.
"""

from __future__ import annotations

import argparse
import logging
import re

from . import config, loader, store
from .config import PROJECT_ROOT
from .ontology import ONTOLOGY_GRAPH, WORLD_GRAPH, beliefs_graph
from .store import bindings

log = logging.getLogger("seed")

REPO_ROOT = PROJECT_ROOT.parent
GENESIS_ROOT = REPO_ROOT / "genesis"
DEFAULT_WORLD = "society"
BELIEFS_GLOB = "beliefs-*.ttl"


def agent_id_of(path) -> str:
    """`beliefs-fern.ttl` -> `fern` — the graph it belongs to."""
    return re.sub(r"^beliefs-|\.ttl$", "", path.name)


def worlds() -> list[str]:
    """Every ratified world on disk. Found by looking, like everything else."""
    return sorted(
        d.name for d in GENESIS_ROOT.iterdir()
        if d.is_dir() and (d / "world.ttl").exists()
    )


def world_dir(name: str):
    """One world, or a refusal that names the ones there are."""
    path = GENESIS_ROOT / name
    if not (path / "world.ttl").exists():
        raise SystemExit(
            f"agora-seed: no world called {name!r} in genesis/ — "
            f"there is {', '.join(worlds()) or 'nothing'}"
        )
    return path


def derive(st) -> None:
    """Run each module's derivation rules, materialising capabilities into the world.

    Rules are SPARQL updates so the derivation is stated in the same language as everything
    else, and live *inside* the package that owns the capability they grant. Re-running is
    safe: INSERT of a triple that is already there is a no-op.
    """
    for path in loader.rule_files():
        st.update(path.read_text())
    for row in bindings(st.query_all(_CAPABILITIES_Q)):
        log.info("derived %-9s -> %s", row["agentId"], row["caps"])


_CAPABILITIES_Q = f"""
SELECT ?agentId (GROUP_CONCAT(?cap; separator=", ") AS ?caps)
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent a ag:Agent ; ag:localId ?agentId ; ag:hasCapability ?c .
  BIND(REPLACE(STR(?c), "^.*#", "") AS ?cap)
}} }} GROUP BY ?agentId ORDER BY ?agentId"""


def seed(world: str = DEFAULT_WORLD) -> None:
    genesis = world_dir(world)
    st = store.from_env(config.env)

    # every package's vocabulary into one T-Box graph — separate files so each capability
    # owns its terms, but agents read one merged vocabulary
    t_box = "\n".join(path.read_text() for path in loader.ontology_files())
    st.put_graph(ONTOLOGY_GRAPH, t_box)
    log.info("loaded T-Box (%s) -> %s", loader.describe(), ONTOLOGY_GRAPH)

    st.put_graph(WORLD_GRAPH, (genesis / "world.ttl").read_text())
    log.info("seeded world %r (topology) -> %s", world, WORLD_GRAPH)

    derive(st)

    for path in sorted(genesis.glob(BELIEFS_GLOB)):
        agent_id = agent_id_of(path)
        graph = beliefs_graph(agent_id)
        st.put_graph(graph, path.read_text())
        log.info("seeded %-9s private beliefs -> %s", agent_id, graph)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-seed",
        description="Load one ratified world from genesis/ into the belief base.",
    )
    p.add_argument("world", nargs="?", default=DEFAULT_WORLD,
                   help=f"which world (default: {DEFAULT_WORLD}). Available: "
                        + ", ".join(worlds()))
    seed(p.parse_args().world)


if __name__ == "__main__":
    main()
