"""orexis-compose — write the compose file for a world, from the world.

  orexis-compose greenhouse     -> world/greenhouse/compose.yaml

A world is self-contained: its documents and the compose file that runs them live in one
directory. The roster is not typed here and not typed by you: it is read from the world as
onboarding reads it (`onboarding.reading.world`), so adding an agent to the world and regenerating is the
whole of deploying one — derived, never hand-maintained, because a second list is a second thing
to drift.

**One container per agent, and that is not packaging taste.** An agent's belief base is a store
in its own volume — nothing else can reach it, so isolation is structural rather than enforced.
See knowledge/decisions/where-the-belief-base-lives.md.

**Agent 0.2.0 runs here.** Each service runs `orexis-agent <world> <id> --volume /app/state`: the
world mounted at `/app/world/<name>` beside `/app/domains`, so a world's `owl:imports` of its
domains resolve, and the broker's address and the series store's handed in as environment —
the `schema:url`s the world asserts on its `mqtt4ssn:Broker` or the installation allocated it
(`onboarding.mqtt.broker`), where the world has a bus, and for each purpose the world's agents are told of
(`installation.purposes`) — history always, metrics where the world is `onboarding:monitored` — the
url and organisation of the series store the installation says `onboarding:serves` it, told under
the purpose's keys, `INFLUX_HISTORY_URL` and `_ORG`, `INFLUX_METRICS_URL` and `_ORG`, beside the
credential `orexis-influx` minted for each, and for metrics the window the installation states, as
`METRICS_INTERVAL_S`. An unmonitored world's agents are told of no metrics store at all. All of it
is deployment graphs, a kind the agent's vocabulary does not
declare, so no container is handed one and the agent cannot read where anything is. An agent that
holds a device writes its command topic, which the ACL admits it and nobody else to — an agent
trusts itself, so nothing is signed until the market brings a second agent to ask.

**The bus is the world's to have, and only a world that has one is given one** (`reading.BUS`, a
broker its society names): the broker's service, its volume, an agent's `MQTT_*` environment, its
broker credential and its certificates. A world with no bus — Hanoi, the courier, the tower — is
its agents alone, each told of its series stores and nothing else, which is all its runtime asks.

**An agent that finishes is not restarted.** The runtime stops an agent that holds no desire and
that no transport reaches once every want is reached — Hanoi's, the courier's, the tower's mover
— and `unless-stopped` would start it again for ever, each time to find nothing and exit. Whether
an agent lasts is read per agent, off the agent booted from its documents (`reading.lasts`), and
only an agent that does not is written `restart: "no"`.

**`network_mode: host` is deliberate.** Every broker is on `localhost`, asserted or allocated,
and every member — agents, stand-ins, a board on the LAN — must reach one bus by one name; and a
world with no bus reaches its series store the same way.

**A world's simulated systems are played by its simulator**, one more service: `python -m
simulation <world>`, connected as the one client that hosts every system the world marks
`sim:simulatedBy`, reading the world as an agent does. See knowledge/domain/kernel/world.md.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from agent.runtime import known, world_of
from agent.metrics import INTERVAL_KEY
from agent.series import HISTORY, METRICS
from agent.store import document, graphs_of, kinds_in, rows
from . import installation, reading
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

#  WHAT A WORLD IS MOUNTED AS: its documents, file by file, each because an agent reads its kind —
#  never its secrets, and never a document of a kind no agent's vocabulary declares, which is the
#  hardware `orexis-firmware` reads on the host. The boot would pass over such a document anyway;
#  not mounting it keeps it out of the container's filesystem as well, and it is the kind that
#  decides, never the file's name (a-documents-kind-says-who-reads-it).
DOCUMENTS = (".ttl", ".trig")


def roster(world: str) -> list[str]:
    """Every agent the world states, by id."""
    store = reading.world(world_dir(world))
    return [r["id"] for r in rows(store, _ROSTER_Q, graphs_of(store, PUBLIC))]


def read_by_an_agent(world: str) -> set[Path]:
    """Every document in the world's directory and under `beliefs/` holding a graph of a kind an
    agent reads — asked of the agent's own vocabulary as its boot has it, and not of onboarding's,
    whose kinds are exactly the ones an agent is not to be handed."""
    here = world_dir(world).resolve()
    store = world_of(here, others=reading.ours())
    candidates = [*here.iterdir(), *((here / "beliefs").iterdir() if (here / "beliefs").is_dir() else [])]
    return {p for p in candidates if p.is_file() and p.suffix in DOCUMENTS
            and any(known(store, kinds) for kinds in kinds_in(document(p)).values())}


def agent_ids(world: str) -> list[str]:
    return roster(world)


def series_credential(agent_id: str, purpose: str = HISTORY) -> str:
    """The name of the file under a world's `secrets/` holding the agent's credential for the series
    store it is told of for `purpose` — minted there by `orexis-influx`, mounted here."""
    return f"influx-{purpose.lower()}-{agent_id}.env"


def simulated_client(world: str) -> str | None:
    """The client the world's simulator connects as, or None where nothing is simulated. One
    simulator plays every simulated system, so they must share one client."""
    store = reading.world(world_dir(world))
    found = [r["id"] for r in rows(store, _SIMULATED_Q, graphs_of(store, PUBLIC))]
    if len(found) > 1:
        raise SystemExit(f"orexis-compose: {world!r} hosts simulated systems on {found}; one simulator plays "
                         "them all, so one client must host them")
    return found[0] if found else None


def _simulator(world: str, read: set[Path], client: str, host: str, plain: int) -> str:
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
    volumes:{_documents(world, read)}
      - ../../agent:/app/agent:ro
      - ../../domains:/app/domains:ro
      - ../../simulation:/app/simulation:ro
"""


