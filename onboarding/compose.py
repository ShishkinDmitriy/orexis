"""orexis-compose — write the compose file for a world, from the world.

  orexis-compose society        -> world/society/compose.yaml

A world is self-contained: its topology, its agents' opening beliefs and the compose file that
runs it all live in one directory. The roster is not typed here and not typed by you: it is
read from `world/<name>/world.ttl`,
the same file the belief base is seeded from. Adding an agent to the world and regenerating is
the whole of deploying one. This is the same move `orexis-acl` already makes for the store's
access list — derived, never hand-maintained, because a second list is a second thing to drift.

**One container per agent, and that is not packaging taste.** An agent's belief base is a file
inside its own container — nothing else can reach it, so isolation is structural rather than
enforced. There are no credentials to hand out and no access registry to keep in step, because
there is no shared store to be let into. See knowledge/decisions/where-the-belief-base-lives.md.

**There is nothing to seed, and no ordering to express.** An agent builds its own belief base
at boot from the world files mounted read-only beside it, runs the derivation itself, and is
born if it has never been. So a service can start whenever it likes and depends on nothing.

**`network_mode: host` is deliberate.** The world states the bus as `mqtt:brokerHost "localhost"`
because a channel name is meaningless without the broker it is on and every member must agree
on it. Put the agents on a bridge network and that stops being true for them while staying true
for the ESP32 — two names for one bus, which is exactly what stating it in the world prevents.
Host networking keeps one bus with one name.

See knowledge/domain/world.md.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from agent import ratified
from agent.config import REPO_ROOT
from orexis_modality_graph.ontology import AG, WORLD_GRAPH
from .namespaces import ACTUATION, MARKET, MQTT, SENSING, SIM, SOSA
from agent import genesis
from agent.genesis import world_dir, worlds

log = logging.getLogger("compose")

IMAGE = "orexis:local"

_ROSTER_Q = f"""
SELECT ?id ?cap WHERE {{ 
  ?a a <{AG}Agent> ; <{AG}localId> ?id .
  OPTIONAL {{ ?a <{AG}hasCapability> ?cap }}
 }}"""

# The CAPABILITY, not the namespace `ACTUATION` imported above. Naming both the same thing
# shadowed the namespace and turned every `<{ACTUATION}actuates>` into nonsense — which cost
# nothing visible, because those patterns sit in OPTIONAL clauses that match nothing when the
# IRI is garbage. The supplier quietly stopped being mounted its signing keys.
ACTUATES = ACTUATION + "Actuation"

_BUS_PORTS_Q = f"""
SELECT ?port ?tlsPort WHERE {{ 
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerPort> ?port .
  OPTIONAL {{ ?bus <{MQTT}brokerTlsPort> ?tlsPort }}  }} LIMIT 1"""


def _bus_ports(world: str) -> tuple[int, int | None]:
    """The ports this world states. Two worlds are two brokers, so they must differ."""
    rows = ratified.rows(ratified.dataset(world), _BUS_PORTS_Q)
    if not rows:
        raise SystemExit(f"orexis-compose: world {world!r} declares no mqtt:MessageBus")
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
    the agent the signing keys and every other agent's opening beliefs.

    And not every file. An agent is given the SOCIETY and not the hardware — it never asks which
    pin a probe is on, only what it acts for, what it may poll and which topics reach it. The
    container simply does not have the file, which is enforcement rather than etiquette: the
    same shape as the Containerfile keeping onboarding out of the image.
    """
    return "\n".join(f"      - ./{p.name}:/app/world/{p.name}:ro"
                      for p in genesis.society_files(world_dir(world)))


