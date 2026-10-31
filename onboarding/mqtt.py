"""orexis-mqtt — mint a credential per principal, and derive the ACL from the wiring.

  orexis-mqtt society     -> credentials for its agents, and a rebuilt broker ACL

The bus had no ACLs at all: `allow_anonymous true`, so any process on the LAN could subscribe
`#` and watch every reading, every bid and every claim. That is the same hole the series
store had, and it gets the same answer — except that here the answer is *derivable*, because
the world already states every channel and who is wired to it.

**The ACL is the wiring.** Nothing is listed by hand. The world's society graph says, in MQTT4SSN's
words, which topic each sensor publishes on and which each device listens to, and who acts for
what; each agent's self graph says which sensors the observer roles it plays read:

    an agent reads sensor S     read the topics S publishes on, and write the topic its board
                                listens to (cadence and sense-now)
    an agent holds actuator A   write the topic A listens to, or its board's (a step's command)
    a person P speaks to it     write the topic P listens to (what it says to them)
    a client hosts sensor X     write the topics X publishes on
    a client hosts actuator A   read the topics A listens to, and the client's own
    a client hosts person P     read the topic P listens to, and write the inbox of the agent P
                                speaks to — the translator, connected as that client — and read what
                                the client P speaks through says, and write what it hears
    P speaks through client C   C writes the topic it says on, and reads the one it listens to

Read that list against `agent/transport/mqtt/driver.py` and it is the same set of topics the agent
subscribes to and publishes on. If it ever stops being, an agent fails to connect — which is the
point of deriving it rather than maintaining it. A topic is named by the patterns of the filters
that match it (MQTT4SSN), so a grant is a pattern, wildcards and all.

**Every principal is world-scoped, devices included.** An agent runs in a container belonging to
one world. A board was argued to be different — flashed once, the same physical thing whichever
world is loaded, which `world/sensing` depends on by being device-for-device identical to
`world/society` so one ESP32 works in either.

That stopped holding when each world got its own broker. A board is flashed with one host and one
**port**, so it already reaches exactly one world; sharing its password meant every world's broker
held a secret the others' boards also used. Its credential lives in `world/<w>/secrets/` now, like
an agent's. The two worlds are still device-for-device identical — what differs is which broker
the board is pointed at.

Only agents get a world-qualified *username*, which is now belt-and-braces rather than load-
bearing: a broker that serves one world has no namespace for `fern` to collide in.

**Taking a principal away is said, never derived.** A re-run grants what the wiring implies and
`orexis-onboard` reports what is held beyond that (`stale`); `--revoke <principal>` takes it: the
credential goes and the ACL is rebuilt without it, the certificate goes on the world's CRL, which
the generated config names on every TLS listener and `certs` writes on every run, empty where
nobody is revoked — a `crlfile` the broker cannot read refuses every agent, not one (#28, #29).

Like `influx_admin`, this is the operator's half and nothing inside an agent may import it.
See knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from cryptography import x509

from . import certs, installation, reading
from agent.ontology import local_of
from agent.store import graphs_of, rows
from .worlds import REPO_ROOT
from .worlds import shown, world_dir, worlds

log = logging.getLogger("mqtt")

def mosquitto_dir(world: str, broker_iri: str | None = None):
    """A world's brokers are its own, so their files live WITH the world rather than in shared infra:
    each broker's config, passwd and ACL under `mosquitto/<its local name>/`, and what every broker
    of the world shares — the authority's CRL — in `mosquitto/` itself, asked with no broker.

    This is what makes an ACL derivable from one world's wiring instead of from every provisioned
    world at once. The old shared broker forced the generator to span all of them — "the operator's
    view by necessity" — and forced a restart whenever a new world appeared, because its authority
    had to be added to a trust bundle the broker only reads at startup. Neither is true of a broker
    that belongs to one world, and a world may have any number.
    """
    return world_dir(world) / "mosquitto" / (local_of(broker_iri) if broker_iri else "")


def service_of(broker_iri: str) -> str:
    """The compose service, and the stem of the volume, a broker runs as: by its local name."""
    return f"mosquitto-{local_of(broker_iri)}"

READ, WRITE = "read", "write"

# Mosquitto's own password format: PBKDF2-HMAC-SHA512, salt and hash base64, iteration count
# written into the line so the broker needs no agreement with us about it. Generated here
# rather than by shelling out to `mosquitto_passwd`, which would put a broker binary on the
# operator's host just to hash a string.
PBKDF2_ITERATIONS = 101
_SALT_BYTES = 12
_HASH_BYTES = 64


# ---------------------------------------------------------------- the grants


@dataclass
class Principal:
    """One thing that may connect, and everything it may say or hear."""

    username: str
    grants: set[tuple[str, str]] = field(default_factory=set)  # (read|write, topic)

    def may(self, access: str, topic: str | None) -> None:
        """A topic the world did not state is not a grant. Silence is not permission."""
        if topic:
            self.grants.add((access, topic))

    def lines(self) -> list[str]:
        return [f"user {self.username}"] + [
            f"topic {access} {topic}" for access, topic in sorted(self.grants,
                                                                  key=lambda g: (g[1], g[0]))
        ]


BELIEF = "http://example.org/orexis#BeliefGraph"
SELF_GRAPH = "http://example.org/orexis#SelfGraph"
ACTUATION = "http://example.org/orexis/actuation#"

#  A TOPIC IS NAMED BY THE PATTERNS OF THE FILTERS THAT MATCH IT, in every query below.
#  MQTT4SSN's words in full: onboarding's texts are held to the 0.1.0 store's dictionary too, which
#  never loaded the transport that binds `mqtt4ssn:`.
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
_AGENTS_Q = "SELECT ?a ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id }"

#  WHAT AN AGENT READS AND NUDGES: the topics of every sensor an observer role it plays reads, and its
#  board's — asked of the agent as its boot reads it, since which sensors are its is declared in its own
#  self graph (`sensing:sensor`), which a store of the whole world does not hold.
_HEARS_Q = f"""
SELECT ?pattern WHERE {{
  ?me a orexis:Self ; orexis:plays/sensing:sensor ?sensor . ?sensor <{MQTT4SSN}observesTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

_NUDGES_Q = f"""
SELECT ?pattern WHERE {{
  ?me a orexis:Self ; orexis:plays/sensing:sensor ?sensor .
  ?board ssn:hasSubSystem ?sensor ; <{MQTT4SSN}listensToTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

#  WHAT AN AGENT COMMANDS: a device it holds (`actuation:hasActuator`), or what it acts for where that
#  listens for commands itself — the courier's van, told its drives where the world answers them (#1002).
_COMMANDS_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?a a orexis:Agent ; orexis:localId ?id .
  {{ ?a <{ACTUATION}hasActuator> ?device }} UNION {{ ?a orexis:actsFor ?device }}
  {{ ?device <{MQTT4SSN}listensToTopic> ?topic }} UNION {{ ?board ssn:hasSubSystem ?device ; <{MQTT4SSN}listensToTopic> ?topic }}
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

#  WHERE AN AGENT IS TOLD THINGS: the topic it listens to itself. It reads its own, and every other
#  agent of the world may write to it — whom an agent may speak to is the world's roster, and what
#  it may say is what the one it speaks to believes (speech's `heard`), not the broker's to judge.
_TOLD_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?a a orexis:Agent ; orexis:localId ?id ; <{MQTT4SSN}listensToTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

#  WHOM AN AGENT SPEAKS TO THAT IS NO AGENT: a person who `speech:speaksTo` it, listening on an inbox of
#  their own, where the agent's MQTT member publishes what it says to them as to any peer; and the
#  client hosting the person — the translator, which speaks for them — writes the agent's inbox, since
#  what the person says arrives there as a statement (knowledge/domain/speech/translator.md).
_SPEAKS_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?person a schema:Person ; speech:speaksTo ?a ; <{MQTT4SSN}listensToTopic> ?topic . ?a orexis:localId ?id .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

_SPEAKS_FOR_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?client <{MQTT4SSN}hasClientID> ?id ; <{MQTT4SSN}hosts> ?person . ?person a schema:Person ; speech:speaksTo ?a .
  ?a <{MQTT4SSN}listensToTopic> ?topic . ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

#  A PERSON'S OWN CLIENT — a phone, a terminal — says their prose on one topic and hears the translator's
#  on another (`speech:speaksThrough`, `speech:saysOn`); the translator, hosting the person, reads the
#  one and writes the other, and the client the reverse, its listening already granted by `_LISTENS_Q`.
_RELAYS_Q = f"""
SELECT ?id ?access ?pattern WHERE {{
  ?client <{MQTT4SSN}hasClientID> ?id ; <{MQTT4SSN}hosts> ?person . ?person speech:speaksThrough ?device .
  {{ ?device speech:saysOn ?topic . BIND ("{READ}" AS ?access) }}
  UNION {{ ?device <{MQTT4SSN}listensToTopic> ?topic . BIND ("{WRITE}" AS ?access) }}
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

_SAYS_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?device <{MQTT4SSN}hasClientID> ?id ; speech:saysOn ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

_CLIENTS_Q = f"""
SELECT ?client ?id WHERE {{ ?client a <{MQTT4SSN}Client> ; <{MQTT4SSN}hasClientID> ?id .
  FILTER NOT EXISTS {{ ?client a orexis:Agent }} }}"""

#  WHO IS CONNECTED TO WHICH BROKER, by the name each principal goes by: an agent by its id, any other
#  client by its client id. A broker's passwd and ACL hold the principals connected to it alone.
_CONNECTED_Q = f"""
SELECT ?c ?id ?broker WHERE {{
  {{ ?c a orexis:Agent ; orexis:localId ?id }} UNION {{ ?c <{MQTT4SSN}hasClientID> ?id FILTER NOT EXISTS {{ ?c a orexis:Agent }} }}
  ?c <{MQTT4SSN}isConnectedToBroker> ?broker }}"""

_PUBLISHES_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?client <{MQTT4SSN}hasClientID> ?id ; <{MQTT4SSN}hosts> ?sensor . ?sensor <{MQTT4SSN}observesTopic> ?topic .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

_LISTENS_Q = f"""
SELECT ?id ?pattern WHERE {{
  ?client <{MQTT4SSN}hasClientID> ?id .
  {{ ?client <{MQTT4SSN}listensToTopic> ?topic }} UNION {{ ?client <{MQTT4SSN}hosts> ?device . ?device <{MQTT4SSN}listensToTopic> ?topic }}
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?pattern }}"""

#  WHERE THE BROKER LISTENS: `schema:url` on the world's `mqtt4ssn:Broker`, plain and TLS. The
#  broker is named in the world's society graph, as what clients connect to; its urls are what the
#  world asserts in a deployment graph of its own, or, where it asserts none, what the installation
#  allocated it in the derived deployment graph (`infra/installation.derived.ttl`) — a kind only
#  onboarding reads, so the agent, told this through its environment, cannot read it off the world.
#  Asserted wins, derived completes, and this only reads which it is (onboarding.installation).
_DEFAULT_PORTS = {"mqtt": 1883, "mqtts": 8883}


def _world(world: str):
    return reading.world(world_dir(world))


def _rows(store, text: str) -> list[dict]:
    """Over the world's common beliefs — the world and its society, where every grant is read."""
    return rows(store, text, graphs_of(store, BELIEF, common=True))


def addresses(world: str) -> dict[str, tuple[str, int, int | None]]:
    """(host, plain port, TLS port or None) of each broker the world's society names, by its IRI, off
    its `schema:url`s. One host and one port per scheme each, which is onboarding's requirement (`requirements.ttl`), held by `reading.check` before any tool asking
    here runs, so this formats and judges nothing. It refused those by hand once, and before that
    kept the first host it met and a port per scheme from whichever url came last.

    The urls are the world's own where it asserts them, and otherwise the ones the installation
    allocated, asked for by the IRI the world's society names its broker by and nothing else — so a
    world is told its own brokers' addresses and never another's. Nothing here computes a port.
    """
    store = _world(world)
    return {b: _address(world, store, b) for b in installation.brokers_of(store)}


def _address(world: str, store, broker_iri: str) -> tuple[str, int, int | None]:
    from urllib.parse import urlparse
    urls = installation.asserted_on(store, broker_iri) or installation.allocated(broker_iri)
    hosts: set[str] = set()
    ports: dict[str, set[int]] = {scheme: set() for scheme in _DEFAULT_PORTS}
    for text in urls:
        url = urlparse(text)
        if url.scheme not in ports:
            continue
        if url.hostname:
            hosts.add(url.hostname)
        ports[url.scheme].add(url.port or _DEFAULT_PORTS[url.scheme])
    #  A BROKER ASSERTING A URL ASSERTS A PLAIN ONE, which is onboarding's requirement; one asserting none
    #  has an address only once the installation has allocated it, which is `orexis-onboard`'s to do.
    if not urls:
        raise SystemExit(f"orexis-mqtt: world {world!r} asserts no url on its mqtt4ssn:Broker {broker_iri}, "
                         "and the installation has allocated it none — `orexis-onboard` allocates one")
    return next(iter(hosts), "localhost"), next(iter(ports["mqtt"])), next(iter(ports["mqtts"]), None)


def connected(world: str) -> dict[str, set[str]]:
    """Every broker the world's society names, by its IRI, with the principals connected to it."""
    store = _world(world)
    out: dict[str, set[str]] = {b: set() for b in installation.brokers_of(store)}
    for row in _rows(store, _CONNECTED_Q):
        out.setdefault(row["broker"], set()).add(row["id"])
    return out


def broker_of(world: str, client: str) -> tuple[str, int, int | None]:
    """The address of the one broker `client` — a board, the simulator, by its IRI or its client id —
    is connected to, which is the one it is flashed or started with. That it is connected to exactly
    one the society names a broker is onboarding's requirement (`requirements.ttl`), held by
    `reading.check` before any tool asking here runs; this formats and judges nothing."""
    store = _world(world)
    (broker,) = {r["broker"] for r in _rows(store, _CONNECTED_Q) if client in (r["c"], r["id"])}
    return addresses(world)[broker]


def agent_username(world: str, agent_id: str) -> str:
    """World-qualified: two worlds each holding a `fern` are two principals, on two belief
    bases, and must not be able to answer for each other."""
    return f"{world}-{agent_id}"


def grants(world: str) -> tuple[dict[str, Principal], dict[str, Principal]]:
    """(agents, devices) — every principal this world implies, and what the wiring allows it,
    asked of the world as an agent boots it."""
    store = _world(world)
    agents: dict[str, Principal] = {}
    devices: dict[str, Principal] = {}

    def agent(agent_id: str) -> Principal:
        return agents.setdefault(agent_id, Principal(agent_username(world, agent_id)))

    for row in _rows(store, _AGENTS_Q):
        agent(row["id"])
    for agent_id in list(agents):
        beliefs = reading.boot(world_dir(world), agent_id, others=reading.ours())
        stated = [*graphs_of(beliefs, BELIEF, common=True), *graphs_of(beliefs, SELF_GRAPH)]
        for row in rows(beliefs, _HEARS_Q, stated):
            agent(agent_id).may(READ, row["pattern"])
        for row in rows(beliefs, _NUDGES_Q, stated):
            agent(agent_id).may(WRITE, row["pattern"])
    for row in _rows(store, _COMMANDS_Q):
        agent(row["id"]).may(WRITE, row["pattern"])
    for row in _rows(store, _TOLD_Q):
        agent(row["id"]).may(READ, row["pattern"])
        for other in list(agents):
            if other != row["id"]:
                agent(other).may(WRITE, row["pattern"])
    for row in _rows(store, _SPEAKS_Q):
        agent(row["id"]).may(WRITE, row["pattern"])

    for row in _rows(store, _CLIENTS_Q):
        if row["id"] in agents:
            continue                # an agent and a device may not share a name
        devices.setdefault(row["id"], Principal(row["id"]))
    for row in _rows(store, _PUBLISHES_Q):
        if row["id"] in devices:
            devices[row["id"]].may(WRITE, row["pattern"])
    for row in _rows(store, _LISTENS_Q):
        if row["id"] in devices:
            devices[row["id"]].may(READ, row["pattern"])
    for row in _rows(store, _SPEAKS_FOR_Q):
        if row["id"] in devices:
            devices[row["id"]].may(WRITE, row["pattern"])
    for row in _rows(store, _RELAYS_Q):
        if row["id"] in devices:
            devices[row["id"]].may(row["access"], row["pattern"])
    for row in _rows(store, _SAYS_Q):
        if row["id"] in devices:
            devices[row["id"]].may(WRITE, row["pattern"])
    return agents, devices


# ---------------------------------------------------------------- credentials


def _hash(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, PBKDF2_ITERATIONS,
                                 _HASH_BYTES)
    return (f"$7${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}"
            f"${base64.b64encode(digest).decode()}")


def _read_password(path: Path) -> str | None:
    """The credential file is the record. The broker keeps only a hash, so a password that is
    not here cannot be recovered — only replaced, which strands whatever already holds it."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("MQTT_PASSWORD="):
            return line.split("=", 1)[1]
    return None


def _credential(path: Path, username: str, note: str, rotate: bool) -> str:
    """Mint this principal's password, or keep the one it already holds."""
    if not rotate and (held := _read_password(path)) is not None:
        return held
    password = secrets.token_urlsafe(24)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# GENERATED by `orexis-mqtt` — {note}\n"
        f"MQTT_USERNAME={username}\n"
        f"MQTT_PASSWORD={password}\n"
    )
    path.chmod(0o600)
    return password


def agent_credential_file(world: str, agent_id: str) -> Path:
    return world_dir(world) / "secrets" / f"mqtt-{agent_id}.env"


def device_credential_file(world: str, device_id: str) -> Path:
    """Beside that world's agent credentials, not in shared infra.

    A board is flashed with ONE host and port, so it belongs to the world whose broker it was
    flashed for — and that world's broker is the only one holding its password. When the broker
    was shared, one credential per physical device was the right shape; with a broker per world
    it left the last secret spanning worlds, which is exactly what `infra/` should not hold.

    The cost is honest: a board moved to another world is re-flashed with that world's
    credential. It was already being re-flashed with that world's port.
    """
    return world_dir(world) / "secrets" / f"mqtt-{device_id}.env"


def provision(world: str, rotate: bool = False) -> None:
    """Every principal's credential, the agents' certificates, and this world's broker files.

    The brokers' addresses are asked FIRST, so a broker with no address asserted or allocated is
    refused before a credential is minted for a bus that is not there. The callers ask the premise
    (`reading.BUS`) and do not call this for a world with no bus."""
    hosts = sorted({host for host, _, _ in addresses(world).values()})
    if not hosts:
        raise SystemExit(f"orexis-mqtt: world {world!r} states no mqtt4ssn:Broker — it has no bus")
    agents, devices = grants(world)
    if not agents:
        raise SystemExit(f"orexis-mqtt: world {world!r} declares no agents")

    for agent_id, principal in sorted(agents.items()):
        path = agent_credential_file(world, agent_id)
        fresh = rotate or not path.exists()
        _credential(path, principal.username, f"agent {agent_id} of world {world}", rotate)
        log.info("  agent-%-12s %-28s %2d grants%s", agent_id, principal.username,
                 len(principal.grants), "  (new)" if fresh else "")

    for device_id, principal in sorted(devices.items()):
        path = device_credential_file(world, device_id)
        # NOT rotated with the world: a device credential is flashed into a board, and rotating
        # it here would silently strand hardware that is not in front of you.
        fresh = not path.exists()
        what = f"device {device_id} — flashed into the board, or handed to its stand-in"
        _credential(path, principal.username, what, rotate=False)
        log.info("  device %-14s %-28s %2d grants%s", device_id, principal.username,
                 len(principal.grants), "  (new — reflash the board)" if fresh else "")

    # Agents also get a client certificate. Boards deliberately do not: a deep-sleeping board
    # would pay a TLS handshake on every wake, and the ACL below authorises both the same way.
    certs.issue_for_world(world, agents.keys(), rotate=rotate, broker_hosts=hosts)

    rebuild(world)
    write_config(world)


def write_config(world: str) -> None:
    """Each of this world's brokers' configuration, on the ports its world asserts or the
    installation allocated it.

    Generated rather than baked, because the ports differ per world and two brokers on one host
    must not collide — which the installation, seeing the host, answers for. Everything else is
    the same in every world, and is here rather than in the image so that changing it is
    regenerating rather than rebuilding.
    """
    for broker_iri, (_, plain, tls) in sorted(addresses(world).items()):
        _write_config(world, broker_iri, plain, tls)


def _write_config(world: str, broker_iri: str, plain: int, tls: int | None) -> None:
    lines = [
        f"# GENERATED by `orexis-mqtt {world}` — do not edit. The broker {local_of(broker_iri)} of this world.",
        "#",
        "# The ports come from the `schema:url`s on this mqtt4ssn:Broker, which is also where its",
        "# agents' environment is generated from. Two brokers are two ports, whatever their worlds.",
        "",
        "log_dest stdout",
        "connection_messages true",
        "# Start as root and drop here, so the container can still be signalled. See",
        "# infra/mosquitto/entrypoint.sh.",
        "user mosquitto",
        "",
        f"listener {plain} 0.0.0.0",
        "allow_anonymous false",
        "password_file /etc/mosquitto/passwd",
        "",
    ]
    if tls:
        lines += [
            f"# Agents, by client certificate. The CN is the username the ACL already grants, so",
            "# there is no second mapping. Its authority is THIS WORLD'S ca.crt — the broker",
            "# belongs to the world, so it trusts exactly one and no bundle is assembled.",
            f"listener {int(tls)} 0.0.0.0",
            "require_certificate true",
            "use_identity_as_username true",
            "cafile /etc/mosquitto/clients-ca.crt",
            "# What that authority has revoked. ALWAYS named: with a crlfile OpenSSL demands a CRL",
            "# from the issuer on every handshake, so a listener naming an absent file refuses the",
            "# whole society — `orexis-mqtt` writes one on every run, empty where nobody is revoked.",
            "# Read at start only, like the certificates: a revocation needs a restart, not a HUP.",
            "crlfile /etc/mosquitto/crl.pem",
            "certfile /etc/mosquitto/broker.crt",
            "# entrypoint.sh re-owns this to mosquitto at 0600 while it is still root, because",
            "# the broker opens it AFTER dropping privileges.",
            "keyfile /run/mosquitto/broker.key",
            "",
        ]
    lines += ["# Shared by both listeners, derived from this world's wiring alone.",
              "acl_file /etc/mosquitto/acl.conf", ""]

    d = mosquitto_dir(world, broker_iri)
    d.mkdir(parents=True, exist_ok=True)
    (d / "orexis.conf").write_text("\n".join(lines))
    (d / "orexis.conf").chmod(0o644)
    log.info("  broker %-24s :%s%s", local_of(broker_iri), plain, f" +mTLS :{int(tls)}" if tls else "")


def rebuild(world: str) -> None:
    """Write each of THIS world's brokers' passwd and ACL, from this world's wiring and nothing
    else: a broker holds the principals connected to it, each with every grant the wiring gives it."""
    agents, devices = grants(world)
    for broker_iri, ids in sorted(connected(world).items()):
        _rebuild(world, broker_iri, {a: p for a, p in agents.items() if a in ids},
                 {d: p for d, p in devices.items() if d in ids})


def _rebuild(world: str, broker_iri: str, agents: dict[str, Principal], devices: dict[str, Principal]) -> None:
    passwd: dict[str, str] = {}
    blocks: list[str] = []
    for agent_id, principal in sorted(agents.items()):
        password = _read_password(agent_credential_file(world, agent_id))
        if password is None:
            continue
        passwd[principal.username] = password
        blocks.append("\n".join(principal.lines()))

    if devices:
        blocks.append("\n# ---- devices " + "-" * 56)
        for device_id, principal in sorted(devices.items()):
            # A board is flashed once and points at ONE broker, so it belongs to whichever world
            # it was flashed for. Two worlds naming the same device is now two brokers, only one
            # of which that board is talking to — which is a clearer story than one broker where
            # both worlds' agents ingested the same readings.
            password = _read_password(device_credential_file(world, device_id))
            if password is None:
                continue
            passwd[principal.username] = password
            blocks.append("\n".join(principal.lines()))

    d = mosquitto_dir(world, broker_iri)
    d.mkdir(parents=True, exist_ok=True)
    passwd_file, acl_file = d / "passwd", d / "acl.conf"
    passwd_file.write_text(
        "".join(f"{user}:{_hash(password)}\n" for user, password in sorted(passwd.items())))
    # 0644, unlike the credential files: the broker runs as an unprivileged user inside a
    # container that maps the host user to root, so a 0600 file is one it cannot open — and what
    # is here are PBKDF2 hashes. The plaintext lives in the per-principal files, which stay 0600
    # and are mounted only into the one container entitled to them.
    passwd_file.chmod(0o644)
    acl_file.write_text(
        f"# GENERATED by `orexis-mqtt {world}` from that world's wiring — do not edit. The broker\n"
        f"# {local_of(broker_iri)}, and the principals connected to it.\n"
        "#\n"
        "# Each principal may say and hear exactly what the world connects it to. There is no\n"
        "# list behind this: add an agent to the world, re-run, and it is admitted. Nothing is\n"
        "# granted by default, and an unlisted user may do nothing at all.\n"
        + "\n".join(blocks) + "\n")
    acl_file.chmod(0o644)
    log.info("  wrote %s and %s (%d principals)", shown(passwd_file), shown(acl_file), len(passwd))


# ---------------------------------------------------------------- revocation


RESTART_HINT = "cd world/{world} && podman compose restart {services}"


def revoke(world: str, principal: str) -> None:
    """Take one principal off the bus, by name: its credential file goes, so the next `rebuild`
    writes it no password and no grants; its certificate, where it has one, goes on the authority's
    CRL and its files go with it, so a re-onboarding issues a new one and the old stays refused.

    Explicit and never implicit. A principal the wiring no longer implies is reported by
    `orexis-onboard` and left alone until somebody says this, because an agent absent from a world
    today may be back tomorrow — and one the wiring STILL implies is granted again by the next
    `orexis-mqtt`, since the wiring is the grant; taking it out of the society is what revokes it
    for good, and this says so.

    The ACL change reaches the broker on the reload the caller sends. The CRL does not: the broker
    reads TLS material at start, so until it restarts the revoked certificate still opens a
    session — with a username the ACL grants nothing, which is a foothold and not a voice.
    """
    agents, devices = grants(world)
    credential = agent_credential_file(world, principal)   # a device's is at the same path
    cert_path, key_path = certs.agent_cert_files(world, principal)
    held = [p for p in (credential, cert_path, key_path) if p.exists()]
    if not held:
        raise SystemExit(f"orexis-mqtt: nothing to revoke — world {world!r} holds no credential or certificate "
                         f"for {principal!r} under secrets/")

    restart = False
    if cert_path.exists():
        serial = certs.revoke(world, cert_path)
        log.info("  %-14s certificate %x revoked — on %s", principal, serial, shown(certs.crl_file(world)))
        restart = True
    for path in held:
        path.unlink()
        log.info("  %-14s %s removed", principal, shown(path))
    rebuild(world)
    if principal in agents or principal in devices:
        log.warning("  ! the wiring still implies %s, so the next `orexis-mqtt %s` grants it again%s — take it "
                    "out of society.ttl to revoke it for good", principal, world,
                    " with a new certificate" if restart else "")
    if restart:
        log.warning("  ! the broker reads its CRL at start and SIGHUP does not reload TLS material — restart it "
                    "for the revocation to take: %s", RESTART_HINT.format(
                        world=world, services=" ".join(service_of(b) for b in sorted(connected(world)))))


def stale(world: str) -> list[str]:
    """What this world holds under `secrets/` for the bus that its wiring no longer implies: a
    broker credential of no agent or device in the society, a certificate of no agent. Report only
    — each line names what, why, and the command that would take it back. A world with no bus
    implies no principal at all, so everything of the bus it still holds is stale."""
    agents, devices = grants(world)
    secrets = world_dir(world) / "secrets"
    if not secrets.is_dir():
        return []
    found = []
    for path in sorted(secrets.iterdir()):
        name = path.name
        if name.startswith("mqtt-") and name.endswith(".env"):
            who = name[len("mqtt-"):-len(".env")]
            if who not in agents and who not in devices:
                found.append(f"secrets/{name} — no agent or device {who!r} in the society; "
                             f"`orexis-mqtt {world} --revoke {who}` takes it back")
        elif name.endswith((".crt", ".key")) and name.rsplit(".", 1)[0] not in ("ca", "broker"):
            who = name.rsplit(".", 1)[0]
            if who not in agents:
                how = ""
                if name.endswith(".crt"):
                    cert = x509.load_pem_x509_certificate(path.read_bytes())
                    how = (" — on the CRL already" if cert.serial_number in certs.revoked(world) else
                           f" — valid until {cert.not_valid_after_utc:%Y-%m-%d} and NOT on the CRL, so it still "
                           "opens a session")
                found.append(f"secrets/{name} — no agent {who!r} in the society{how}; "
                             f"`orexis-mqtt {world} --revoke {who}` revokes it")
    return found


# The broker reads `passwd` and `acl.conf` only at startup, so a regenerated ACL means nothing
# until it is told. SIGHUP makes it reread both WITHOUT dropping a single connected client —
# adding an agent must not interrupt the ones already running.
#
# Signalling it is more awkward than it should be, for two reasons that are both this host's
# and neither of which is worth making the operator remember:
#
#   - `podman kill --signal HUP` reaches the container's PID 1, which is the entrypoint shell
#     (root, so that podman can signal it at all — see infra/mosquitto/entrypoint.sh). The
#     shell then cannot forward to the broker: AppArmor mediates signals to a confined
#     process, and the profile that ships with the host's mosquitto package grants no `signal`
#     rules at all. Measured: a root shell in that container signals an unprivileged child
#     fine, and mosquitto specifically with EPERM.
#   - From the HOST it works, because the user namespace's creator keeps CAP_KILL inside it.
#
# So: signal the broker child of that container's PID 1, from here. `-P` keeps it exact — any
# other broker on this machine, including one from an unrelated project, is untouched.
BROKER_CONTAINER = "OREXIS_BROKER_CONTAINER"
# The world's compose project, and the broker's service in it.
def _broker_names(world: str, broker_iri: str):
    return (f"orexis-{world}_{service_of(broker_iri)}_1", f"orexis-{world}-{service_of(broker_iri)}-1")

RELOAD_HINT = ("pkill -HUP -P $(podman inspect -f '{{.State.Pid}}' <broker-container>)")


def reload_broker(world: str) -> bool:
    """Tell each of the world's running brokers to reread what we just wrote; whether every one was.
    Best effort, and never fatal."""
    return all([_reload(world, b) for b in sorted(connected(world))])


def _reload(world: str, broker_iri: str) -> bool:
    """Tell a running broker to reread what we just wrote. Best effort, and never fatal.

    Not running is the ordinary case during first-time setup — the ACL has to exist before the
    broker will start at all — so this reports rather than fails. What it must never do is stay
    quiet: mosquitto accepts a SUBSCRIBE it will not honour, so an unreloaded ACL looks like an
    agent that has gone silent rather than an error.
    """
    import os
    import signal
    import subprocess

    names = [n for n in (os.environ.get(BROKER_CONTAINER),) if n] or list(_broker_names(world, broker_iri))
    for name in names:
        try:
            out = subprocess.run(["podman", "inspect", "-f", "{{.State.Pid}}", name],
                                 capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            break  # no podman here at all; nothing to reload and nothing to say about it
        pid = out.stdout.strip()
        if out.returncode != 0 or not pid.isdigit() or pid == "0":
            continue
        children = (Path("/proc") / pid / "task" / pid / "children")
        try:
            broker_pids = [int(p) for p in children.read_text().split()]
        except OSError:
            broker_pids = []
        if not broker_pids:
            continue
        for broker in broker_pids:
            try:
                os.kill(broker, signal.SIGHUP)
            except OSError as exc:
                log.warning("  ! could not signal the broker (%s) — reload it by hand: %s",
                            exc, RELOAD_HINT)
                return False
        log.info("reloaded %s — connected agents kept their sessions", name)
        return True

    log.warning("  ! no running broker found, so nothing was reloaded. It will read these "
                "files when it next starts; if one IS running, reload it with: %s", RELOAD_HINT)
    return False


def main(argv: list[str] | None = None) -> None:
    """A world with no bus is answered, not refused: there is nothing to grant it, which is what
    `orexis-onboard` says of it too, and a loop running each step over every world goes on."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-mqtt",
        description="Mint each principal's broker credential and derive the ACL from the world. "
                    "A world whose society names no broker has no bus, and is granted nothing.")
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--rotate", action="store_true",
                   help="replace every AGENT password. Devices are never rotated this way — "
                        "their credential is flashed into a board.")
    p.add_argument("--no-reload", action="store_true",
                   help="write the files but do not signal the broker. It will keep enforcing "
                        "the previous ACL until it is reloaded or restarted.")
    p.add_argument("--revoke", metavar="PRINCIPAL",
                   help="take ONE principal off the bus, by its id, and grant nothing else: its credential "
                        "goes, its certificate goes on the world's CRL. Never implicit — `orexis-onboard` "
                        "only reports what the wiring no longer implies. The broker must be restarted "
                        "for a revoked certificate to be refused.")
    args = p.parse_args(argv)
    log.info("world %s", args.world)
    if args.revoke:
        #  A world with no bus may still hold a credential from when it had one; what is revoked
        #  is what is on disk, so this is not gated on the premise the grants are.
        revoke(args.world, args.revoke)
    elif reading.BUS not in reading.premises(world_dir(args.world)):
        log.info("  no bus — its society names no mqtt4ssn:Broker, so there is nothing to grant")
        return
    else:
        reading.check(world_dir(args.world))
        provision(args.world, rotate=args.rotate)
    if not args.no_reload:
        reload_broker(args.world)


if __name__ == "__main__":
    main()
