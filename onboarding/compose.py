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

from agent import ratified
from agent.config import REPO_ROOT
from agent.ontology import AG, WORLD_GRAPH
from agent import genesis
from agent.genesis import world_dir, worlds

log = logging.getLogger("compose")

IMAGE = "agora:local"

_ROSTER_Q = f"""
SELECT ?id ?cap WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  OPTIONAL {{ ?a <{AG}hasCapability> ?cap }}
}} }}"""

ACTUATION = AG + "Actuation"

_BUS_PORTS_Q = f"""
SELECT ?port ?tlsPort WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?bus a <{AG}MessageBus> ; <{AG}brokerPort> ?port .
  OPTIONAL {{ ?bus <{AG}brokerTlsPort> ?tlsPort }} }} }} LIMIT 1"""


def _bus_ports(world: str) -> tuple[int, int | None]:
    """The ports this world states. Two worlds are two brokers, so they must differ."""
    rows = ratified.rows(ratified.dataset(world), _BUS_PORTS_Q)
    if not rows:
        raise SystemExit(f"agora-compose: world {world!r} declares no ag:MessageBus")
    tls = rows[0].get("tlsPort")
    return int(rows[0]["port"]), int(tls) if tls else None


def roster(world: str) -> dict[str, set[str]]:
    """Every agent and what it will be able to do — derived here exactly as seeding derives it.

    Read from Turtle and computed in memory, so this works before anything has been seeded,
    which it must: the compose file is what brings the seeder up in the first place. Running
    the real rules rather than guessing is what lets a service mount only what its agent needs
    — a container that never actuates never sees a signing key.
    """
    out: dict[str, set[str]] = {}
    for row in ratified.rows(ratified.dataset(world), _ROSTER_Q):
        out.setdefault(row["id"], set())
        if row.get("cap"):
            out[row["id"]].add(row["cap"])
    return dict(sorted(out.items()))


def agent_ids(world: str) -> list[str]:
    return list(roster(world))


def _world_files(world: str) -> str:
    """Every Turtle the world is written in, mounted one by one.

    Still file by file rather than the directory: mounting `world/<name>/` wholesale would hand
    the agent the signing keys and every other agent's opening beliefs. A world is now several
    files — the society, the stand it runs on — and an agent needs all of them, because they are
    one graph to every query it makes.
    """
    return "\n".join(f"      - ./{p.name}:/app/world/{p.name}:ro"
                      for p in genesis.world_files(world_dir(world)))


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
    world_files = _world_files(world)
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
      # Where the three files mounted below live. The agent connects with the certificate when
      # the world states a TLS port and it holds one.
      MQTT_CERT: "/app/world/secrets/agent.crt"
      MQTT_KEY: "/app/world/secrets/agent.key"
      MQTT_CA: "/app/world/secrets/ca.crt"
    env_file:
      # where the series store is, and the org — safe for every agent to hold
      - ../../infra/.env
      # this agent's own bucket and a token that opens only it, and its own broker
      # credential. Minted by `agora-influx` and `agora-mqtt` from this world; mounted into
      # THIS container and no other, which is what makes the isolation structural rather
      # than a promise. Run both tools before `up`, or these files do not exist.
      - ./secrets/influx-{agent_id}.env
      - ./secrets/mqtt-{agent_id}.env
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
{world_files}
      - ./beliefs/{agent_id}.ttl:/app/world/beliefs/{agent_id}.ttl:ro
      # Its own certificate and nothing else — the same rule as the beliefs above. The private
      # key is the whole of its identity on the bus, so a neighbour's must be unreachable.
      # ca.crt is THIS WORLD'S authority — what it needs to verify its own broker. The same
      # authority vouches for both ends, which is what makes a world self-contained.
      - ./secrets/{agent_id}.crt:/app/world/secrets/agent.crt:ro
      - ./secrets/{agent_id}.key:/app/world/secrets/agent.key:ro
      - ./secrets/ca.crt:/app/world/secrets/ca.crt:ro{signing}
      # the discovered trees, mounted so a code change needs a restart, not a rebuild
      - ../../capabilities:/app/capabilities:ro
      - ../../transports:/app/transports:ro
      - ../../vocabulary:/app/vocabulary:ro
      - ../../agent:/app/agent:ro