def _service(agent_id: str, caps: set[str], world: str) -> str:
    # Only an agent that actuates has any use for a signing key, so only that one is given
    # them. Note the world is mounted FILE BY FILE rather than as a directory: mounting
    # world/<name>/ wholesale would hand every agent the signing keys and every other agent's
    # opening beliefs, neither of which it has any business reading.
    signing = ""
    if ACTUATES in caps:
        signing = ("\n      # it actuates, so it co-signs — these two keys and nothing else\n"
                   "      - ./secrets/host.key:/app/world/secrets/host.key:ro\n"
                   "      - ./secrets/clearing.key:/app/world/secrets/clearing.key:ro")
    # Its OWN identity (#144 signing, #145 sealing) — mounted only where keygen minted it, so
    # a world onboarded before keygen learned agents composes exactly as it always did. File
    # by file like everything here: the directory would hand it every other agent's keys.
    from agent.genesis import secrets_dir, world_dir

    own = secrets_dir(world_dir(world))
    for suffix in (".sign.key", ".seal.key"):
        if (own / f"{agent_id}{suffix}").exists():
            signing += (f"\n      - ./secrets/{agent_id}{suffix}"
                        f":/app/world/secrets/{agent_id}{suffix}:ro")
    world_files = _world_files(world)
    return f"""
  agent-{agent_id}:
    image: {IMAGE}
    command: ["orexis-agent"]
    environment:
      OREXIS_AGENT_ID: "{agent_id}"
      # Where to keep its belief base. A named volume, because beliefs must survive a
      # restart — otherwise every start would be a partial re-birth.
      OREXIS_STORE: "/app/state"
      # the ratified world, mounted below. The agent reads files, not a service.
      OREXIS_WORLD_DIR: "/app/world"
      # Where the three files mounted below live. The agent connects with the certificate when
      # the world states a TLS port and it holds one.
      MQTT_CERT: "/app/world/secrets/agent.crt"
      MQTT_KEY: "/app/world/secrets/agent.key"
      MQTT_CA: "/app/world/secrets/ca.crt"
    env_file:
      # where the series store is, and the org — safe for every agent to hold
      - ../../infra/.env
      # this agent's own bucket and a token that opens only it, and its own broker
      # credential. Minted by `orexis-influx` and `orexis-mqtt` from this world; mounted into
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
      - orexis-{world}-{agent_id}:/app/state
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
      # The trees, mounted so a code change needs a restart rather than a rebuild — the SAME
      # three the Containerfile copies, and keeping them in step is the lesson this block
      # keeps relearning. It relearned it again when `assembly/` arrived: this block said "the
      # same TWO" while the image copied three, and a restart would have failed on a missing
      # module. `tests/test_layout.py` compares the two lists now, so the next tree cannot
      # arrive in one and not the other. capabilities/ and transports/ moved inside agent/ and their husks
      # were mounted silently; then vocabulary/ moved inside packages/ and its mount failed
      # LOUDLY — a bind whose source is gone refuses to start the container, but only at the
      # next restart, which arrived with a host logout weeks after the tree moved. A mount
      # resolves when a container is CREATED, so a stale one keeps running until the day it
      # cannot.
      - ../../assembly:/app/assembly:ro
      - ../../agent:/app/agent:ro
      - ../../packages:/app/packages:ro
"""


# Everything a stand-in needs, which is exactly what a board is told in its config.h and no
# more. It does not read the world: a real board could not, and letting this one would quietly
# make it a different kind of thing than the hardware it stands in for.
# Everything a stand-in needs, which is exactly what a board is told in its config.h and no
# more — but one row PER VALUE it reports, because a part may report several down one line.
#
# The container belongs to whichever device holds the credential (`mqtt:onBus`), and the values
# belong to every simulated sensor on that device's reading topic, itself included. That is the
# shape `world/sensing` already states for a real KY-015: one peripheral owns the connection and
# its neighbours share the wire without minting a principal that never connects.
#
# What the simulator is told to be, keyed by the mode the world states.
#
# STATED, not derived from the IRI. This used to be `senseMode.rsplit("#")[-1].lower()`, which
# tied a container's environment to how a term happens to be spelled — so renaming the modes to
# read as procedures would have sent `SIM_SENSE_MODE: "pushreporting"` to a simulator that
# compares against `"push"`, and a self-clocked stand-in would have quietly kept an interval
# instead. Nothing would have failed: the world validates, the container starts, and the only
# symptom is a device behaving like the other kind.
#
# The env word is the simulator's contract and the IRI is the society's vocabulary. They are
# allowed to differ, and saying so once is what stops a rename reaching across the boundary.
_SIM_MODE = {
    SENSING + "ScheduledProcedure": "scheduled",
    SENSING + "PushProcedure": "push",
    SENSING + "PolledProcedure": "pull",
}