def _documents(world: str, read: set[Path], agent_id: str | None = None) -> str:
    """The world's documents an agent reads, file by file, and an agent's own beliefs file where
    it has one — never another agent's."""
    here = world_dir(world).resolve()
    files = [p for p in sorted(here.iterdir()) if p in read]
    if agent_id is not None:
        files += [p for p in sorted((here / "beliefs").glob(f"{agent_id}.*")) if p in read]
    return "".join(f"\n      - ./{p.relative_to(here)}:/app/world/{world}/{p.relative_to(here)}:ro" for p in files)


def _restart(lasting: bool) -> str:
    """How an agent's service is restarted: always but by hand where it lasts, and never where it
    finishes (`reading.lasts`), since a restart of an agent that finished would boot, find nothing
    to pursue and exit again, for as long as the policy allowed."""
    if lasting:
        return "restart: unless-stopped"
    return ("# it holds no desire and no transport reaches it, so it exits once every want is reached,\n"
            "    # or as unreachable — restarted, it would only exit again\n"
            '    restart: "no"')


def _service(agent_id: str, world: str, read: set[Path], bus: tuple[str, int, int | None] | None,
             series: dict[str, tuple[str, str]], window: float | None, lasting: bool) -> str:
    """An agent's service. `bus` is the broker's (host, plain port, TLS port), or None where the
    world has none — and then nothing of a bus is written: no `MQTT_*`, no broker credential, no
    certificate. `lasting` says whether the agent runs for good (`reading.lasts`), and so whether
    its container is restarted."""
    stores = "".join(f'\n      INFLUX_{purpose}_URL: "{url}"\n      INFLUX_{purpose}_ORG: "{organisation}"'
                     for purpose, (url, organisation) in series.items())
    if METRICS in series and window is not None:
        stores += f'\n      {INTERVAL_KEY}: "{window:g}"'
    credentials = "".join(f"\n      - ./secrets/{series_credential(agent_id, purpose)}" for purpose in series)
    if bus:
        host, plain, tls = bus
        tls_env = f'\n      MQTT_TLS_PORT: "{tls}"' if tls else ""
        where = f"""
      # where this world's broker listens — asserted or allocated, generated here, never read off the world by the agent
      MQTT_HOST: "{host}"
      MQTT_PORT: "{plain}"{tls_env}
      MQTT_CERT: "/app/secrets/agent.crt"
      MQTT_KEY: "/app/secrets/agent.key"
      MQTT_CA: "/app/secrets/ca.crt\""""
        minted = (f"its own bucket per purpose and a token that opens only it, minted by `orexis-influx {world}`, and\n"
                  f"      # its own broker credential, minted by `orexis-mqtt {world}`; mounted into THIS container alone"
                  f"{credentials}\n      - ./secrets/mqtt-{agent_id}.env")
        certificates = (f"\n      - ./secrets/{agent_id}.crt:/app/secrets/agent.crt:ro"
                        f"\n      - ./secrets/{agent_id}.key:/app/secrets/agent.key:ro"
                        "\n      - ./secrets/ca.crt:/app/secrets/ca.crt:ro")
    else:
        where, certificates = "", ""
        minted = (f"its own bucket per purpose and a token that opens only it, minted by `orexis-influx {world}`;\n"
                  f"      # mounted into THIS container alone — the world has no bus, so no broker credential{credentials}")
    return f"""
  agent-{agent_id}:
    image: {IMAGE}
    command: ["orexis-agent", "/app/world/{world}", "{agent_id}", "--volume", "/app/state"]
    environment:{where}
      # where each series it writes goes, and the org — the store the installation says serves each
      # purpose, its metrics only where the world is monitored — safe for every agent to hold{stores}
    env_file:
      # {minted}
    network_mode: host
    # Rootless podman maps YOUR uid into the container; map it onto the image's user so the agent
    # can write its own belief-base volume.
    userns_mode: "keep-id:uid=10001,gid=10001"
    {_restart(lasting)}
    volumes:
      # its own belief base, and nobody else can name it
      - orexis-{world}-{agent_id}:/app/state
      # the world's documents, file by file, at the path its imports of the domains resolve from{_documents(world, read, agent_id)}{certificates}
      # The trees, mounted so a code change needs a restart rather than a rebuild — the SAME ones
      # the Containerfile copies, which `tests/test_layout.py` holds the two lists to.
      - ../../agent:/app/agent:ro
      - ../../domains:/app/domains:ro
      - ../../simulation:/app/simulation:ro
"""


