"""orexis-mqtt — mint a credential per principal, and derive the ACL from the wiring.

  orexis-mqtt society     -> credentials for its agents, and a rebuilt broker ACL

The bus had no ACLs at all: `allow_anonymous true`, so any process on the LAN could subscribe
`#` and watch every reading, every bid and every claim. That is the same hole the series
store had, and it gets the same answer — except that here the answer is *derivable*, because
the world already states every channel and who is wired to it.

**The ACL is the wiring.** Nothing is listed by hand. The same connections that give an agent a
capability give it exactly the topics that capability needs:

    sensing:polls S          read S's readingTopic, write S's commandTopic
    market:bidsIn M         read M's offerTopic and M's claimTopic/<me>, write M's bidTopic/<me>
                            and M's redeemTopic/<me> — the holder presents its own claim (#132)
    market:hosts M          write M's offerTopic and claimTopic/<bidder>, read bidTopic/+ and
                            redeemTopic/+
                        and each bidder's eventTopic
    actuation:hasActuator V    write V's commandTopic
    mqtt:eventTopic E     write E

Read that list against `capabilities/market/bidding.py` and `hosting.py` and it is the same
set of topics they subscribe and publish. If it ever stops being, an agent fails to connect —
which is the point of deriving it rather than maintaining it.

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

from agent import ratified
from orexis_capability_reporting import sovereign

from . import certs
from agent.config import REPO_ROOT
from agent.genesis import world_dir, worlds
from orexis_capability_market.terms import NS as MARKET
from modality.ontology import AG, WORLD_GRAPH
from .namespaces import ACTUATION, MQTT, SENSING, SIM
log = logging.getLogger("mqtt")

def mosquitto_dir(world: str):
    """A broker per world, so its files live WITH the world rather than in shared infra.

    This is what makes the ACL below derivable from one world's wiring instead of from every
    provisioned world at once. The old shared broker forced the generator to span all of them —
    "the operator's view by necessity" — and forced a restart whenever a new world appeared,
    because its authority had to be added to a trust bundle the broker only reads at startup.
    Neither is true of a broker that belongs to one world.
    """
    return world_dir(world) / "mosquitto"

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


def _q(body: str) -> str:
    """IRIs in full: this runs on rdflib, which pre-binds prefixes that a real store does not.
    See backend/tests/test_store.py."""
    return f"SELECT {body}"


_AGENTS_Q = _q(f"""?id ?eventTopic WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  OPTIONAL {{ ?a <{MQTT}eventTopic> ?eventTopic }}
 }}""")

_POLLS_Q = _q(f"""?id ?readingTopic ?commandTopic WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{SENSING}polls> ?s .
  ?s <{MQTT}readingTopic> ?readingTopic .
  OPTIONAL {{ ?s <{MQTT}commandTopic> ?commandTopic }}
 }}""")

_BIDS_Q = _q(f"""?id ?offerTopic ?bidTopic ?claimTopic ?redeemTopic WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{MARKET}bidsIn> ?m .
  ?m <{MARKET}offerTopic> ?offerTopic ; <{MARKET}bidTopic> ?bidTopic ;
     <{MARKET}claimTopic> ?claimTopic .
  OPTIONAL {{ ?m <{MARKET}redeemTopic> ?redeemTopic }}
 }}""")

_HOSTS_Q = _q(f"""?id ?offerTopic ?bidTopic ?claimTopic ?redeemTopic ?bidderEvent
WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{MARKET}hosts> ?m .
  ?m <{MARKET}offerTopic> ?offerTopic ; <{MARKET}bidTopic> ?bidTopic ;
     <{MARKET}claimTopic> ?claimTopic .
  OPTIONAL {{ ?m <{MARKET}redeemTopic> ?redeemTopic }}
  OPTIONAL {{ ?b <{MARKET}bidsIn> ?m ; <{MQTT}eventTopic> ?bidderEvent }}
 }}""")

# A simulated sensor learns it was watered by reading what the valve REPORTED, never what the
# valve was told. A real plant gets wet because water arrives; nothing arrives here, so the
# valve's own account of what it dispensed stands in for the water — and a command the valve
# refused produces no report, so the soil stays dry. Reading the command instead would have
# watered the plant on an unsigned order, which is exactly the failure the market exists to
# prevent. The grant belongs to the DEVICE, not to its agent: an agent in this world has no
# more business reading a valve's traffic than one in any other world.
# Guarded on mqtt:onBus, because the grant belongs to whatever CONNECTS. A board reporting two
# properties is two sensors and one process: without this, the second sensor mints a principal
# of its own holding a single dose grant, for a client that never connects — the same defect
# #81 names one level up, where a board authenticates as one of its own peripherals.
_SIM_DOSE_Q = _q(f"""?id ?statusTopic WHERE {{
  ?d <{AG}localId> ?id ; <{SIM}simulatedBy> ?model ; <{SENSING}monitors> ?subject ;
     <{MQTT}onBus> ?bus .
  {{ ?valve <{ACTUATION}actuates> ?subject ; <{MQTT}statusTopic> ?statusTopic }}
  UNION
  {{ ?valve <{ACTUATION}drawsFrom> ?subject ; <{MQTT}statusTopic> ?statusTopic }}
 }}""")
# The UNION's second branch is the SUPPLY side (the barrel learns to run dry): a source's
# level stand-in hears every valve that draws from its subject — same guard, same grant
# shape, because the litre is one event with two witnesses.

# And the rain, by the same guard: a simulated sensor whose subject can be rained on hears it
# arrive on the subject's sim:rainTopic. Its own channel rather than the valve's status topic,
# because the status topic is the VALVE's testimony and rain is nobody's — the soil cannot tell
# the two waters apart, but the record must never say a valve dispensed what a stranger poured.
_SIM_RAIN_Q = _q(f"""?id ?rainTopic WHERE {{
  ?d <{AG}localId> ?id ; <{SIM}simulatedBy> ?model ; <{SENSING}monitors> ?subject ;
     <{MQTT}onBus> ?bus .
  ?subject <{SIM}rainTopic> ?rainTopic .
 }}""")

# The meddler itself: ONE principal per world that states sim:strayDoseMeanDays, granted WRITE on
# every rain topic and nothing else. The worst a compromised meddler can do is be over-generous
# with water — it cannot hear a reading, see an offer, or speak for a valve.
_MEDDLER_Q = _q(f"""?rainTopic WHERE {{
  ?w a <{AG}World> ; <{SIM}strayDoseMeanDays> ?mean .
  ?subject <{SIM}rainTopic> ?rainTopic .
 }}""")

# Any valve that reports, stood in for or not. This used to require sim:simulatedBy, which meant
# a REAL valve could not publish the status its own firmware sends — "so the executor knows water
# actually flowed" — and the broker dropped it silently, because MQTT never refuses a publish out
# loud. The simulation was strictly more capable than the hardware it stands for, which is the
# wrong way round.
_VALVE_STATUS_Q = _q(f"""?id ?statusTopic WHERE {{ 
  ?v <{AG}localId> ?id ; <{ACTUATION}actuates> ?subject ; <{MQTT}statusTopic> ?statusTopic .
 }}""")

# And whoever actuates it must be able to HEAR that report, or the confirmation goes nowhere.
_ACTUATOR_STATUS_Q = _q(f"""?id ?statusTopic WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{ACTUATION}hasActuator> ?v .
  ?v <{MQTT}statusTopic> ?statusTopic .
 }}""")

# One way of holding an actuator. There used to be two, because a simulated valve was a
# different class held by a different property; it is an actuation:Valve that happens to be stood in
# for now, so the agent side of this stopped needing to know the difference at all.
_ACTUATES_Q = _q(f"""?id ?commandTopic WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  ?a <{ACTUATION}hasActuator> ?v .
  ?v <{MQTT}commandTopic> ?commandTopic .
 }}""")

# `mqtt:onBus` is the device's own declaration that it is reachable on a bus — the same test
# `MqttDriver.claims()` applies. Anything without it speaks no MQTT and needs no credential.
_DEVICES_Q = _q(f"""?id ?readingTopic ?commandTopic WHERE {{ 
  ?d <{AG}localId> ?id ; <{MQTT}onBus> ?bus .
  OPTIONAL {{ ?d <{MQTT}readingTopic> ?readingTopic }}
  OPTIONAL {{ ?d <{MQTT}commandTopic> ?commandTopic }}
 }}""")


_BUS_Q = f"""
SELECT ?host WHERE {{  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerHost> ?host  }}
LIMIT 1"""


def broker_host(world: str) -> str:
    """The name this world's members meet the broker under — which must be the CN on its
    certificate, or every agent that verifies it will refuse the connection."""
    found = ratified.rows(ratified.dataset(world), _BUS_Q)
    if not found:
        raise SystemExit(f"orexis-mqtt: world {world!r} declares no mqtt:MessageBus")
    return found[0]["host"]


def agent_username(world: str, agent_id: str) -> str:
    """World-qualified: two worlds each holding a `fern` are two principals, on two belief
    bases, and must not be able to answer for each other."""
    return f"{world}-{agent_id}"


def grants(world: str) -> tuple[dict[str, Principal], dict[str, Principal]]:
    """(agents, devices) — every principal this world implies, and what the wiring allows it.

    The world is composed exactly as an agent composes it, derivation included, so this asks
    the same graph the agent will act from rather than a description of it.
    """
    ds = ratified.dataset(world)
    agents: dict[str, Principal] = {}
    devices: dict[str, Principal] = {}

    def agent(agent_id: str) -> Principal:
        return agents.setdefault(agent_id, Principal(agent_username(world, agent_id)))

    for row in ratified.rows(ds, _AGENTS_Q):
        # Voluntary disclosure: an agent announces its own verdict, and may write nowhere else.
        agent(row["id"]).may(WRITE, row.get("eventTopic"))

    for row in ratified.rows(ds, _POLLS_Q):
        me = agent(row["id"])
        me.may(READ, row["readingTopic"])
        me.may(WRITE, row.get("commandTopic"))  # cadence and sense-now

    for row in ratified.rows(ds, _BIDS_Q):
        me, who = agent(row["id"]), row["id"]
        me.may(READ, row["offerTopic"])
        me.may(READ, f"{row['claimTopic']}/{who}")  # its own claim, and nobody else's
        if row.get("redeemTopic"):
            me.may(WRITE, f"{row['redeemTopic']}/{who}")  # presents its OWN claim (#132)
        me.may(WRITE, f"{row['bidTopic']}/{who}")

    for row in ratified.rows(ds, _HOSTS_Q):
        me = agent(row["id"])
        me.may(WRITE, row["offerTopic"])
        me.may(WRITE, f"{row['claimTopic']}/+")  # it addresses each winner in turn
        if row.get("redeemTopic"):
            me.may(READ, f"{row['redeemTopic']}/+")  # and hears every holder's claim (#132)
        me.may(READ, f"{row['bidTopic']}/+")
        me.may(READ, row.get("bidderEvent"))

    for row in ratified.rows(ds, _ACTUATES_Q):
        agent(row["id"]).may(WRITE, row["commandTopic"])

    # The sovereign's question channel (packages/orexis-capability-reporting/sovereign.py): one principal per world, never
    # mounted into any agent container, may ask each agent and hear each answer — and each
    # agent may hear only its own questions and answer only on its own channel. Explicit
    # topic pairs rather than wildcards, in this file's own idiom: silence is not permission.
    asker = devices.setdefault(sovereign.SOVEREIGN, Principal(sovereign.SOVEREIGN))
    for agent_id in sorted(agents):
        asker.may(WRITE, sovereign.query_topic(agent_id))
        asker.may(READ, sovereign.result_topic(agent_id))
        agents[agent_id].may(READ, sovereign.query_topic(agent_id))
        agents[agent_id].may(WRITE, sovereign.result_topic(agent_id))

    for row in ratified.rows(ds, _DEVICES_Q):
        if row["id"] in agents:
            continue  # an agent and a device may not share a name; the world says which it is
        device = devices.setdefault(row["id"], Principal(row["id"]))
        device.may(WRITE, row.get("readingTopic"))  # it publishes what it read
        device.may(READ, row.get("commandTopic"))  # it listens for what to do

    for row in ratified.rows(ds, _SIM_DOSE_Q):
        devices.setdefault(row["id"], Principal(row["id"])).may(READ, row["statusTopic"])

    for row in ratified.rows(ds, _SIM_RAIN_Q):
        devices.setdefault(row["id"], Principal(row["id"])).may(READ, row["rainTopic"])

    for row in ratified.rows(ds, _MEDDLER_Q):
        devices.setdefault("meddler", Principal("meddler")).may(WRITE, row["rainTopic"])

    for row in ratified.rows(ds, _VALVE_STATUS_Q):
        # it already reads its command topic as any device does; this is the other direction
        devices.setdefault(row["id"], Principal(row["id"])).may(WRITE, row["statusTopic"])

    for row in ratified.rows(ds, _ACTUATOR_STATUS_Q):
        agents.setdefault(row["id"], Principal(agent_username(world, row["id"]))).may(
            READ, row["statusTopic"])

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


def provisioned_worlds() -> list[str]:
    """Every world whose agents already hold credentials.

    The broker is one process serving whatever is running, so its ACL has to span all of them —
    and rebuilding it from only the world just provisioned would lock the others out. This is
    the operator's view by necessity; see the note in `ratified.py`.
    """
    return [w for w in worlds() if any((world_dir(w) / "secrets").glob("mqtt-*.env"))]


def provision(world: str, rotate: bool = False) -> None:
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
        what = ("the sovereign's question channel — held on the host, never mounted into any "
                "agent container" if device_id == sovereign.SOVEREIGN
                else f"device {device_id} — flashed into the board")
        _credential(path, principal.username, what, rotate=False)
        log.info("  device %-14s %-28s %2d grants%s", device_id, principal.username,
                 len(principal.grants), "  (new — reflash the board)" if fresh else "")

    # Agents also get a client certificate. Boards deliberately do not: a deep-sleeping board
    # would pay a TLS handshake on every wake, and the ACL below authorises both the same way.
    certs.issue_for_world(world, agents.keys(), rotate=rotate,
                          broker_host=broker_host(world))

    rebuild(world)
    write_config(world)


_PORTS_Q = f"""
SELECT ?port ?tlsPort WHERE {{ 
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerPort> ?port .
  OPTIONAL {{ ?bus <{MQTT}brokerTlsPort> ?tlsPort }}  }} LIMIT 1"""


def write_config(world: str) -> None:
    """This world's broker configuration, from the ports the world itself states.

    Generated rather than baked, because the ports are a fact about THIS world and two brokers on
    one host must not collide. Everything else is the same in every world, and is here rather
    than in the image so that changing it is regenerating rather than rebuilding.
    """
    found = ratified.rows(ratified.dataset(world), _PORTS_Q)
    if not found:
        raise SystemExit(f"orexis-mqtt: world {world!r} declares no mqtt:MessageBus")
    plain, tls = int(found[0]["port"]), found[0].get("tlsPort")

    lines = [
        f"# GENERATED by `orexis-mqtt {world}` — do not edit. One broker per world.",
        "#",
        "# The ports come from this world's mqtt:MessageBus, which is also where its agents read",
        "# them. Two worlds are two brokers on two ports, and neither can hear the other.",
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
            "certfile /etc/mosquitto/broker.crt",
            "# entrypoint.sh re-owns this to mosquitto at 0600 while it is still root, because",
            "# the broker opens it AFTER dropping privileges.",
            "keyfile /run/mosquitto/broker.key",
            "",
        ]
    lines += ["# Shared by both listeners, derived from this world's wiring alone.",
              "acl_file /etc/mosquitto/acl.conf", ""]

    d = mosquitto_dir(world)
    d.mkdir(parents=True, exist_ok=True)
    (d / "orexis.conf").write_text("\n".join(lines))
    (d / "orexis.conf").chmod(0o644)
    log.info("  broker %-24s :%s%s", world, plain, f" +mTLS :{int(tls)}" if tls else "")


def rebuild(world: str) -> None:
    """Write THIS world's broker files, from this world's wiring and nothing else."""
    passwd: dict[str, str] = {}
    blocks: list[str] = []

    agents, devices = grants(world)
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

    d = mosquitto_dir(world)
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
        f"# GENERATED by `orexis-mqtt {world}` from that world's wiring — do not edit.\n"
        "#\n"
        "# Each principal may say and hear exactly what the world connects it to. There is no\n"
        "# list behind this: add an agent to world.ttl, re-run, and it is admitted. Nothing is\n"
        "# granted by default, and an unlisted user may do nothing at all.\n"
        + "\n".join(blocks) + "\n")
    acl_file.chmod(0o644)
    log.info("  wrote %s and %s (%d principals)", passwd_file.relative_to(REPO_ROOT),
             acl_file.relative_to(REPO_ROOT), len(passwd))


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
# One broker per world, so the name is the world's compose project.
def _broker_names(world: str):
    return (f"orexis-{world}_mosquitto_1", f"orexis-{world}-mosquitto-1")

RELOAD_HINT = ("pkill -HUP -P $(podman inspect -f '{{.State.Pid}}' <broker-container>)")


def reload_broker(world: str) -> bool:
    """Tell a running broker to reread what we just wrote. Best effort, and never fatal.

    Not running is the ordinary case during first-time setup — the ACL has to exist before the
    broker will start at all — so this reports rather than fails. What it must never do is stay
    quiet: mosquitto accepts a SUBSCRIBE it will not honour, so an unreloaded ACL looks like an
    agent that has gone silent rather than an error.
    """
    import os
    import signal
    import subprocess

    names = [n for n in (os.environ.get(BROKER_CONTAINER),) if n] or list(_broker_names(world))
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-mqtt",
        description="Mint each principal's broker credential and derive the ACL from the world.")
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--rotate", action="store_true",
                   help="replace every AGENT password. Devices are never rotated this way — "
                        "their credential is flashed into a board.")
    p.add_argument("--no-reload", action="store_true",
                   help="write the files but do not signal the broker. It will keep enforcing "
                        "the previous ACL until it is reloaded or restarted.")
    args = p.parse_args()
    log.info("world %s", args.world)
    provision(args.world, rotate=args.rotate)
    if not args.no_reload:
        reload_broker(args.world)


if __name__ == "__main__":
    main()
