"""agora-validate — hold a whole ratified world to every package's shapes, before anything runs.

  agora-validate society

**This is the sovereign's check, not an agent's.** An agent validates *itself* at boot and
refuses to start if its own beliefs do not hold — that is `agent.validate.validate_agent`, and it
belongs in the runtime because the consequence is not running. This one asks a different
question: does the world I just authored hold together *at all*, for every agent in it, before I
grant anything or start anything?

So it lives here. It runs before onboarding, and `agora-onboard` runs it first for a reason worth
stating: onboarding an inconsistent world mints real credentials for agents that will then fail
their own startup validation, and leaves them lying around.

It builds exactly what an agent would build — the vocabulary, the world, the derivation, and
every agent's opening beliefs — and needs no store, no server and no credentials to do it. The
machinery is `agent.validate`'s, shared with the agent's self-check, because two ways to decide
whether beliefs hold is one too many.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import logging
import sys

from agent import genesis
from agent.ontology import PROVENANCE_GRAPH, beliefs_graph
from agent.store import Store
from agent.validate import conforms, graph_from

log = logging.getLogger("validate")


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

    # Every public graph — asserted, derived and entailed — plus the meta-graph describing
    # them, so `ag:PublicGraphShape` can fire. This check runs UNFOCUSED, over the whole
    # world, which is the only place a shape about graphs could ever fire: an agent's own
    # startup check is focused on its own node and would skip it silently.
    data = graph_from(st, *st.public_graphs(), PROVENANCE_GRAPH,
                      *(beliefs_graph(a) for a in everyone))
    ok, report = conforms(data)
    print(report)

    for agent_id, caps in genesis.derived(st):
        marker = "" if agent_id in everyone else "   (no opening beliefs authored)"
        log.info("  %-10s %s%s", agent_id, caps, marker)
    return ok


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