def _broker(world: str, plain: int, tls: int | None) -> str:
    """This world's own broker. Not shared infra, and that is the point.

    A broker per world costs about 2 MB and removes more than it adds: its ACL derives from ONE
    world's wiring instead of every provisioned world at once, it trusts exactly one certificate
    authority instead of a bundle rebuilt whenever a world appears, and a new world no longer
    forces a restart of something other societies are talking to. See knowledge/domain/onboarding/onboarding.md.
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
      # generated by `orexis-mqtt {world}` from this world's wiring and the ports it asserts or is allocated
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
    #  THE BUS, where the world's society names a broker — and only then is `broker` asked for an
    #  address, which it refuses for a world with none.
    bus = broker(world) if reading.BUS in reading.premises(world_dir(world)) else None
    series = {purpose: installation.series(purpose) for purpose in installation.purposes(world)}
    window = installation.interval(METRICS) if METRICS in series else None
    client = simulated_client(world)
    if client and not bus:
        raise SystemExit(f"orexis-compose: {world!r} hosts simulated systems on {client!r} and names no "
                         "mqtt4ssn:Broker for its simulator to connect to")
    read = read_by_an_agent(world)
    services = ((_broker(world, *bus[1:]) if bus else "")
                + (_simulator(world, read, client, *bus[:2]) if client else "")
                + "".join(_service(a, world, read, bus, series, window, reading.lasts(world_dir(world), a))
                          for a in who))
    volumes = (f"  orexis-{world}-mosquitto:\n" if bus else "") + "".join(f"  orexis-{world}-{a}:\n" for a in who)
    first = f"orexis-mqtt {world}" if bus else f"orexis-influx {world}"
    return f"""# GENERATED by `orexis-compose {world}` from the world beside it — do not edit.
#
# The roster is the world. Add an agent there, regenerate, and it is deployed; there is no second
# list to keep in step. Run `{first}` first, then from this directory:
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