"""


# Everything a stand-in needs, which is exactly what a board is told in its config.h and no
# more. It does not read the world: a real board could not, and letting this one would quietly
# make it a different kind of thing than the hardware it stands in for.
_SIMULATED_Q = f"""
SELECT ?id ?readingTopic ?commandTopic ?senseMode ?initial ?dryRate ?tick ?litres ?doseTopic ?port ?minValue ?maxValue
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?d <{AG}localId> ?id ; <{AG}simulatedBy> ?model ; <{AG}readingTopic> ?readingTopic ;
     <{AG}monitors> ?subject .
  OPTIONAL {{ ?d <{AG}commandTopic> ?commandTopic }}
  OPTIONAL {{ ?d <{AG}senseMode> ?senseMode }}
  OPTIONAL {{ ?model <{AG}modelInitialValue> ?initial }}
  OPTIONAL {{ ?model <{AG}modelDryRate> ?dryRate }}
  OPTIONAL {{ ?model <{AG}modelTickSeconds> ?tick }}
  OPTIONAL {{ ?model <{AG}modelMinValue> ?minValue }}
  OPTIONAL {{ ?model <{AG}modelMaxValue> ?maxValue }}
  OPTIONAL {{ ?subject <{AG}litresPerFraction> ?litres }}
  OPTIONAL {{ ?valve <{AG}actuates> ?subject ; <{AG}statusTopic> ?doseTopic }}
  ?bus a <{AG}MessageBus> ; <{AG}brokerPort> ?port .
}} }}"""


def _simulator(world: str, row: dict) -> str:
    """One container per stand-in, mirroring one container per agent.

    So one principal holds one credential and the ACL model is unchanged — the broker cannot
    tell this from a board, and neither can anything else. It reuses the agent image because it
    needs one library that image already has; a second image for a hundred-line script would be
    another thing to build and keep current, for nothing.
    """
    sim_id = row["id"]
    mode = (row.get("senseMode") or "").rsplit("#", 1)[-1].lower() or "scheduled"
    optional = "".join(
        f'\n      {k}: "{v}"' for k, v in (
            ("SIM_COMMAND_TOPIC", row.get("commandTopic")),
            ("SIM_DOSE_TOPIC", row.get("doseTopic")),
            ("SIM_INITIAL_VALUE", row.get("initial")),
            ("SIM_DRY_RATE", row.get("dryRate")),
            ("SIM_TICK_SECONDS", row.get("tick")),
            ("SIM_LITRES_PER_FRACTION", row.get("litres")),
        ) if v not in (None, ""))
    return f"""
  sim-{sim_id}:
    build:
      # its own directory: it needs one file, and the repo root is excluded from image
      # contexts anyway — the agent image must not carry the simulator, nor it the agent
      context: ../../firmware/simulated-sensor
    image: agora-simulator:local
    environment:
      SIM_SENSOR_ID: "{sim_id}"
      SIM_READING_TOPIC: "{row['readingTopic']}"
      # ag:Scheduled keeps the interval its agent gives it, like a deep-sleeping board;
      # ag:Push keeps its own clock and takes no orders. The agent derives its capability
      # from the same fact and never learns which side of it this is.
      SIM_SENSE_MODE: "{mode}"
      MQTT_HOST: "localhost"
      MQTT_PORT: "{int(row['port'])}"{optional}
    env_file:
      # its own credential, minted by `agora-mqtt` exactly as a board's is — the broker has no
      # way to tell a stand-in from hardware, which is the point
      - ./secrets/mqtt-{sim_id}.env
    network_mode: host
    restart: unless-stopped