# `?litres` is joined through the PROPERTY the domain's valuation is denominated in rather than
# through the subject alone. Three sensors on one board can monitor one plant, so the subject
# cannot say which reading a litre of water moves — `market:aboutProperty` can, and it says
# soil moisture. Without that join a dose would warm the thermometer.
#
# NO DOMAIN TERM IS NAMED, and that is the contract rather than a nicety. The term that
# carries `market:aboutProperty` IS the lot-per-property conversion — the domain states it on
# each subject as the physics (`ag:fern water:litresPerFraction 2.0`) — so the query binds
# ?conversion from the denomination and uses it as the predicate. Swap the domain and its own
# valuation term (watts per degree, litres per fraction) joins here with this file unchanged,
# which is what "the domain is a plug-in" demands of a generator.
#
# It was `water:hasTarget` interpolated by name, then `water:litresPerFraction` after #120
# deleted the first — and the dead-name interval matched nothing silently: every generated
# SIM_VALUES lost its "litres", every dose moved nothing, and the first live run of the
# verification arc flagged the world for false knowledge. The interpolated-IRI failure mode
# the kernel vocabulary (packages/orexis-modality-graph/ontology.py) warns about, caught by exactly the detector built to catch it — and the
# lesson is not "name the right term" but "name no term", which this now does.
_SIMULATED_Q = f"""
SELECT ?id ?readingTopic ?commandTopic ?senseMode ?tick ?doseTopic ?drainTopic ?port
       ?pointer ?initial ?loses ?subjectLoses ?swing ?litres ?doseEffect ?minValue ?maxValue
       ?subjectMax ?scale ?rainTopic
WHERE {{
  ?d <{AG}localId> ?id ; <{SIM}simulatedBy> ?deviceModel ; <{MQTT}readingTopic> ?readingTopic ;
     <{MQTT}onBus> ?onBus .
  ?s <{MQTT}readingTopic> ?readingTopic ; <{SIM}simulatedBy> ?model ;
     <{SENSING}monitors> ?subject .
  OPTIONAL {{ ?d <{MQTT}commandTopic> ?commandTopic }}
  OPTIONAL {{ ?d <{SENSING}senseMode> ?senseMode }}
  OPTIONAL {{ ?deviceModel <{SIM}tickSeconds> ?tick }}
  OPTIONAL {{ ?s <{MQTT}readingPointer> ?pointer }}
  OPTIONAL {{ ?model <{SIM}initialValue> ?initial }}
  OPTIONAL {{ ?model <{SIM}losesPerDay> ?loses }}
  OPTIONAL {{ ?model <{SIM}dailySwing> ?swing }}
  OPTIONAL {{ ?model <{SIM}minValue> ?minValue }}
  OPTIONAL {{ ?model <{SIM}maxValue> ?maxValue }}
  OPTIONAL {{ ?s <{SOSA}observes> ?wetProperty .
             ?conversion <{MARKET}aboutProperty> ?wetProperty .
             ?subject ?conversion ?litres .
             # The subject's own loss rate (#164), riding the same denomination join: the
             # property water moves is the property that drains, so the physics reaches
             # exactly the valued channel and never the thermometer beside it. The kernel
             # term is read — a domain's own word (water:driesPerDay) arrives entailed
             # through its subproperty bridge, so no domain is named here either.
             OPTIONAL {{ ?subject <{SIM}losesPerDay> ?subjectLoses }} }}
  OPTIONAL {{ ?valve <{ACTUATION}actuates> ?subject ; <{MQTT}statusTopic> ?doseTopic }}
  # The SUPPLY side of the same wire (the barrel learns to run dry): a level stand-in watches
  # every valve that DRAWS from its subject — the litre that fills a pot lowers the barrel.
  OPTIONAL {{ ?drainer <{ACTUATION}drawsFrom> ?subject ; <{MQTT}statusTopic> ?drainTopic }}
  # A subject may carry the model's ceiling by entailment (water:capacityL is a subproperty
  # of sim:maxValue) — one statement, the #164 pattern, read here like the drying is.
  OPTIONAL {{ ?subject <{SIM}maxValue> ?subjectMax }}
  OPTIONAL {{ ?subject <{SIM}doseEffect> ?doseEffect }}
  OPTIONAL {{ ?w a <{AG}World> ; <{SIM}timeScale> ?scale }}
  OPTIONAL {{ ?subject <{SIM}rainTopic> ?rainTopic }}
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerPort> ?port .
 }}"""


