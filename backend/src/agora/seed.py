"""Genesis (v1, hand-authored): load the ratified world into the belief base.

The sovereign authors the world directly in the vocabulary the agents read — Turtle, in
`genesis/` — and this just PUTs each file into its graph. No translation layer, one language
end to end:

  */ontology.ttl              -> :ontology          the T-Box, one file per package
  genesis/world.ttl           -> :world             hardware + wiring, public
  */rules.ru                  -> :world             DERIVES each agent's capabilities
  genesis/beliefs-<agent>.ttl -> :beliefs/<agent>   that agent's private parameters

The packages are not listed anywhere: `agora.loader` finds them by looking, so seeding a
build that has gained a capability needs no edit here. See decisions/capability-packages.md.

The derivation step is what keeps abilities honest: the sovereign never writes down what an
agent can do, only what it is wired to. Capability follows from hardware and connections —
a pull-mode sensor gives its agent a cadence to own, a push-mode one does not — so the two
can never drift apart. Change the wiring, re-run genesis, and abilities follow.

Re-run after editing (bump agora:versionNumber in world.ttl on a structural change).

  agora-seed

See knowledge/decisions/genesis.md, knowledge/decisions/world-graph.md.
"""

from __future__ import annotations

import logging
import re

from . import config, loader, store
from .config import PROJECT_ROOT
from .ontology import ONTOLOGY_GRAPH, WORLD_GRAPH, beliefs_graph
from .store import bindings

log = logging.getLogger("seed")

REPO_ROOT = PROJECT_ROOT.parent
GENESIS_DIR = REPO_ROOT / "genesis"
WORLD_TTL = GENESIS_DIR / "world.ttl"
BELIEFS_GLOB = "beliefs-*.ttl"


def agent_id_of(path) -> str:
    """`genesis/beliefs-fern.ttl` -> `fern` — the graph it belongs to."""
    return re.sub(r"^beliefs-|\.ttl$", "", path.name)


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


def seed() -> None:
    st = store.from_env(config.env)

    # every package's vocabulary into one T-Box graph — separate files so each capability
    # owns its terms, but agents read one merged vocabulary
    t_box = "\n".join(path.read_text() for path in loader.ontology_files())
    st.put_graph(ONTOLOGY_GRAPH, t_box)
    log.info("loaded T-Box (%s) -> %s", loader.describe(), ONTOLOGY_GRAPH)

    st.put_graph(WORLD_GRAPH, WORLD_TTL.read_text())
    log.info("seeded world (topology + capabilities) -> %s", WORLD_GRAPH)

    derive(st)

    for path in sorted(GENESIS_DIR.glob(BELIEFS_GLOB)):
        agent_id = agent_id_of(path)
        graph = beliefs_graph(agent_id)
        st.put_graph(graph, path.read_text())
        log.info("seeded %-9s private beliefs -> %s", agent_id, graph)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    seed()


if __name__ == "__main__":
    main()
