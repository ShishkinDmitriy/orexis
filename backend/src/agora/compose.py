"""agora-compose — write the compose file for a world, from the world.

  agora-compose society        -> deploy/compose.society.yml

The roster is not typed here and not typed by you: it is read from `genesis/<world>/world.ttl`,
the same file the belief base is seeded from. Adding an agent to the world and regenerating is
the whole of deploying one. This is the same move `agora-acl` already makes for the store's
access list — derived, never hand-maintained, because a second list is a second thing to drift.

**One container per agent, and that is not packaging taste.** On one filesystem every agent can
read every other agent's store credential out of `keys/fuseki/`, which makes the per-graph ACL
a convention rather than a boundary. Each service here mounts exactly one `.pw` file — its own
— so an agent cannot authenticate as anybody else even if its code tried. See
knowledge/decisions/belief-base-isolation.md.

**Ordering is expressed, not hoped for.** The `seed` service runs to completion first; every
agent waits on it (`service_completed_successfully`). An agent that started against an unseeded
store would fail on its first read, loudly but pointlessly.

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
from .seed import DEFAULT_WORLD, world_dir, worlds

log = logging.getLogger("compose")

REPO_ROOT = PROJECT_ROOT.parent
OUT_DIR = REPO_ROOT / "deploy"
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


def _service(agent_id: str, caps: set[str]) -> str:
    # Only an agent that actuates has any use for a signing key, so only that one is given
    # them. Mounting keys/ wholesale would hand every agent every other agent's store
    # credential, which is precisely the isolation this layout exists to provide.
    signing = ""
    if ACTUATION in caps:
        signing = ("\n      # it actuates, so it co-signs — the two keys and nothing else\n"
                   "      - ../keys/host.key:/app/keys/host.key:ro\n"
                   "      - ../keys/clearing.key:/app/keys/clearing.key:ro")
    return f"""
  agent-{agent_id}:
    image: {IMAGE}
    command: ["agora-agent"]
    environment:
      AGORA_AGENT_ID: "{agent_id}"
    env_file: [../.env]
    network_mode: host
    # Rootless podman maps YOUR uid into the container. Without this it lands on a subuid that
    # cannot read a 0600 credential owned by you, so the agent falls back to admin — silently
    # undoing the isolation. Map it onto the image's unprivileged user instead.
    userns_mode: "keep-id:uid=10001,gid=10001"
    restart: unless-stopped
    depends_on:
      seed:
        condition: service_completed_successfully
    volumes:
      # exactly one credential: its own. This is the isolation the ACL assumes.
      - ../keys/fuseki/{agent_id}.pw:/app/keys/fuseki/{agent_id}.pw:ro{signing}
      # the discovered trees, mounted so a code change needs a restart, not a rebuild
      - ../capabilities:/app/capabilities:ro
      - ../transports:/app/transports:ro
      - ../domain:/app/domain:ro
      - ../kernel:/app/kernel:ro
      - ../backend/src/agora:/app/backend/src/agora:ro
"""


def render(world: str) -> str:
    who = roster(world)
    if not who:
        raise SystemExit(f"agora-compose: world {world!r} declares no agents")

    services = "".join(_service(a, caps) for a, caps in who.items())
    return f"""# GENERATED by `agora-compose {world}` from genesis/{world}/world.ttl — do not edit.
#
# The roster is the ratified world. Add an agent there, regenerate, and it is deployed; there
# is no second list to keep in step. Run from this directory:
#
#   podman compose -f compose.{world}.yml up -d
#   podman compose -f compose.{world}.yml logs -f
#
# Infra (Fuseki, Influx, Grafana) lives in the repo-root docker-compose.yml and is not repeated
# here — bring it up first. The MQTT broker runs on the host; see infra/mosquitto/lan.conf.

name: agora-{world}

# podman-compose puts every service in one pod by default, and a pod cannot combine with the
# per-service user-namespace mapping below ("--userns and --pod cannot be set together"). The
# mapping is the thing that makes an agent able to read its own credential and nothing else, so
# the pod is what gives way. Ignored by docker compose, which does not create pods at all.
x-podman:
  in_pod: false

services:
  # Genesis. Runs to completion, then the agents start — an agent against an unseeded store
  # fails on its first read, loudly and pointlessly.
  seed:
    image: {IMAGE}
    command: ["agora-seed", "{world}"]
    env_file: [../.env]
    network_mode: host
    userns_mode: "keep-id:uid=10001,gid=10001"
    restart: "no"
    volumes:
      - ../genesis:/app/genesis:ro
      - ../capabilities:/app/capabilities:ro
      - ../transports:/app/transports:ro
      - ../domain:/app/domain:ro
      - ../kernel:/app/kernel:ro
      - ../backend/src/agora:/app/backend/src/agora:ro
{services}"""


def generate(world: str = DEFAULT_WORLD) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"compose.{world}.yml"
    out.write_text(render(world))
    who = roster(world)
    log.info("wrote %s", out.relative_to(REPO_ROOT))
    for agent_id, caps in who.items():
        short = ", ".join(sorted(c.rsplit("#", 1)[-1] for c in caps)) or "nothing"
        signs = "  +signing keys" if ACTUATION in caps else ""
        log.info("  agent-%-10s %s%s", agent_id, short, signs)

    missing = [a for a in who if not (REPO_ROOT / "keys" / "fuseki" / f"{a}.pw").exists()]
    if missing:
        # A bind mount of a path that does not exist becomes a DIRECTORY, and the agent then
        # falls back to admin — silently undoing the isolation this file exists to provide.
        log.warning("  ! no credential for %s — run `agora-acl %s` before starting, or the "
                    "mount becomes a directory and they connect as admin",
                    ", ".join(missing), world)
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