def _values(rows: list[dict]) -> str:
    """What this device reports, as the JSON its firmware is handed.

    A pointer per property, defaulted to `/value` for the one that states none — which is what a
    single-property board sends and what `agent/pointer.py` reads when a sensor says nothing.
    Sorted so regenerating an unchanged world produces an unchanged file.
    """
    specs = []
    seen_pointers = set()
    for row in sorted(rows, key=lambda r: r.get("pointer") or "/value"):
        # One spec per VALUE: the drain-topic join (a source hears several valves) multiplies
        # rows without multiplying values, so a pointer builds its spec exactly once.
        if (row.get("pointer") or "/value") in seen_pointers:
            continue
        seen_pointers.add(row.get("pointer") or "/value")
        spec = {"pointer": row.get("pointer") or "/value"}
        # An explicitly modelled loss is an OVERRIDE; absent one, the subject's own
        # physics (entailed from its domain's word — water:driesPerDay, #164) is the fact.
        if row.get("loses") in (None, "") and row.get("subjectLoses") not in (None, ""):
            row = {**row, "loses": row["subjectLoses"]}
        # The supply side rides the same entailments: the subject's dose effect (a water
        # source's -1.0, conservation stated once on the class) is what a DRAINED litre
        # does, its own "drains" key now that a barrel can also be dosed — it used to
        # override "litres", which was right exactly as long as no subject was on both
        # sides of the wire. The entailed ceiling (water:capacityL) is still the max where
        # the model states none, and "litres" keeps meaning what a DOSED litre converts by
        # (a pot's litres-per-fraction, a barrel's litres-per-stored-litre — both arrive
        # through the denomination join, neither named).
        if row.get("maxValue") in (None, "") and row.get("subjectMax") not in (None, ""):
            row = {**row, "maxValue": row["subjectMax"]}
        for key, field in (("min", "minValue"), ("max", "maxValue"),
                           ("initial", "initial"), ("loses", "loses"), ("swing", "swing"),
                           ("litres", "litres"), ("drains", "doseEffect")):
            if row.get(field) not in (None, ""):
                spec[key] = float(row[field])
        specs.append(spec)
    return json.dumps(specs, separators=(",", ":"))


# The world's one meddler, and only if the world states sim:strayDoseMeanDays: which pots can be
# rained on, how often on average, and at what pace the world runs.
_MEDDLER_Q = f"""
SELECT DISTINCT ?rainTopic ?strayDays ?scale ?port WHERE {{
  ?w a <{AG}World> ; <{SIM}strayDoseMeanDays> ?strayDays .
  ?subject <{SIM}rainTopic> ?rainTopic .
  OPTIONAL {{ ?w <{SIM}timeScale> ?scale }}
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerPort> ?port .
 }}"""


def _meddler(world: str, rows: list[dict]) -> str:
    """Somebody who waters the pots and never asks — its own image, its own credential.

    NOT part of the sensor image, deliberately: a pot must not water itself, and a stand-in
    that secretly did could never be told from one whose physics were broken. The ACL grants
    this principal WRITE on each rain topic and nothing else, so the worst a compromised
    meddler can do is be over-generous with water.
    """
    row = rows[0]
    topics = json.dumps(sorted({r["rainTopic"] for r in rows}), separators=(",", ":"))
    scale = f'\n      MEDDLER_TIMESCALE: "{row["scale"]}"' if row.get("scale") else ""
    return f"""
  sim-meddler:
    build:
      context: ../../firmware/simulated-meddler
    image: orexis-meddler:local
    environment:
      MEDDLER_TOPICS: '{topics}'
      MEDDLER_MEAN_DAYS: "{row["strayDays"]}"{scale}
      MQTT_HOST: "localhost"
      MQTT_PORT: "{int(row["port"])}"
    env_file:
      - ./secrets/mqtt-meddler.env
    network_mode: host
    restart: unless-stopped
"""


def _persist_looks(world: str) -> int:
    """The constitutional debounce (#180), read from the merged T-Box the way orexis-firmware
    reads it for the boards: a stand-in must rehearse the same N consecutive looks, or the
    simulation promises a faster messenger than any real pot has."""
    from .namespaces import SENSING
    rows = ratified.rows(ratified.dataset(world), f"""
SELECT ?n WHERE {{ <{SENSING}SensingCapability> <{SENSING}alarmPersistenceLooks> ?n }} LIMIT 1""")
    return int(float(rows[0]["n"])) if rows else 2


