"""agora-compose — write the compose file for a world, from the world.

  agora-compose society        -> world/society/compose.yaml

A world is self-contained: its topology, its agents' opening beliefs and the compose file that
runs it all live in one directory. The roster is not typed here and not typed by you: it is
read from `world/<name>/world.ttl`,
the same file the belief base is seeded from. Adding an agent to the world and regenerating is
the whole of deploying one. This is the same move `agora-acl` already makes for the store's
access list — derived, never hand-maintained, because a second list is a second thing to drift.

**One container per agent, and that is not packaging taste.** An agent's belief base is a file
inside its own container — nothing else can reach it, so isolation is structural rather than
enforced. There are no credentials to hand out and no access registry to keep in step, because
there is no shared store to be let into. See knowledge/decisions/where-the-belief-base-lives.md.

**There is nothing to seed, and no ordering to express.** An agent builds its own belief base
at boot from the world files mounted read-only beside it, runs the derivation itself, and is
born if it has never been. So a service can start whenever it likes and depends on nothing.

**`network_mode: host` is deliberate.** The world states the bus as `ag:brokerHost "localhost"`
because a channel name is meaningless without the broker it is on and every member must agree
on it. Put the agents on a bridge network and that stops being true for them while staying true
for the ESP32 — two names for one bus, which is exactly what stating it in the world prevents.
Host networking keeps one bus with one name.

See knowledge/domain/world.md.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import rdflib

from . import loader
from .config import PROJECT_ROOT
from .ontology import AG, ONTOLOGY_GRAPH, WORLD_GRAPH
from .genesis import DEFAULT_WORLD, world_dir, worlds

log = logging.getLogger("compose")

REPO_ROOT = PROJECT_ROOT.parent
IMAGE = "agora:local"

_ROSTER_Q = f"""
SELECT ?id ?cap WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  OPTIONAL {{ ?a <{AG}hasCapability> ?cap }}
}} }}"""

ACTUATION = AG + "Actuation"


def roster(world: str) -> dict[str, set[str]]:
    """Every agent and what it will be able to do — derived here exactly as seeding derives it.

    Read from Turtle and computed in memory, so this works before anything has been seeded,
    which it must: the compose file is what brings the seeder up in the first place. Running
    the real rules rather than guessing is what lets a service mount only what its agent needs
    — a container that never actuates never sees a signing key.
    """
    ds = rdflib.Dataset()
    for path in loader.ontology_files():
        ds.graph(rdflib.URIRef(ONTOLOGY_GRAPH)).parse(path, format="turtle")
    ds.graph(rdflib.URIRef(WORLD_GRAPH)).parse(world_dir(world) / "world.ttl", format="turtle")
    for rule in loader.rule_files():
        ds.update(rule.read_text())

    out: dict[str, set[str]] = {}
    for row in ds.query(_ROSTER_Q):
        out.setdefault(str(row.id), set())
        if row.cap:
            out[str(row.id)].add(str(row.cap))
    return dict(sorted(out.items()))


def agent_ids(world: str) -> list[str]:
    return list(roster(world))


def _service(agent_id: str, caps: set[str], world: str) -> str:
    # Only an agent that actuates has any use for a signing key, so only that one is given
    # them. Note the world is mounted FILE BY FILE rather than as a directory: mounting
    # world/<name>/ wholesale would hand every agent the signing keys and every other agent's
    # opening beliefs, neither of which it has any business reading.
    signing = ""
    if ACTUATION in caps:
        signing = ("\n      # it actuates, so it co-signs — these two keys and nothing else\n"
                   "      - ./secrets/host.key:/app/world/secrets/host.key:ro\n"
                   "      - ./secrets/clearing.key:/app/world/secrets/clearing.key:ro")
    return f"""
  agent-{agent_id}:
    image: {IMAGE}
    command: ["agora-agent"]
    environment:
      AGORA_AGENT_ID: "{agent_id}"
      # Where to keep its belief base. A named volume, because beliefs must survive a
      # restart — otherwise every start would be a partial re-birth.
      AGORA_STORE: "/app/state"
      # the ratified world, mounted below. The agent reads files, not a service.
      AGORA_WORLD_DIR: "/app/world"
    env_file: [../../infra/.env]
    network_mode: host
    # Rootless podman maps YOUR uid into the container; without this the agent lands on a
    # subuid that cannot write its own belief-base volume. Map it onto the image's user.
    userns_mode: "keep-id:uid=10001,gid=10001"
    restart: unless-stopped
    volumes:
      # its own belief base, and nobody else can name it
      - agora-{world}-{agent_id}:/app/state
      # the ratified world, at a fixed path — so the agent is told only its own id and never
      # learns that other worlds exist. Only the topology and ITS OWN opening beliefs: an
      # agent has no business reading what anyone else was authored to want.
      - ./world.ttl:/app/world/world.ttl:ro
      - ./beliefs/{agent_id}.ttl:/app/world/beliefs/{agent_id}.ttl:ro{signing}
      # the discovered trees, mounted so a code change needs a restart, not a rebuild
      - ../../capabilities:/app/capabilities:ro
      - ../../transports:/app/transports:ro
      - ../../domain:/app/domain:ro
      - ../../kernel:/app/kernel:ro
      - ../../backend/src/agora:/app/backend/src/agora:ro
