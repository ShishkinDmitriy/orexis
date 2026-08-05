"""agora-mqtt — mint a credential per principal, and derive the ACL from the wiring.

  agora-mqtt society     -> credentials for its agents, and a rebuilt broker ACL

The bus had no ACLs at all: `allow_anonymous true`, so any process on the LAN could subscribe
`#` and watch every reading, every bid and every voucher. That is the same hole the series
store had, and it gets the same answer — except that here the answer is *derivable*, because
the world already states every channel and who is wired to it.

**The ACL is the wiring.** Nothing is listed by hand. The same connections that give an agent a
capability give it exactly the topics that capability needs:

    ag:polls S          read S's readingTopic, write S's commandTopic
    ag:bidsIn M         read M's offerTopic and M's voucherTopic/<me>, write M's bidTopic/<me>
    ag:hosts M          write M's offerTopic and voucherTopic/<bidder>, read bidTopic/+
                        and each bidder's eventTopic
    ag:hasActuator V    write V's commandTopic
    ag:eventTopic E     write E

Read that list against `capabilities/market/bidding.py` and `hosting.py` and it is the same
set of topics they subscribe and publish. If it ever stops being, an agent fails to connect —
which is the point of deriving it rather than maintaining it.

**Agents are world-scoped principals; devices are not.** An agent runs in a container belonging
to one world. A board is flashed once and is the same board whichever world is loaded — which
`world/sensing` depends on deliberately, being device-for-device identical to `world/society`
so one ESP32 works in either. So a device's credential lives in `infra/secrets/devices/` and is
reused across worlds, and only agents get a world-qualified username.

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

from . import ratified
from .config import PROJECT_ROOT
from .genesis import DEFAULT_WORLD, world_dir, worlds
from .ontology import AG, WORLD_GRAPH

log = logging.getLogger("mqtt")

REPO_ROOT = PROJECT_ROOT.parent
MOSQUITTO_DIR = REPO_ROOT / "infra" / "mosquitto"
PASSWD_FILE = MOSQUITTO_DIR / "passwd"
ACL_FILE = MOSQUITTO_DIR / "acl.conf"
DEVICE_SECRETS = REPO_ROOT / "infra" / "secrets" / "devices"

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


_AGENTS_Q = _q(f"""?id ?eventTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  OPTIONAL {{ ?a <{AG}eventTopic> ?eventTopic }}
}} }}""")

_POLLS_Q = _q(f"""?id ?readingTopic ?commandTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}polls> ?s .
  ?s <{AG}readingTopic> ?readingTopic .
  OPTIONAL {{ ?s <{AG}commandTopic> ?commandTopic }}
}} }}""")

_BIDS_Q = _q(f"""?id ?offerTopic ?bidTopic ?voucherTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}bidsIn> ?m .
  ?m <{AG}offerTopic> ?offerTopic ; <{AG}bidTopic> ?bidTopic ;
     <{AG}voucherTopic> ?voucherTopic .
}} }}""")

_HOSTS_Q = _q(f"""?id ?offerTopic ?bidTopic ?voucherTopic ?bidderEvent
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}hosts> ?m .
  ?m <{AG}offerTopic> ?offerTopic ; <{AG}bidTopic> ?bidTopic ;
     <{AG}voucherTopic> ?voucherTopic .
  OPTIONAL {{ ?b <{AG}bidsIn> ?m ; <{AG}eventTopic> ?bidderEvent }}
}} }}""")

# A modelled subject listens for its own watering. There is no board to receive the dose, so
# the agent holding the model applies it to the model — which means reading the command topic
# of whatever actuates its subject. Mirrors the query in capabilities/simulated-sensing.
_MODELS_Q = _q(f"""?id ?commandTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}models> ?m .
  ?m <{AG}monitors> ?subject .
  ?valve <{AG}actuates> ?subject ; <{AG}commandTopic> ?commandTopic .
}} }}""")

# Both ways of holding an actuator. A simulated valve is driven over the same channel as a real
# one — that is what makes the market unable to tell them apart — so it is granted the same way.
_ACTUATES_Q = _q(f"""?id ?commandTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  ?a <{AG}hasActuator>|<{AG}hasSimulatedActuator> ?v .
  ?v <{AG}commandTopic> ?commandTopic .
}} }}""")

# `ag:onBus` is the device's own declaration that it is reachable on a bus — the same test
# `MqttDriver.claims()` applies. Anything without it speaks no MQTT and needs no credential.
_DEVICES_Q = _q(f"""?id ?readingTopic ?commandTopic WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?d <{AG}localId> ?id ; <{AG}onBus> ?bus .
  OPTIONAL {{ ?d <{AG}readingTopic> ?readingTopic }}
  OPTIONAL {{ ?d <{AG}commandTopic> ?commandTopic }}
}} }}""")


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
        me.may(READ, f"{row['voucherTopic']}/{who}")  # its own voucher, and nobody else's
        me.may(WRITE, f"{row['bidTopic']}/{who}")

    for row in ratified.rows(ds, _HOSTS_Q):
        me = agent(row["id"])
        me.may(WRITE, row["offerTopic"])
        me.may(WRITE, f"{row['voucherTopic']}/+")  # it addresses each winner in turn
        me.may(READ, f"{row['bidTopic']}/+")
        me.may(READ, row.get("bidderEvent"))

    for row in ratified.rows(ds, _MODELS_Q):
        agent(row["id"]).may(READ, row["commandTopic"])

    for row in ratified.rows(ds, _ACTUATES_Q):
        agent(row["id"]).may(WRITE, row["commandTopic"])

    for row in ratified.rows(ds, _DEVICES_Q):
        if row["id"] in agents:
            continue  # an agent and a device may not share a name; the world says which it is
        device = devices.setdefault(row["id"], Principal(row["id"]))
        device.may(WRITE, row.get("readingTopic"))  # it publishes what it read
        device.may(READ, row.get("commandTopic"))  # it listens for what to do

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
        f"# GENERATED by `agora-mqtt` — {note}\n"
        f"MQTT_USERNAME={username}\n"
        f"MQTT_PASSWORD={password}\n"
    )
    path.chmod(0o600)
    return password


def agent_credential_file(world: str, agent_id: str) -> Path:
    return world_dir(world) / "secrets" / f"mqtt-{agent_id}.env"


def device_credential_file(device_id: str) -> Path:
    return DEVICE_SECRETS / f"{device_id}.env"


def provisioned_worlds() -> list[str]:
    """Every world whose agents already hold credentials.

    The broker is one process serving whatever is running, so its ACL has to span all of them —
    and rebuilding it from only the world just provisioned would lock the others out. This is
    the operator's view by necessity; see the note in `ratified.py`.
    """
    return [w for w in worlds() if any((world_dir(w) / "secrets").glob("mqtt-*.env"))]


def provision(world: str = DEFAULT_WORLD, rotate: bool = False) -> None:
    agents, devices = grants(world)
    if not agents:
        raise SystemExit(f"agora-mqtt: world {world!r} declares no agents")

    for agent_id, principal in sorted(agents.items()):
        path = agent_credential_file(world, agent_id)
        fresh = rotate or not path.exists()
        _credential(path, principal.username, f"agent {agent_id} of world {world}", rotate)
        log.info("  agent-%-12s %-28s %2d grants%s", agent_id, principal.username,
                 len(principal.grants), "  (new)" if fresh else "")

    for device_id, principal in sorted(devices.items()):
        path = device_credential_file(device_id)
        # NOT rotated with the world: a device credential is flashed into a board, and rotating
        # it here would silently strand hardware that is not in front of you.
        fresh = not path.exists()
        _credential(path, principal.username, f"device {device_id} — flashed into the board",
                    rotate=False)
        log.info("  device %-14s %-28s %2d grants%s", device_id, principal.username,
                 len(principal.grants), "  (new — reflash the board)" if fresh else "")

    rebuild()


def rebuild() -> None:
    """Write the broker's two files from every provisioned world at once."""
    passwd: dict[str, str] = {}
    blocks: list[str] = []
    devices_seen: dict[str, Principal] = {}

    for world in provisioned_worlds():
        agents, devices = grants(world)
        blocks.append(f"\n# ---- world {world} " + "-" * (60 - len(world)))
        for agent_id, principal in sorted(agents.items()):
            password = _read_password(agent_credential_file(world, agent_id))
            if password is None:
                continue
            passwd[principal.username] = password
            blocks.append("\n".join(principal.lines()))
        for device_id, principal in sorted(devices.items()):
            # A board shared by two worlds is one principal holding the union of what those
            # worlds say it may do — which is the same thing said twice, when they agree.
            held = devices_seen.setdefault(device_id, Principal(principal.username))
            held.grants |= principal.grants

    if devices_seen:
        blocks.append("\n# ---- devices (not world-scoped: a board is flashed once) " + "-" * 8)
        for device_id, principal in sorted(devices_seen.items()):
            password = _read_password(device_credential_file(device_id))
            if password is None:
                continue
            passwd[principal.username] = password
            blocks.append("\n".join(principal.lines()))

    MOSQUITTO_DIR.mkdir(parents=True, exist_ok=True)
    PASSWD_FILE.write_text(
        "".join(f"{user}:{_hash(password)}\n" for user, password in sorted(passwd.items())))
    # 0644, unlike the credential files: the broker runs as an unprivileged user inside a
    # container that maps the host user to root, so a 0600 file is one it cannot open — and
    # what is here are PBKDF2 hashes. The plaintext lives in the per-principal files, which
    # stay 0600 and are mounted only into the one container entitled to them.
    PASSWD_FILE.chmod(0o644)
    ACL_FILE.write_text(
        "# GENERATED by `agora-mqtt` from every provisioned world's wiring — do not edit.\n"
        "#\n"
        "# Each principal may say and hear exactly what the world connects it to. There is no\n"
        "# list behind this: add an agent to a world.ttl, re-run, and it is admitted. Nothing\n"
        "# is granted by default, and an unlisted user may do nothing at all.\n"
        + "\n".join(blocks) + "\n")
    ACL_FILE.chmod(0o644)
    log.info("wrote %s and %s (%d principals)", PASSWD_FILE.relative_to(REPO_ROOT),
             ACL_FILE.relative_to(REPO_ROOT), len(passwd))


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
BROKER_CONTAINER = "AGORA_BROKER_CONTAINER"
_BROKER_NAMES = ("agora_mosquitto_1", "agora-mosquitto-1")

RELOAD_HINT = ("pkill -HUP -P $(podman inspect -f '{{.State.Pid}}' <broker-container>)")


def reload_broker() -> bool:
    """Tell a running broker to reread what we just wrote. Best effort, and never fatal.

    Not running is the ordinary case during first-time setup — the ACL has to exist before the
    broker will start at all — so this reports rather than fails. What it must never do is stay
    quiet: mosquitto accepts a SUBSCRIBE it will not honour, so an unreloaded ACL looks like an
    agent that has gone silent rather than an error.
    """
    import os
    import signal
    import subprocess

    names = [n for n in (os.environ.get(BROKER_CONTAINER),) if n] or list(_BROKER_NAMES)
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
        prog="agora-mqtt",
        description="Mint each principal's broker credential and derive the ACL from the world.")
    p.add_argument("world", nargs="?", default=DEFAULT_WORLD,
                   help=f"which world (default: {DEFAULT_WORLD}). Available: " + ", ".join(worlds()))
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
        reload_broker()


if __name__ == "__main__":
    main()