def _simulator(world: str, rows: list[dict]) -> str:
    """One container per stand-in, mirroring one container per agent.

    So one principal holds one credential and the ACL model is unchanged — the broker cannot
    tell this from a board, and neither can anything else. It reuses the agent image because it
    needs one library that image already has; a second image for a hundred-line script would be
    another thing to build and keep current, for nothing.

    Takes every row for one device rather than one row, because a device reports a value per
    property and the container is the device. What varies per value goes into `SIM_VALUES`; what
    is true of the whole board — its identity, its topics, who holds its clock — stays here.
    """
    row = rows[0]
    sim_id = row["id"]
    mode = _SIM_MODE.get(row.get("senseMode") or "", "scheduled")
    # A device may GAIN on some channels and LOSE on others, and the sign is which side of
    # the wire each topic is on — so the two sets travel separately, each sorted so an
    # unchanged world regenerates an unchanged file. A pot has dose topics only (the valve
    # that actuates it); a source used to have drain topics only (every valve that draws
    # from it) and the two were unioned into one env var, which was right until the barrel
    # learned to fill: it now hears the city's valve RAISE its stock through the same kind
    # of status message the plant valves LOWER it with, and only the set membership can say
    # which is which.
    dose_topics = ",".join(sorted({r.get("doseTopic") for r in rows if r.get("doseTopic")}))
    drain_topics = ",".join(sorted({r.get("drainTopic") for r in rows if r.get("drainTopic")}))
    optional = "".join(
        f'\n      {k}: "{v}"' for k, v in (
            ("SIM_COMMAND_TOPIC", row.get("commandTopic")),
            ("SIM_DOSE_TOPIC", dose_topics),
            ("SIM_DRAIN_TOPIC", drain_topics),
            ("SIM_TICK_SECONDS", row.get("tick")),
            # The world's clock (sim:timeScale), handed to every stand-in alike, because
            # physics that age at different rates stop composing. And the rain channel
            # (sim:rainTopic) — where the meddler's water arrives, if this world has one.
            ("SIM_TIMESCALE", row.get("scale")),
            ("SIM_RAIN_TOPIC", row.get("rainTopic")),
            # The society's debounce (#180), the same figure the boards compile in.
            ("SIM_ALARM_PERSIST_LOOKS", _persist_looks(world)),
        ) if v not in (None, ""))
    return f"""
  sim-{sim_id}:
    build:
      # its own directory: it needs one file, and the repo root is excluded from image
      # contexts anyway — the agent image must not carry the simulator, nor it the agent
      context: ../../firmware/simulated-sensor
    image: orexis-simulator:local
    environment:
      SIM_SENSOR_ID: "{sim_id}"
      SIM_READING_TOPIC: "{row['readingTopic']}"
      # What this board reports and where each value goes in its one message. A part that
      # reports two properties down one line is a list of two; a probe is a list of one.
      SIM_VALUES: '{_values(rows)}'
      # sensing:ScheduledProcedure keeps the interval its agent gives it, like a deep-sleeping board;
      # sensing:PushProcedure keeps its own clock and takes no orders. The agent derives its capability
      # from the same fact and never learns which side of it this is.
      SIM_SENSE_MODE: "{mode}"
      MQTT_HOST: "localhost"
      MQTT_PORT: "{int(row['port'])}"{optional}
    env_file:
      # its own credential, minted by `orexis-mqtt` exactly as a board's is — the broker has no
      # way to tell a stand-in from hardware, which is the point
      - ./secrets/mqtt-{sim_id}.env
    network_mode: host
    restart: unless-stopped
"""


_SIM_VALVES_Q = f"""
SELECT ?id ?commandTopic ?statusTopic ?mlPerSecond ?maxDoseMl ?port
WHERE {{ 
  ?v <{AG}localId> ?id ; <{SIM}simulatedBy> ?model ; <{ACTUATION}actuates> ?subject ;
     <{MQTT}commandTopic> ?commandTopic ; <{MQTT}statusTopic> ?statusTopic .
  OPTIONAL {{ ?v <{ACTUATION}mlPerSecond> ?mlPerSecond }}
  OPTIONAL {{ ?v <{ACTUATION}maxDoseMl> ?maxDoseMl }}
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerPort> ?port .
 }}"""


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
    image: orexis-valve:local
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
      # its own credential, minted by `orexis-mqtt` exactly as a real valve's would be
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

    plain, tls = _bus_ports(world)
    # One row per value, grouped back into one container per device: the query cannot return a
    # list, and the device is what gets a container, a credential and a clock.
    simulated: dict[str, list[dict]] = {}
    for row in ratified.rows(ratified.dataset(world), _SIMULATED_Q):
        simulated.setdefault(row["id"], []).append(row)
    valves = ratified.rows(ratified.dataset(world), _SIM_VALVES_Q)
    meddler = ratified.rows(ratified.dataset(world), _MEDDLER_Q)
    services = _broker(world, plain, tls) + "".join(
        _simulator(world, simulated[sim_id]) for sim_id in sorted(simulated)) + "".join(
        _valve(world, row) for row in sorted(valves, key=lambda r: r["id"])) + (
        _meddler(world, meddler) if meddler else "") + "".join(
        _service(a, caps, world) for a, caps in who.items())
    volumes = f"  orexis-{world}-mosquitto:\n" + "".join(
        f"  orexis-{world}-{a}:\n" for a in who)
    return f"""# GENERATED by `orexis-compose {world}` from the world.ttl beside it — do not edit.
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

name: orexis-{world}

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
        prog="orexis-compose",
        description="Generate the compose file for a world, from that world's roster.",
    )
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