"""


_SIM_VALVES_Q = f"""
SELECT ?id ?commandTopic ?statusTopic ?mlPerSecond ?maxDoseMl ?port
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?v <{AG}localId> ?id ; <{AG}simulatedBy> ?model ; <{AG}actuates> ?subject ;
     <{AG}commandTopic> ?commandTopic ; <{AG}statusTopic> ?statusTopic .
  OPTIONAL {{ ?v <{AG}mlPerSecond> ?mlPerSecond }}
  OPTIONAL {{ ?v <{AG}maxDoseMl> ?maxDoseMl }}
  ?bus a <{AG}MessageBus> ; <{AG}brokerPort> ?port .
}} }}"""


def _valve(world: str, row: dict) -> str:
    """A valve that does not exist, refusing what a real one would refuse.

    Its own image, holding `cryptography` the sensor's does not need — because it VERIFIES. The
    supplier co-signs every command exactly as it would for hardware, and this opens only for a
    token carrying both signatures, so the simulation exercises the part of actuation the market
    exists to make safe rather than the part around it.

    It is mounted the two PUBLIC keys and no private one. It cannot author a command, which is
    what makes the check worth running.
    """
    valve_id = row["id"]
    return f"""
  valve-{valve_id}:
    build:
      # its own directory: the repo root is excluded from image contexts, and firmware must not
      # carry the agent any more than the agent carries firmware
      context: ../../firmware/simulated-valve
    image: agora-valve:local
    environment:
      VALVE_ID: "{valve_id}"
      VALVE_COMMAND_TOPIC: "{row['commandTopic']}"
      VALVE_STATUS_TOPIC: "{row['statusTopic']}"
      VALVE_ML_PER_SECOND: "{row.get('mlPerSecond', 10.0)}"
      VALVE_MAX_DOSE_ML: "{row.get('maxDoseMl', 1000.0)}"
      # public halves only — it verifies, it never signs
      VALVE_HOST_PUB: "/keys/host.pub"
      VALVE_CLEARING_PUB: "/keys/clearing.pub"
      MQTT_HOST: "localhost"
      MQTT_PORT: "{int(row['port'])}"
    env_file:
      # its own credential, minted by `agora-mqtt` exactly as a real valve's would be
      - ./secrets/mqtt-{valve_id}.env
    network_mode: host
    restart: unless-stopped
    volumes:
      # the PUBLIC keys, and nothing else from secrets/. A stand-in that could reach host.key
      # could sign for the society, and then verifying would be theatre.
      - ./secrets/host.pub:/keys/host.pub:ro
      - ./secrets/clearing.pub:/keys/clearing.pub:ro
"""


def _broker(world: str, plain: int, tls: int | None) -> str:
    """This world's own broker. Not shared infra, and that is the point.

    A broker per world costs about 2 MB and removes more than it adds: its ACL derives from ONE
    world's wiring instead of every provisioned world at once, it trusts exactly one certificate
    authority instead of a bundle rebuilt whenever a world appears, and a new world no longer
    forces a restart of something other societies are talking to. See knowledge/domain/onboarding.md.
    """
    ports = f'["{plain}:{plain}"' + (f', "{tls}:{tls}"]' if tls else "]")
    tls_mounts = "" if not tls else (
        "\n      # Its authority is this world's own, so it trusts exactly one and never learns\n"
        "      # that other worlds exist — the same rule the belief base already follows.\n"
        "      - ./secrets/ca.crt:/etc/mosquitto/clients-ca.crt:ro\n"
        "      - ./secrets/broker.crt:/etc/mosquitto/broker.crt:ro\n"
        "      - ./secrets/broker.key:/etc/mosquitto/broker.key:ro")
    return f"""
  mosquitto:
    build:
      context: ../../infra/mosquitto
      dockerfile: Containerfile
    image: agora-mosquitto:local
    ports: {ports}
    restart: unless-stopped
    volumes:
      # generated by `agora-mqtt {world}` from this world's wiring and its stated ports
      - ./mosquitto/agora.conf:/etc/mosquitto/conf.d/agora.conf:ro
      - ./mosquitto/passwd:/etc/mosquitto/passwd:ro
      - ./mosquitto/acl.conf:/etc/mosquitto/acl.conf:ro{tls_mounts}
      # retained cadences outlive a restart: a sleeping board must still receive the interval
      # its agent set before the broker bounced
      - agora-{world}-mosquitto:/var/lib/mosquitto
"""


def render(world: str) -> str:
    who = roster(world)
    if not who:
        raise SystemExit(f"agora-compose: world {world!r} declares no agents")

    plain, tls = _bus_ports(world)
    simulated = ratified.rows(ratified.dataset(world), _SIMULATED_Q)
    valves = ratified.rows(ratified.dataset(world), _SIM_VALVES_Q)
    services = _broker(world, plain, tls) + "".join(
        _simulator(world, row) for row in sorted(simulated, key=lambda r: r["id"])) + "".join(
        _valve(world, row) for row in sorted(valves, key=lambda r: r["id"])) + "".join(
        _service(a, caps, world) for a, caps in who.items())
    volumes = f"  agora-{world}-mosquitto:\n" + "".join(
        f"  agora-{world}-{a}:\n" for a in who)
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
# Infra (MQTT, Influx, Grafana) lives in infra/compose.yaml — bring it up first; the agents here
# discover the broker from the world and will retry until it answers. There is no triplestore.
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


def generate(world: str) -> Path:
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
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
