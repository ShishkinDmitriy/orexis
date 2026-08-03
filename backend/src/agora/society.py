"""agora-up — bring the society to life from the world, one process per agent.

  agora-up          every agent the world declares
  agora-up fern     just one, by name

Nothing here is a list. It asks the **belief base** who exists — `?a a ag:Agent` — and starts
one `agora-agent` for each, handing it the single thing an agent process is ever told: its own
id. So the roster is the ratified world, and re-seeding a different world brings up a
different society with no edit here and no edit to any unit file.

That is the whole point of deriving capabilities. An agent is not written; it is **born from
the model** — the world says what it is wired to, genesis derives what it can therefore do,
and this starts a process that discovers both. Adding an agent is adding it to `world.ttl`.

**One OS process each, deliberately.** It would be less code to run them in threads, and that
would quietly destroy the property the design rests on: a process boundary is what makes one
agent unable to read another's beliefs, and it is why the auction had to become a protocol
rather than a calculation. Supervision must not be the thing that undoes it.

Contrast the firmware, which cannot work this way: a board is hardware and is flashed by hand.
What the world decides is what an *agent* is — which is why the same flashed board is a
watcher in one world and a bidder in another.

See knowledge/decisions/capability-packages.md, genesis/README.md.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys

from . import config, store
from .ontology import WORLD_GRAPH
from .store import bindings

log = logging.getLogger("society")

# Who exists, and what each turned out to be able to do. Both are facts of the world: the
# roster is stated, the capabilities are derived — so this is the census, not a plan.
_ROSTER_Q = f"""
SELECT ?agentId (GROUP_CONCAT(DISTINCT ?cap; separator=", ") AS ?caps)
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent a ag:Agent ; ag:localId ?agentId .
  OPTIONAL {{ ?agent ag:hasCapability ?c . BIND(REPLACE(STR(?c), "^.*#", "") AS ?cap) }}
}} }} GROUP BY ?agentId ORDER BY ?agentId"""


def roster(st) -> list[tuple[str, str]]:
    """Every agent the world declares, with what it was derived to be able to do."""
    return [(r["agentId"], r.get("caps") or "") for r in bindings(st.query_all(_ROSTER_Q))]


def spawn(agent_id: str) -> subprocess.Popen:
    """One agent, one process, told only its own id.

    The child inherits stdout/stderr rather than being piped: every agent already logs under
    its own name, so one terminal reads as the society talking, and nothing here has to invent
    a format or sit between an agent and its output.
    """
    return subprocess.Popen(
        [sys.executable, "-m", "agora.runtime"],
        env={**os.environ, "AGORA_AGENT_ID": agent_id},
    )


def run(only: str | None = None) -> int:
    st = store.from_env(config.env)
    try:
        everyone = roster(st)
    except Exception as exc:
        raise SystemExit(
            f"agora-up: cannot read the world ({exc}).\n"
            "  The roster IS the world, so it has to be seeded:\n"
            "    docker compose up -d && agora-seed society"
        )

    if not everyone:
        raise SystemExit("agora-up: the world declares no agents — has it been seeded?")
    if only:
        everyone = [(a, c) for a, c in everyone if a == only]
        if not everyone:
            raise SystemExit(f"agora-up: the world knows no agent {only!r}")

    children: dict[str, subprocess.Popen] = {}
    for agent_id, caps in everyone:
        if not caps:
            # Derivation gave it nothing, so there is nothing to run. Worth saying out loud:
            # it means the wiring implies no ability, which is almost always a genesis mistake.
            log.warning("%s has no derived capability — not starting it", agent_id)
            continue
        children[agent_id] = spawn(agent_id)
        log.info("born  %-10s %s", agent_id, caps)

    if not children:
        raise SystemExit("agora-up: nobody had a capability to run")
    log.info("%d agent(s) up — ^C to stop them all", len(children))

    stopping = False

    def stop(*_) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        log.info("stopping the society")
        for child in children.values():
            child.terminate()  # each agent shuts its own modules down on SIGTERM

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    failed = 0
    for agent_id, child in children.items():
        code = child.wait()
        # A clean stop is 0, or the signal we sent. Anything else is an agent that died.
        if code not in (0, -signal.SIGTERM) and not stopping:
            log.error("%s exited with %s", agent_id, code)
            failed += 1
            stop()
        elif code not in (0, -signal.SIGTERM):
            log.error("%s exited with %s", agent_id, code)
            failed += 1
    return 1 if failed else 0


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )
    p = argparse.ArgumentParser(
        prog="agora-up",
        description="Start one process per agent the seeded world declares.",
        epilog="The roster comes from the belief base, so `agora-seed <world>` is what "
               "decides who comes up.",
    )
    p.add_argument("agent", nargs="?", help="start only this one, by local id")
    sys.exit(run(p.parse_args().agent))


if __name__ == "__main__":
    main()