"""


def render(world: str) -> str:
    who = roster(world)
    if not who:
        raise SystemExit(f"agora-compose: world {world!r} declares no agents")

    services = "".join(_service(a, caps, world) for a, caps in who.items())
    volumes = "".join(f"  agora-{world}-{a}:\n" for a in who)
    return f"""# GENERATED by `agora-compose {world}` from the world.ttl beside it — do not edit.
#
# The roster is the ratified world. Add an agent there, regenerate, and it is deployed; there
# is no second list to keep in step. Run from this directory:
#
#   cd world/{world} && podman compose up -d
#   cd world/{world} && podman compose logs -f
#
# `compose.yaml` is the Compose Specification's own filename, so no -f is needed.
#
# Infra (Influx, Grafana) lives in the repo-root infra/compose.yaml — bring it up first. The
# MQTT broker runs on the host; see infra/mosquitto/lan.conf. There is no triplestore.
#
# Every agent here holds its own belief base in its own volume, so bringing this world up
# cannot disturb another world, and adding a world restarts nothing. Two worlds may run at once
# — but only if their DEVICES differ, since two agents on one topic both ingest.

name: agora-{world}

# podman-compose puts every service in one pod by default, and a pod cannot combine with the
# per-service user-namespace mapping below ("--userns and --pod cannot be set together"). The
# mapping is the thing that makes an agent able to read its own credential and nothing else, so
# the pod is what gives way. Ignored by docker compose, which does not create pods at all.
x-podman:
  in_pod: false

services:
{services}
volumes:
{volumes}"""


def generate(world: str = DEFAULT_WORLD) -> Path:
    out = world_dir(world) / "compose.yaml"
    out.write_text(render(world))
    who = roster(world)
    log.info("wrote %s", out.relative_to(REPO_ROOT))
    for agent_id, caps in who.items():
        short = ", ".join(sorted(c.rsplit("#", 1)[-1] for c in caps)) or "nothing"
        signs = "  +signing keys" if ACTUATION in caps else ""
        log.info("  agent-%-10s %s%s", agent_id, short, signs)

    unborn = [a for a in who
              if not (world_dir(world) / "beliefs" / f"{a}.ttl").exists()]
    if unborn:
        # Declared by the world but never given opening beliefs. It will fail its own
        # startup validation, which is the right place to notice — but sooner is better.
        log.warning("  ! no opening beliefs authored for %s — it will refuse to start",
                    ", ".join(unborn))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-compose",
        description="Generate the compose file for a world, from that world's roster.",
    )
    p.add_argument("world", nargs="?", default=DEFAULT_WORLD,
                   help=f"which world (default: {DEFAULT_WORLD}). Available: "
                        + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
