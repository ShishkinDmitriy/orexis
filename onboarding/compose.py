"""orexis-compose — write the compose file for a world, from the world.

  orexis-compose greenhouse     -> world/greenhouse/compose.yaml

A world is self-contained: its documents and the compose file that runs them live in one
directory. The roster is not typed here and not typed by you: it is read from the world as an
agent boots it (`agent.runtime.world_of`), so adding an agent to the world and regenerating is the
whole of deploying one — derived, never hand-maintained, because a second list is a second thing
to drift.

**One container per agent, and that is not packaging taste.** An agent's belief base is a store
in its own volume — nothing else can reach it, so isolation is structural rather than enforced.
See knowledge/decisions/where-the-belief-base-lives.md.

**Agent 0.2.0 runs here.** Each service runs `orexis-agent <world> <id> --volume /app/state`: the
world mounted at `/app/world/<name>` beside `/app/domains`, so a world's `owl:imports` of its
domains resolve, and the broker's address handed in as environment, generated from the `schema:url`
on the world's `mqtt4ssn:Broker` — the agent itself never reads where its broker is. An agent that
holds a device writes its command topic, which the ACL admits it and nobody else to — an agent
trusts itself, so nothing is signed until the market brings a second agent to ask.

**`network_mode: host` is deliberate.** The world states its broker on `localhost`, and every
member — agents, stand-ins, a board on the LAN — must reach one bus by one name.

**A world's simulated systems are played by its simulator**, one more service: `python -m
simulation <world>`, connected as the one client that hosts every system the world marks
`sim:simulatedBy`, reading the world as an agent does. See knowledge/domain/world.md.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from agent.runtime import world_of
from agent.store import graphs_of, rows
from .worlds import REPO_ROOT
from .worlds import world_dir, worlds

from .mqtt import broker

log = logging.getLogger("compose")

IMAGE = "orexis:local"
PUBLIC = "http://example.org/orexis#PublicGraph"

_ROSTER_Q = "SELECT ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id } ORDER BY ?id"

#  THE CLIENT THE SIMULATOR CONNECTS AS: whichever hosts the systems no one built.
_SIMULATED_Q = """
SELECT DISTINCT ?id WHERE {
  ?client <https://www.w3id.org/MQTT4SSN-Ontology#hasClientID> ?id ;
          <https://www.w3id.org/MQTT4SSN-Ontology#hosts> ?system .
  ?system <http://example.org/orexis/sim#simulatedBy> ?model } ORDER BY ?id"""

#  WHAT A WORLD IS MOUNTED AS: its documents, file by file — never its secrets, and never its
#  wiring. An agent is not handed the hardware: only the sovereign loads both, and what keeps the
#  wiring out of an agent is that the file is not in its filesystem. `orexis-firmware` reads it, on
#  the host.
DOCUMENTS = (".ttl", ".trig")
HARDWARE_FILES = ("hardware.ttl",)


def roster(world: str) -> list[str]:
    """Every agent the world states, by id."""
    store = world_of(world_dir(world))
    return [r["id"] for r in rows(store, _ROSTER_Q, graphs_of(store, PUBLIC))]


def agent_ids(world: str) -> list[str]:
    return roster(world)


def simulated_client(world: str) -> str | None:
    """The client the world's simulator connects as, or None where nothing is simulated. One
    simulator plays every simulated system, so they must share one client."""
    store = world_of(world_dir(world))
    found = [r["id"] for r in rows(store, _SIMULATED_Q, graphs_of(store, PUBLIC))]
    if len(found) > 1:
        raise SystemExit(f"orexis-compose: {world!r} hosts simulated systems on {found}; one simulator plays "
                         "them all, so one client must host them")
    return found[0] if found else None


def _simulator(world: str, client: str, host: str, plain: int) -> str:
    return f"""
  simulation:
    image: {IMAGE}
    command: ["python", "-m", "simulation", "/app/world/{world}"]
    environment:
      MQTT_HOST: "{host}"
      MQTT_PORT: "{plain}"
    env_file:
      # the credential of `{client}`, the client that hosts what the world says no one built
      - ./secrets/mqtt-{client}.env
    network_mode: host
    userns_mode: "keep-id:uid=10001,gid=10001"
    restart: unless-stopped
    volumes:{_documents(world)}
      - ../../agent:/app/agent:ro
      - ../../domains:/app/domains:ro
      - ../../simulation:/app/simulation:ro
"""


def _documents(world: str, agent_id: str | None = None) -> str:
    """The world's documents, file by file, and an agent's own beliefs file where it has one —
    never another agent's."""
    here = world_dir(world)
    files = [p for p in sorted(here.iterdir())
             if p.is_file() and p.suffix in DOCUMENTS and p.name not in HARDWARE_FILES]
    if agent_id is not None:
        files += [p for p in sorted((here / "beliefs").glob(f"{agent_id}.*")) if p.suffix in DOCUMENTS]
    return "".join(f"\n      - ./{p.relative_to(here)}:/app/world/{world}/{p.relative_to(here)}:ro" for p in files)


def _service(agent_id: str, world: str, host: str, plain: int, tls: int | None) -> str:
    tls_env = f'\n      MQTT_TLS_PORT: "{tls}"' if tls else ""
    return f"""
  agent-{agent_id}:
    image: {IMAGE}
    command: ["orexis-agent", "/app/world/{world}", "{agent_id}", "--volume", "/app/state"]
    environment:
      # where this world's broker listens — generated from the world, never read off it by the agent
      MQTT_HOST: "{host}"
      MQTT_PORT: "{plain}"{tls_env}
      MQTT_CERT: "/app/secrets/agent.crt"
      MQTT_KEY: "/app/secrets/agent.key"
      MQTT_CA: "/app/secrets/ca.crt"
    env_file:
      # where the series store is, and the org — safe for every agent to hold
      - ../../infra/.env
      # its own bucket and a token that opens only it, minted by `orexis-influx {world}`, and its
      # own broker credential, minted by `orexis-mqtt {world}`; mounted into THIS container alone
      - ./secrets/influx-{agent_id}.env
      - ./secrets/mqtt-{agent_id}.env
    network_mode: host
    # Rootless podman maps YOUR uid into the container; map it onto the image's user so the agent
    # can write its own belief-base volume.
    userns_mode: "keep-id:uid=10001,gid=10001"
    restart: unless-stopped
    volumes:
      # its own belief base, and nobody else can name it
      - orexis-{world}-{agent_id}:/app/state
      # the world's documents, file by file, at the path its imports of the domains resolve from{_documents(world, agent_id)}
      - ./secrets/{agent_id}.crt:/app/secrets/agent.crt:ro
      - ./secrets/{agent_id}.key:/app/secrets/agent.key:ro
      - ./secrets/ca.crt:/app/secrets/ca.crt:ro
      # The trees, mounted so a code change needs a restart rather than a rebuild — the SAME ones
      # the Containerfile copies, which `tests/test_layout.py` holds the two lists to.
      - ../../agent:/app/agent:ro
      - ../../domains:/app/domains:ro
      - ../../simulation:/app/simulation:ro
      - ../../assembly:/app/assembly:ro
      - ../../agent_old:/app/agent_old:ro
      - ../../packages:/app/packages:ro
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
    image: orexis-mosquitto:local
    ports: {ports}
    restart: unless-stopped
    volumes:
      # generated by `orexis-mqtt {world}` from this world's wiring and its stated ports
      - ./mosquitto/orexis.conf:/etc/mosquitto/conf.d/orexis.conf:ro
      - ./mosquitto/passwd:/etc/mosquitto/passwd:ro
      - ./mosquitto/acl.conf:/etc/mosquitto/acl.conf:ro{tls_mounts}
      # retained cadences outlive a restart: a sleeping board must still receive the interval
      # its agent set before the broker bounced
      - orexis-{world}-mosquitto:/var/lib/mosquitto
"""



def render(world: str) -> str:
    who = roster(world)
    if not who:
        raise SystemExit(f"orexis-compose: world {world!r} declares no agents")
    host, plain, tls = broker(world)
    client = simulated_client(world)
    services = _broker(world, plain, tls) + (_simulator(world, client, host, plain) if client else "") + "".join(
        _service(a, world, host, plain, tls) for a in who)
    volumes = f"  orexis-{world}-mosquitto:\n" + "".join(f"  orexis-{world}-{a}:\n" for a in who)
    return f"""# GENERATED by `orexis-compose {world}` from the world beside it — do not edit.
#
# The roster is the world. Add an agent there, regenerate, and it is deployed; there is no second
# list to keep in step. Run `orexis-mqtt {world}` first, then from this directory:
#
#   cd world/{world} && podman compose up -d
#   cd world/{world} && podman compose logs -f

name: orexis-{world}

# podman-compose puts every service in one pod by default, and a pod cannot combine with the
# per-service user-namespace mapping below. Ignored by docker compose.
x-podman:
  in_pod: false

services:
{services}
volumes:
{volumes}"""


def generate(world: str) -> Path:
    out = world_dir(world) / "compose.yaml"
    out.write_text(render(world))
    log.info("wrote %s", out.relative_to(REPO_ROOT))
    for agent_id in roster(world):
        log.info("  agent-%s", agent_id)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-compose",
        description="Generate the compose file for a world, from that world's roster.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
