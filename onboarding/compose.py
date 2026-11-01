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
that no transport reaches once every want is reached — the courier's, the tower's mover — or, for
one that is no executor, once every want has a plan published — Hanoi's — and `unless-stopped`
would start it again for ever, each time to find nothing and exit. Whether
an agent lasts is read per agent, off the agent booted from its documents (`reading.lasts`), and
only an agent that does not is written `restart: "no"`.

**`network_mode: host` is deliberate.** Every broker is on `localhost`, asserted or allocated,
and every member — agents, stand-ins, a board on the LAN — must reach one bus by one name; and a
world with no bus reaches its series store the same way.

**A world's simulated systems are played by its simulator**, one more service: `python -m
simulation <world>`, connected as the one client that hosts every system the world marks
`sim:simulatedBy`, reading the world as an agent does. See knowledge/domain/kernel/world.md.

**An agent that translates is handed the model and its carriers' secrets**, and nothing else is: an
agent playing `translation:Translator` speaks with the people of its chats itself, so its own container is
told where the language model answers (`MODEL_URL`, the installation's `onboarding:Model`) and handed which
model and its key (`infra/secrets/model.env`), and, for each transport it speaks through beside the bus,
its secret — its bot's token (`secrets/telegram-<agent>.env`) and where its bot answers (`TELEGRAM_URL`,
off the world's deployment graph), its mailbox (`secrets/mail-<agent>.env`) — each written by hand, since
nothing can mint a bot or a mailbox. An agent that translates nothing is handed none of it, and a world
with a translator where the installation names no model is refused, as a monitored world is where
metrics are served by no store (knowledge/domain/translation/translator.md).
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from agent.runtime import EMAIL, KERNEL, TELEGRAM, documents, extra_of, known, packages_of, world_of
from agent.tree import closed, dependency_files, imported, kept, packages as tree_packages, sources as tree_sources
from agent.metrics.window import INTERVAL_KEY
from agent.series import HISTORY, METRICS
from agent.store import document, graphs_of, kinds_in, rows, whose
from . import installation, reading
from .worlds import REPO_ROOT
from .worlds import world_dir, worlds

from .mqtt import addresses, broker_of, service_of
from agent.ontology import local_of
from .reading import MQTT4SSN

log = logging.getLogger("compose")

IMAGE = "orexis:local"
#  THE EXTRA THE KERNEL'S SERIES WRITER BRINGS, and the simulator's: units beside the packages
#  (knowledge/decisions/a-package-brings-its-own-dependencies.md).
SERIES, SIMULATION = "series", "simulation"
#  THE DISTRIBUTION'S OWN FILES, where its extras are declared and its packages' code is: beside this tree,
#  whatever root a caller's worlds are read from.
_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


TRANSLATION = "translation"
BELIEF = "http://example.org/orexis#BeliefGraph"

_IDS_Q = "SELECT ?a ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id }"

#  THE BROKERS EACH AGENT IS CONNECTED TO, which its environment names with the url it reaches each at.
_CONNECTED_Q = f"""
SELECT ?id ?broker WHERE {{ ?a a orexis:Agent ; orexis:localId ?id ; <{MQTT4SSN}isConnectedToBroker> ?broker }}
ORDER BY ?id ?broker"""

#  WHERE AN AGENT'S BOT ANSWERS: the `schema:url` the world's deployment graph states on the bot the agent speaks
#  through on Telegram.
_BOT_Q = """
SELECT ?url WHERE { $agent <http://example.org/orexis/telegram#hasBot> ?bot . ?bot <https://schema.org/url> ?url } ORDER BY ?url"""


def declared_extras() -> frozenset[str]:
    """Every extra the distribution declares: the units that bring a library of their own, each from its file."""
    return frozenset(dependency_files(_PYPROJECT))


@dataclass(frozen=True)
class Image:
    """What one container is built from: the packages of `agent/` it holds, and the extras those bring."""
    tag: str
    packages: tuple[str, ...]
    extras: tuple[str, ...]
    simulator: bool = False

    def build(self) -> str:
        """The service's image and the build that makes it, its own: the Containerfile handed the packages to
        keep and the extras to install (knowledge/decisions/a-package-brings-its-own-dependencies.md)."""
        return (f"image: {self.tag}\n    build:\n      context: ../..\n      dockerfile: Containerfile\n      args:\n"
                f"        # the packages it runs and what they bring beyond the core, and nothing else's\n"
                f'        PACKAGES: "{",".join(self.packages)}"\n'
                f'        EXTRAS: "{",".join(self.extras)}"\n'
                f'        SIMULATOR: "{"yes" if self.simulator else "no"}"')

    def mounts(self) -> str:
        """The trees mounted over what the image copies, so a code change needs a restart and no rebuild — the
        agent tree entry by entry as the image keeps it (`agent.tree.kept`), the domains, the simulator's own."""
        lines = [f"\n      - ../../agent/{rel}:/app/agent/{rel}:ro" for rel in kept(self.packages, KERNEL)]
        lines.append("\n      - ../../domains:/app/domains:ro")
        if self.simulator:
            lines.append("\n      - ../../simulation:/app/simulation:ro")
        return "".join(lines)


def _extras(packages, series: bool, *also: str) -> tuple[str, ...]:
    declared = declared_extras()
    return tuple(sorted({extra_of(p) for p in packages if extra_of(p) in declared} | ({SERIES} if series else set())
                        | set(also)))


def image_of(world: str, agent_id: str, series: bool) -> Image:
    """`agent_id`'s own image: every package it loads and every package whose code those import, by
    `agent.tree.closed`, and the extras they bring — the series writer's where the installation serves a store."""
    packages = tuple(closed(packages_of(reading.boot(world_dir(world), agent_id, others=reading.ours()))))
    return Image(f"orexis-{world}-{agent_id}:local", packages, _extras(packages, series))


def simulator_image(world: str) -> Image:
    """The simulator's own image: the packages of the agent tree its code imports, and its extra."""
    packages = tuple(closed(sorted(imported(tree_sources(REPO_ROOT / "simulation"), set(tree_packages(KERNEL))))))
    return Image(f"orexis-{world}-simulation:local", packages, _extras(packages, False, SIMULATION), simulator=True)


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
#  decides, never the file's name (a-documents-kind-says-who-reads-it). And a document of an
#  agent's own goes to the agent its content names, and to no other container: the boot would
#  pass over another agent's, and not mounting it keeps one agent's desires out of another's
#  filesystem — again by what the document says, never by what it is called.


def roster(world: str) -> list[str]:
    """Every agent the world states, by id."""
    return reading.agents(world_dir(world))


def read_by_an_agent(world: str) -> dict[Path, frozenset[str] | None]:
    """Every document the boot reads in the world's directory, under `beliefs/` and under
    `secrets/` (`runtime.documents`), holding a graph of a kind an agent reads — asked of the
    agent's own vocabulary as its boot has it, and not of onboarding's, whose kinds are exactly the
    ones an agent is not to be handed — with whom it is FOR: None where it holds a common graph,
    which every agent and the simulator read, and otherwise the ids of the agents whose own
    graphs it holds, by what it says (`store.whose`) and never by its name."""
    here = world_dir(world).resolve()
    store = world_of(here, others=reading.ours())
    ids = {r["a"]: r["id"] for r in rows(store, _IDS_Q, graphs_of(store, BELIEF, common=True))}
    out: dict[Path, frozenset[str] | None] = {}
    for path in documents(here):
        if here not in path.parents:
            continue
        doc = document(path)
        held = {graph: kinds for graph, kinds in kinds_in(doc).items() if known(store, kinds)}
        if not held:
            continue
        common = any(whose(doc, graph) is None for graph in held)
        out[path] = None if common else frozenset(ids[whose(doc, graph)] for graph in held)
    return out


def agent_ids(world: str) -> list[str]:
    return roster(world)


def series_credential(agent_id: str, purpose: str = HISTORY) -> str:
    """The name of the file under a world's `secrets/` holding the agent's credential for the series
    store it is told of for `purpose` — minted there by `orexis-influx`, mounted here."""
    return f"influx-{purpose.lower()}-{agent_id}.env"


def simulated_client(world: str) -> str | None:
    """The client the world's simulator connects as, or None where nothing is simulated. One
    simulator plays every simulated system, so one client hosts them all, and that client is connected
    to a broker: the simulation domain's requirement and onboarding's (`domains/sim/requirements.ttl`,
    `onboarding/requirements.ttl`), held by `reading.check` before any tool asking here runs. This
    formats and judges nothing; it refused two clients by hand once."""
    store = reading.world(world_dir(world))
    found = {r["id"] for r in rows(store, _SIMULATED_Q, graphs_of(store, BELIEF, common=True))}
    return found.pop() if found else None


@dataclass(frozen=True)
class Translating:
    """What an agent that translates is handed: where the model answers, where its bot answers where it has one,
    and the carriers beside the bus it speaks through — `telegram`, `mail` — each a secret written by hand."""
    model: str
    bot: str | None
    carriers: tuple[str, ...]


def translating(world: str, agent_id: str) -> Translating | None:
    """What `agent_id` of `world` is handed for translating, booted as its container boots it — or None where it plays
    no translator. A translator where the installation names no model is refused."""
    beliefs = reading.boot(world_dir(world), agent_id, others=reading.ours())
    loaded = set(packages_of(beliefs))
    if TRANSLATION not in loaded:
        return None
    model = installation.model()
    if model is None:
        raise SystemExit(f"{agent_id} of world {world!r} translates, and the installation names no onboarding:Model — "
                         f"state where one answers in {installation._where(installation.INSTALLATION)}, or take the "
                         "translator out of its self graph")
    store = reading.world(world_dir(world))
    iri = next(r["a"] for r in rows(store, _IDS_Q, graphs_of(store, BELIEF, common=True)) if r["id"] == agent_id)
    bot = next((r["url"] for r in rows(store, _BOT_Q, graphs_of(store, BELIEF, reading.DEPLOYMENT, common=True), agent=iri)), None)
    carriers = tuple(name for name, package in (("telegram", TELEGRAM), ("mail", EMAIL)) if package in loaded)
    return Translating(model, bot, carriers)


def _simulator(world: str, read: set[Path], client: str, host: str, plain: int) -> str:
    image = simulator_image(world)
    return f"""
  simulation:
    {image.build()}
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
    volumes:{_documents(world, read)}{image.mounts()}
"""


def _documents(world: str, read: dict[Path, frozenset[str] | None], agent_id: str | None = None) -> str:
    """The world's documents an agent reads, file by file — those it keeps in `secrets/` among them,
    which are not committed — each public one, and each holding a graph that says it is this
    agent's own, never another agent's: whose a document is, is what it says (`read_by_an_agent`),
    so a document is mounted where its owner boots whatever its file is called. The simulator,
    `agent_id` None, is no agent and is handed the public documents alone."""
    here = world_dir(world).resolve()
    return "".join(f"\n      - ./{p.relative_to(here)}:/app/world/{world}/{p.relative_to(here)}:ro"
                   for p, owners in read.items() if owners is None or agent_id in owners)


def _restart(lasting: bool) -> str:
    """How an agent's service is restarted: always but by hand where it lasts, and never where it
    finishes (`reading.lasts`), since a restart of an agent that finished would boot, find nothing
    to pursue and exit again, for as long as the policy allowed."""
    if lasting:
        return "restart: unless-stopped"
    return ("# it holds no desire and no transport reaches it, so it exits once every want is reached —\n"
            "    # or has a plan published, where it is no executor — or as unreachable; restarted, it\n"
            "    # would only exit again\n"
            '    restart: "no"')


def _service(agent_id: str, world: str, read: set[Path], bus: list[tuple[str, str]] | None,
             series: dict[str, tuple[str, str]], window: float | None, lasting: bool, journal: str | None = None,
             incidents: tuple[str | None, list[str]] = (None, []), translates: Translating | None = None,
             image: Image | None = None) -> str:
    """An agent's service. `bus` is each broker the agent is connected to, by its IRI, with the url
    it reaches it at — TLS where the broker listens so, since an agent of a world with a bus holds a
    certificate — or None where the world has none, and then nothing of a bus is written: no
    `MQTT_*`, no broker credential, no certificate. `lasting` says whether the agent runs for good (`reading.lasts`), and so whether
    its container is restarted."""
    stores = "".join(f'\n      INFLUX_{purpose}_URL: "{url}"\n      INFLUX_{purpose}_ORG: "{organisation}"'
                     for purpose, (url, organisation) in series.items())
    if METRICS in series and window is not None:
        stores += f'\n      {INTERVAL_KEY}: "{window:g}"'
    if journal is not None:
        stores += ("\n      # where it serves its journal, on the host's loopback, allocated by the installation"
                   f'\n      JOURNAL_PORT: "{urlparse(journal).port}"')
    level, classes = incidents
    if level is not None or classes:
        stores += "\n      # what the world's deployment counts as an incident in its journal, beside its vocabulary"
    if level is not None:
        stores += f'\n      JOURNAL_INCIDENT_LEVEL: "{level}"'
    if classes:
        stores += f'\n      JOURNAL_INCIDENTS: "{" ".join(classes)}"'
    credentials = "".join(f"\n      - ./secrets/{series_credential(agent_id, purpose)}" for purpose in series)
    if translates is not None:
        stores += ("\n      # where the language model answers — the installation's `onboarding:Model`; which model, and the"
                   f'\n      # key, arrive in the installation\'s secret below\n      MODEL_URL: "{translates.model}"')
        if translates.bot:
            stores += f'\n      # where its Telegram bot answers, as the world\'s deployment graph states\n      TELEGRAM_URL: "{translates.bot}"'
        credentials += ("\n      # the model's name and key — `infra/model.env.example` says how — since it translates"
                        "\n      - ../../infra/secrets/model.env")
        for carrier in translates.carriers:
            credentials += (f"\n      # its {'bot' if carrier == 'telegram' else 'mailbox'}'s secret, written by hand: nothing can mint one"
                            f"\n      - ./secrets/{carrier}-{agent_id}.env")
    if bus is not None:
        told = " ".join(f"{iri} {url}" for iri, url in bus)
        where = f"""
      # each broker it is connected to and where that listens — asserted or allocated, generated here,
      # never read off the world by the agent
      MQTT_BROKERS: "{told}"
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
    {image.build()}
    command: ["orexis-agent", "/app/world/{world}", "{agent_id}", "--volume", "/app/state", "--journal", "/app/journal"]
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
      # its journal, a store of its own beside the beliefs and apart from them
      - orexis-{world}-{agent_id}-journal:/app/journal
      # the world's documents, file by file, at the path its imports of the domains resolve from{_documents(world, read, agent_id)}{certificates}
      # The trees, mounted so a code change needs a restart rather than a rebuild — the SAME entries its
      # image keeps, the kernel and its own packages and no other's, which `tests/test_layout.py` holds
      # to `agent.tree.kept`.{image.mounts()}
"""


def _broker(world: str, broker_iri: str, plain: int, tls: int | None) -> str:
    """One of this world's own brokers, as a service of its own. Not shared infra, and that is the point.

    A world may have any number of brokers, each served apart, on its own ports with its own passwd,
    ACL and volume, and every one of them trusting the world's authority alone. A broker of a world's
    own costs about 2 MB and removes more than it adds: its ACL derives from ONE
    world's wiring instead of every provisioned world at once, it trusts exactly one certificate
    authority instead of a bundle rebuilt whenever a world appears, and a new world no longer
    forces a restart of something other societies are talking to. See knowledge/domain/onboarding/onboarding.md.
    """
    ports = f'["{plain}:{plain}"' + (f', "{tls}:{tls}"]' if tls else "]")
    tls_mounts = "" if not tls else (
        "\n      # Its authority is this world's own, so it trusts exactly one and never learns\n"
        "      # that other worlds exist — the same rule the belief base already follows.\n"
        "      - ./secrets/ca.crt:/etc/mosquitto/clients-ca.crt:ro\n"
        "      # and what that authority has revoked — empty where nobody is, and always mounted,\n"
        "      # since the config names it and a crlfile that is absent refuses every agent\n"
        "      - ./mosquitto/crl.pem:/etc/mosquitto/crl.pem:ro\n"
        "      - ./secrets/broker.crt:/etc/mosquitto/broker.crt:ro\n"
        "      - ./secrets/broker.key:/etc/mosquitto/broker.key:ro")
    service, files = service_of(broker_iri), f"./mosquitto/{local_of(broker_iri)}"
    return f"""
  {service}:
    build:
      context: ../../infra/mosquitto
      dockerfile: Containerfile
    image: orexis-mosquitto:local
    ports: {ports}
    restart: unless-stopped
    volumes:
      # generated by `orexis-mqtt {world}` from this world's wiring and the ports it asserts or is allocated
      - {files}/orexis.conf:/etc/mosquitto/conf.d/orexis.conf:ro
      - {files}/passwd:/etc/mosquitto/passwd:ro
      - {files}/acl.conf:/etc/mosquitto/acl.conf:ro{tls_mounts}
      # retained cadences outlive a restart: a sleeping board must still receive the interval
      # its agent set before the broker bounced
      - orexis-{world}-{service}:/var/lib/mosquitto
"""



def _reached(world: str) -> dict[str, list[tuple[str, str]]]:
    """Each agent's brokers, by its id: the IRI and the url it reaches it at, TLS where the broker
    listens so and plain where it does not."""
    store = reading.world(world_dir(world))
    where = addresses(world)
    out: dict[str, list[tuple[str, str]]] = {}
    for r in rows(store, _CONNECTED_Q, graphs_of(store, BELIEF, common=True)):
        host, plain, tls = where[r["broker"]]
        out.setdefault(r["id"], []).append((r["broker"], f"mqtts://{host}:{tls}" if tls else f"mqtt://{host}:{plain}"))
    return out


def render(world: str) -> str:
    who = roster(world)
    if not who:
        raise SystemExit(f"orexis-compose: world {world!r} declares no agents")
    #  THE BUS, where the world's society names a broker — a service per broker, each agent told the
    #  ones it is connected to — and only then are the brokers' addresses asked for.
    bus = addresses(world) if reading.BUS in reading.premises(world_dir(world)) else {}
    reached = _reached(world) if bus else {}
    series = {purpose: installation.series(purpose) for purpose in installation.purposes(world)}
    window = installation.interval(METRICS) if METRICS in series else None
    client = simulated_client(world)
    read = read_by_an_agent(world)
    store = reading.world(world_dir(world))
    iris = {r["id"]: r["a"] for r in rows(store, _IDS_Q, graphs_of(store, BELIEF, common=True))}
    counted = installation.incidents(world)
    services = ("".join(_broker(world, b, *bus[b][1:]) for b in sorted(bus))
                + (_simulator(world, read, client, *broker_of(world, client)[:2]) if client else "")
                + "".join(_service(a, world, read, reached.get(a, []) if bus else None, series, window,
                                   reading.lasts(world_dir(world), a), installation.journal(iris[a]), counted,
                                   translating(world, a), image_of(world, a, bool(series)))
                          for a in who))
    volumes = ("".join(f"  orexis-{world}-{service_of(b)}:\n" for b in sorted(bus))
               + "".join(f"  orexis-{world}-{a}:\n  orexis-{world}-{a}-journal:\n" for a in who))
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
        translates = translating(world, agent_id)
        for carrier in translates.carriers if translates else ():
            secret = world_dir(world) / "secrets" / f"{carrier}-{agent_id}.env"
            log.info("    its %s is %s%s", "mailbox" if carrier == "mail" else "bot's token",
                     secret.relative_to(REPO_ROOT) if secret.is_relative_to(REPO_ROOT) else secret,
                     "" if secret.exists() else ", which is not there: write it by hand (knowledge/runbooks/run-a-world.md)")
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-compose",
        description="Generate the compose file for a world, from that world's roster.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    world = p.parse_args().world
    reading.check(world_dir(world))
    generate(world)


if __name__ == "__main__":
    main()
