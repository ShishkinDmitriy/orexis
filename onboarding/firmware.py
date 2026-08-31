"""orexis-firmware — a board's config.h, from the world it belongs to.

  orexis-firmware sensing              every board in that world
  orexis-firmware sensing --board esp32_fern

**Everything in a `config.h` is a per-instance deployment fact**, and every one of them was
already written down somewhere else. The broker and its port are in the world's `mqtt:MessageBus`;
the ids and topics are the society's; the pins are the hardware's; the credential was minted by
`orexis-mqtt`; the cadence bounds are the ontology's. Keeping a second copy in a C header is the
same second list this project refuses everywhere else — and it is the expensive kind, because
correcting it means physically retrieving a board.

This session paid that cost three times: a port change, a credential rotation, and a calibration
that could not be adjusted without a screwdriver.

**Two routes to one broker.** An agent reaches it at `mqtt:brokerHost`, which is loopback and must
be — agents are host-networked and every member has to agree on one name. A board on the wifi
cannot use that name, so it is given the `orexis:lanHost` of whichever host runs the broker. That
is a fact about the network, not about the society, which is why it hangs off the ComputeHost and
not the bus.

**What is NOT generated** is anything that is a property of the code rather than the deployment —
retry counts, the listen window, the ADC sampling. Those stay in the firmware where they belong.
The line is the same one drawn everywhere else here: if changing it means changing what this
board IS, it comes from the world; if it means changing how the firmware behaves, it is code.

The output is gitignored, like every other credential-bearing generated file.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from agent import ratified
from agent.config import REPO_ROOT
from agent.genesis import world_dir, worlds
from orexis_agent_progression.ontology import OREXIS, ONTOLOGY_GRAPH, WORLD_GRAPH
from .namespaces import BME280, DHT11, ESP32, I2C, MC, MQTT, ONEWIRE, PROBE, RGBLED, SENSING, SOSA



log = logging.getLogger("firmware")

FIRMWARE_ROOT = REPO_ROOT / "firmware"
WIFI_ENV = REPO_ROOT / "infra" / "secrets" / "wifi.env"

# Every board that states which firmware it runs, with the probe every such board carries and
# the OPTIONAL parts this generator has a template for — an LED, a DHT11, a BME280. A board
# carrying something it has no template for is reported (_untemplated), not guessed at.
_BOARDS_Q = f"""
SELECT ?boardId ?firmware ?lan ?host ?port ?sensorId ?readTopic ?cmdTopic ?gpio ?rawDry ?rawWet
       ?alarm
       ?ledRed ?ledGreen ?ledBlue ?airPin ?bmeSda ?bmeScl ?bmeAddr ?ws2812
WHERE {{
  ?board a <{MC}Microcontroller> ; <{OREXIS}localId> ?boardId ; <{SOSA}hosts> ?sensor .
  # The firmware name: stated on the board directly, or — since #175 — entailed onto the
  # board's connecting DEVICE from its firmware class, and reached through the hosting the
  # deployment produces. Two spellings of one fact, and either satisfies the query.
  {{ ?board <{MC}firmware> ?firmware }}
  UNION
  {{ ?board <{SOSA}hosts> ?fwBearer . ?fwBearer <{MC}firmware> ?firmware }}
  ?sensor a <{PROBE}CapacitiveMoistureProbe> ; <{OREXIS}localId> ?sensorId ;
          <{MQTT}readingTopic> ?readTopic ;
          <{PROBE}rawDry> ?rawDry ; <{PROBE}rawWet> ?rawWet .
  OPTIONAL {{ ?sensor <{MQTT}commandTopic> ?cmdTopic }}
  # Whether the board's connecting device promises announce-on-crossing (#151) — the same
  # stream-and-bus join every other device fact makes since #96.
  OPTIONAL {{ ?watcher <{MQTT}readingTopic> ?readTopic ; <{MQTT}onBus> ?wBus ;
              <http://www.w3.org/ns/ssn/implements>
                <http://example.org/orexis/sensing#AlarmProcedure> .
             BIND(true AS ?alarm) }}
  ?bus a <{MQTT}MessageBus> ; <{MQTT}brokerHost> ?host ; <{MQTT}brokerPort> ?port .
  OPTIONAL {{ ?pi a <{OREXIS}ComputeHost> ; <{OREXIS}lanHost> ?lan }}

  # Which LINE a leg is on is now two facts and a wire: the role belongs to the peripheral's
  # pin, the number to the board's, and only the wire knows they are the same connection. That
  # is the whole point of the remodelling, and it costs this query one hop per pin.
  ?sensor <{MC}hasPin> ?probeLeg .
  ?probeLeg <{MC}pinRole> <{MC}AnalogInPinRole> .
  ?probeWire <{MC}joins> ?probeLeg, ?probePin .
  ?probePin <{MC}gpio> ?gpio .

  # All OPTIONAL and all separate, because a board without a status LED is an ordinary board
  # and must still generate — the alternative is a query that silently returns no rows and a
  # generator that reports the world states no boards at all.
  OPTIONAL {{ ?board <{SOSA}hosts> ?led . ?led a <{RGBLED}RgbLed> ;
                <{MC}hasPin> ?rLeg, ?gLeg, ?bLeg .
             ?rLeg <{MC}pinRole> <{RGBLED}RedPinRole>   . ?rw <{MC}joins> ?rLeg, ?rPin . ?rPin <{MC}gpio> ?ledRed .
             ?gLeg <{MC}pinRole> <{RGBLED}GreenPinRole> . ?gw <{MC}joins> ?gLeg, ?gPin . ?gPin <{MC}gpio> ?ledGreen .
             ?bLeg <{MC}pinRole> <{RGBLED}BluePinRole>  . ?bw <{MC}joins> ?bLeg, ?bPin . ?bPin <{MC}gpio> ?ledBlue }}
  # Matched on the ROLE rather than on the device class, and it stays that way now that asking
  # for the parent class would work — the entailments are materialised before anything reads
  # them (see orexis/inference.py), so the reason this was written defensively is gone. The role
  # is what the firmware actually needs to know anyway: this is the pin it must bit-bang,
  # whatever part is on the end of it. Matching the class would be asking a question whose
  # answer it would then have to translate.
  OPTIONAL {{ ?board <{SOSA}hosts> ?air .
             ?air <{MC}hasPin> ?airLeg .
             ?airLeg <{MC}pinRole> <{ONEWIRE}DataPinRole> .
             ?aw <{MC}joins> ?airLeg, ?airPinNode . ?airPinNode <{MC}gpio> ?airPin }}
  # The BME280, matched on its CLASS and not only on the I2C roles — the roles say which two
  # lines to open a bus on, and the class says what to say down it. An I2C part this firmware
  # has no driver for must be reported (see _untemplated), not driven as a BME280 because it
  # happens to have an SDA leg. The address is the unit's, by its SDO strap, and defaults in
  # the firmware to 0x76 when the world states none.
  OPTIONAL {{ ?board <{SOSA}hosts> ?bme . ?bme a <{BME280}Bme280> ;
                <{MC}hasPin> ?sdaLeg, ?sclLeg .
             ?sdaLeg <{MC}pinRole> <{I2C}DataPinRole>  . ?sdaW <{MC}joins> ?sdaLeg, ?sdaPin . ?sdaPin <{MC}gpio> ?bmeSda .
             ?sclLeg <{MC}pinRole> <{I2C}ClockPinRole> . ?sclW <{MC}joins> ?sclLeg, ?sclPin . ?sclPin <{MC}gpio> ?bmeScl .
             OPTIONAL {{ ?bme <{I2C}address> ?bmeAddr }} }}
  # A BUILT-IN status LED, from the board's CLASS rather than from any wire: a FireBeetle 2
  # ESP32-E carries a WS2812 on GPIO 5 by construction, stated once as a restriction in
  # packages/orexis-part-esp32 and carried to this unit by the closure. Nothing in a world's
  # hardware.ttl says it, and nothing could unsay it.
  OPTIONAL {{ ?board <{ESP32}ws2812Gpio> ?ws2812 }}
 }}"""

# Every part a board hosts that has legs, with its classes — so a part this generator has no
# template for is REPORTED rather than silently left out of the header it would have needed
# a line in. The templates are the OPTIONAL blocks above; this is their complement.
_HOSTED_Q = f"""
SELECT ?boardId ?partId ?class WHERE {{
  ?board a <{MC}Microcontroller> ; <{OREXIS}localId> ?boardId ; <{SOSA}hosts> ?part .
  ?part <{MC}hasPin> ?leg ; a ?class .
  OPTIONAL {{ ?part <{OREXIS}localId> ?partId }}
 }}"""

# The classes the header above knows how to describe. A part whose classes meet none of these
# gets a warning naming it, which is the whole of what this generator can honestly do for it.
_TEMPLATED = (f"{PROBE}CapacitiveMoistureProbe", f"{RGBLED}RgbLed", f"{DHT11}Dht11",
              f"{BME280}Bme280")

_BOUNDS_Q = f"""
SELECT ?min ?max WHERE {{ 
  <{SENSING}SensingCapability> <{SENSING}minSleepS> ?min ; <{SENSING}maxSleepS> ?max  }} LIMIT 1"""


def _env(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def _wifi() -> tuple[str, str]:
    """The site's wifi, which is infrastructure and belongs to no world.

    Not in the world graph on purpose: every world on this bench shares one network, and a
    society should not have opinions about an SSID.
    """
    ssid, password = _env(WIFI_ENV, "WIFI_SSID"), _env(WIFI_ENV, "WIFI_PASS")
    if not ssid or not password:
        raise SystemExit(
            f"no wifi credentials: create {WIFI_ENV.relative_to(REPO_ROOT)} with WIFI_SSID and "
            "WIFI_PASS. It is the site's network, not any world's, which is why it lives in "
            "infra/secrets/ and not in a world.ttl.")
    return ssid, password


def render(world: str, row: dict, bounds: tuple[int, int], persist: int = 2) -> str:
    creds = world_dir(world) / "secrets" / f"mqtt-{row['sensorId']}.env"
    user, password = _env(creds, "MQTT_USERNAME"), _env(creds, "MQTT_PASSWORD")
    if not password:
        raise SystemExit(f"no credential for {row['sensorId']} in "
                         f"{creds.relative_to(REPO_ROOT)} — run `orexis-mqtt {world}` first")
    ssid, wifi_pass = _wifi()
    # A board is not on the host, so loopback is meaningless to it. Fall back to the stated
    # broker host only when no ComputeHost publishes a LAN host — which will not work, and
    # says so, rather than silently writing "localhost" into a board's flash.
    broker = row.get("lan") or row["host"]
    if not row.get("lan"):
        log.warning("  ! no orexis:lanHost on any ComputeHost — writing %r, which a board on the "
                    "wifi cannot reach", broker)
    lo, hi = bounds
    return f"""// GENERATED by `orexis-firmware {world}` from that world — do not edit.
//
// Every value below is a fact the world already states: the broker and its port from the
// mqtt:MessageBus, the ids and topics from the society, the pin from the wiring, the credential
// from `orexis-mqtt`, the cadence bounds from the ontology. Editing this file makes it disagree
// with the world, and the world is what the agents believe.
//
// Regenerate after any of those change:  orexis-firmware {world}
#pragma once

// The site's network. Infrastructure, not a world's business — infra/secrets/wifi.env.
#define WIFI_SSID "{ssid}"
#define WIFI_PASS "{wifi_pass}"

// This world's broker, at the LAN host of the host running it. Agents reach the same broker
// at mqtt:brokerHost (loopback); a board cannot, so it is given the route that works from the wifi.
#define MQTT_HOST "{broker}"
#define MQTT_PORT {int(row['port'])}

// Who this board is on the bus. The broker refuses anonymous clients, and its ACL grants this
// principal exactly the topics below and nothing else.
#define MQTT_USER "{user}"
#define MQTT_PASS "{password}"

// Who this instrument is. NOT what it is monitoring: a probe does not know which plant it sits
// in, and has no use for the answer. Which subject a reading is ABOUT is the world's statement
// and the agent's to apply — the board is handed one identifier, its own, exactly as an agent
// process is. It used to carry a PLANT_ID, left over from when topics were built as
// "sensors/<plant>/moisture" rather than read from mqtt:readingTopic.
#define SENSOR_ID "{row['sensorId']}"
#define MOISTURE_TOPIC "{row['readTopic']}"
#define CMD_TOPIC "{row.get('cmdTopic', '')}"

// Where the probe is wired, and what its numbers mean — both facts about this probe in this
// pot, which is why they are here and not in the firmware. The firmware is per model; these are
// per instance, and two identical probes differ.
#define MOISTURE_PIN {int(row['gpio'])}
#define ADC_DRY {int(row['rawDry'])}
#define ADC_WET {int(row['rawWet'])}
{_optional_pins(row)}
// The constitutional bounds, from the ontology rather than compiled in twice: the agent will not
// ask for a cadence outside these, and the board will not honour one.
#define MIN_SLEEP_S {lo}
#define MAX_SLEEP_S {hi}
{_crossing(row, persist)}"""


def _crossing(row: dict, persist: int = 2) -> str:
    """The announce-on-crossing promise (#151), compiled in only where the world states it.

    A define rather than a runtime flag because the ULP machinery is real code with a real
    footprint, and a board whose world makes no such promise should not carry the means to
    keep it — absence stays a statement, in the firmware exactly as in the graph.
    """
    if not row.get("alarm"):
        return ""
    return ("\n// The world promises this board announces on crossing (#151): the ULP watches\n"
            "// the commanded band between heartbeats and wakes the radio when the value leaves it.\n"
            "#define WAKE_ON_ALARM 1\n"
            "// How many consecutive breaching looks make the news real (#180) — the society's\n"
            "// figure (sensing:alarmPersistenceLooks): one look is an ADC glitch, not physics.\n"
            f"#define WAKE_PERSIST_LOOKS {persist}\n")


def _persist_looks(ds) -> int:
    """The constitutional debounce (#180), read where the delta's default is read — and like
    it, a figure of the FAMILY's: what counts as evidence of a real event is the society's to
    say, so both temperaments compile the same answer."""
    n = ratified.rows(ds, f"""
SELECT ?n WHERE {{ <{SENSING}SensingCapability> <{SENSING}alarmPersistenceLooks> ?n }} LIMIT 1""")
    return int(float(n[0]["n"])) if n else 2


def _optional_pins(row: dict) -> str:
    """The rest of what the board carries, emitted only where the world states it.

    A `#define` that is absent rather than zero is deliberate: the firmware guards on `#ifdef`,
    so a board with no LED compiles the LED code out entirely instead of driving GPIO 0 — which
    is a strapping pin, and would hold the board in bootloader mode on the next reset.
    """
    out = []
    if row.get("ledRed"):
        out += [
            "",
            "// The status LED, from the world's wiring. Three driven legs and a common return; the",
            "// return goes to ground, which the world states as a wire like any other.",
            f"#define LED_RED_PIN {int(row['ledRed'])}",
            f"#define LED_GREEN_PIN {int(row['ledGreen'])}",
            f"#define LED_BLUE_PIN {int(row['ledBlue'])}",
        ]
    if row.get("airPin"):
        out += [
            "",
            "// The air sensor's data leg. Its two properties travel in the SAME message as the",
            "// moisture — one board is one client with one credential, so it publishes once —",
            "// and each is picked out by the mqtt:readingPointer its sensor states in the world.",
            f"#define AIR_SENSOR_PIN {int(row['airPin'])}",
        ]
    if row.get("bmeSda"):
        addr = int(row["bmeAddr"]) if row.get("bmeAddr") else 0x76
        out += [
            "",
            "// The BME280, over I2C on these two lines. Temperature, humidity and pressure travel",
            "// in the SAME message as the moisture, each picked out by the mqtt:readingPointer its",
            "// sensor states in the world. The address is the unit's SDO strap, from the wiring.",
            f"#define BME280_SDA_PIN {int(row['bmeSda'])}",
            f"#define BME280_SCL_PIN {int(row['bmeScl'])}",
            f"#define BME280_ADDR 0x{addr:02X}",
        ]
    if row.get("ws2812"):
        out += [
            "",
            "// The board's OWN status LED — an addressable WS2812 on this line, from the board",
            "// class rather than the wiring. Same outcome vocabulary as a wired KY-016; the",
            "// firmware drives it through the core's RMT driver and needs no library.",
            f"#define STATUS_LED_WS2812_PIN {int(row['ws2812'])}",
        ]
    return "\n".join(out) + "\n" if out else ""


def _untemplated(ds, board: str) -> list[str]:
    """The parts on this board the header says nothing about, by id."""
    classes: dict[str, set[str]] = {}
    for r in ratified.rows(ds, _HOSTED_Q):
        if r["boardId"] == board:
            classes.setdefault(r.get("partId") or "(unnamed)", set()).add(r["class"])
    return sorted(p for p, c in classes.items() if not c & set(_TEMPLATED))



_SENTINEL_Q = """
SELECT ?lo ?hi ?agentId WHERE {{
  ?s <{OREXIS}localId> "{sensor_id}" ; <{SENSING}monitors> ?subject ;
     <http://www.w3.org/ns/sosa/observes> ?prop .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?r .
  ?r <http://www.w3.org/ns/ssn/systems/inCondition> ?c .
  ?c <http://www.w3.org/ns/ssn/forProperty> ?prop ;
     <https://schema.org/minValue> ?lo ; <https://schema.org/maxValue> ?hi .
  OPTIONAL {{ ?agent <{SENSING}polls> ?s ; <{OREXIS}localId> ?agentId }}
 }}"""


def _max_reading_age(world: str, agent_id: str | None) -> int | None:
    """The polling agent's `sensing:maxReadingAgeS`, read from ITS beliefs file.

    Found on the sentinel template's first real run (world/terrace): the ratified dataset holds
    the PUBLIC graphs, and a freshness rule is a belief — private, in `beliefs/<agent>.ttl`,
    never in the world. So an OPTIONAL that asked the dataset for it bound nothing, silently,
    and every sentinel would have been compiled to the 750 s default whatever its agent
    believed — exactly the mismatch #323 warned would bite. The sovereign holds the beliefs
    files (it authored them), so the generator reads the one that matters here.
    """
    if not agent_id:
        return None
    path = world_dir(world) / "beliefs" / f"{agent_id}.ttl"
    if not path.exists():
        return None
    import rdflib
    g = rdflib.Graph().parse(path, format="turtle")
    for value in g.objects(None, rdflib.URIRef(f"{SENSING}maxReadingAgeS")):
        return int(value.toPython())
    return None


def render_sentinel(world: str, row: dict, ds) -> str:
    """config.h for the SECOND firmware (#151): a sentinel takes no orders, so its config
    carries what a command would have — the band, compiled from the WORLD's operating range
    for the pot it watches, and a heartbeat generated to fit under the polling agent's own
    Listening freshness rule so a healthy sentinel is never called stale.

    The rest of what the board carries — an LED, a DHT11, a BME280, a built-in WS2812 — is the
    same wiring question for either temperament, so `_optional_pins` answers it for both."""
    creds = world_dir(world) / "secrets" / f"mqtt-{row['sensorId']}.env"
    user, password = _env(creds, "MQTT_USERNAME"), _env(creds, "MQTT_PASSWORD")
    if not password:
        raise SystemExit(f"no credential for {row['sensorId']} — run `orexis-mqtt {world}` first")
    ssid, wifi_pass = _wifi()
    broker = row.get("lan") or row["host"]

    found = ratified.rows(ds, _SENTINEL_Q.format(OREXIS=OREXIS, SENSING=SENSING,
                                                 sensor_id=row["sensorId"]))
    if not found:
        raise SystemExit(f"{row['sensorId']}: a sentinel watches the world's operating range, "
                         f"and its subject states none for the observed property")
    lo, hi = float(found[0]["lo"]), float(found[0]["hi"])
    # Under the agent's absolute freshness rule with a fifth to spare, or its default when the
    # world grants no Listening yet: a heartbeat the agent would call stale is a lie on a timer.
    stated = _max_reading_age(world, found[0].get("agentId"))
    max_age = stated if stated is not None else 750
    heartbeat = max(60, int(max_age * 0.8))
    # The FAMILY's figure, deliberately, where a governed board is told its agent's own pick:
    # a sentinel takes no orders, so no revision could ever reach it, and baking anything but
    # the society's default would freeze one agent's passing opinion into a flash image.
    frac = ratified.rows(ds, f"""
SELECT ?f WHERE {{ <{SENSING}SensingCapability> <{SENSING}alarmDeltaFraction> ?f }} LIMIT 1""")
    delta = round((float(frac[0]["f"]) if frac else 0.25) * (hi - lo), 3)
    persist = _persist_looks(ds)

    return f"""// GENERATED by `orexis-firmware {world}` for {row['boardId']} — do not edit.
//
// A SENTINEL's config carries what a command would have (#151): this board takes no orders,
// so the band comes from the world's own operating range and the heartbeat is fitted under
// its agent's Listening freshness rule. Regenerate after either changes.
#pragma once

#define WIFI_SSID "{ssid}"
#define WIFI_PASS "{wifi_pass}"

#define MQTT_HOST "{broker}"
#define MQTT_PORT {int(row['port'])}
#define MQTT_USER "{user}"
#define MQTT_PASS "{password}"

#define SENSOR_ID "{row['sensorId']}"
#define MOISTURE_TOPIC "{row['readTopic']}"

#define MOISTURE_PIN {int(row['gpio'])}
#define ADC_DRY {int(row['rawDry'])}
#define ADC_WET {int(row['rawWet'])}
{_optional_pins(row)}
// NOT the band. A sentinel's ULP watches MOVEMENT — the last published value plus or minus
// WAKE_DELTA — and does not compare against the operating range at all; watching it made a pot
// outside its range wake the radio every patrol, forever. The range is still read here, because
// it is what SIZES the deviation limit below. See
// knowledge/decisions/the-sentinel-alarms-on-movement.md.

// Fitted under the polling agent's sensing:maxReadingAgeS ({max_age}s) with room to spare:
// a heartbeat the agent would call stale would make a healthy sentinel read as a dead one.
#define HEARTBEAT_S {heartbeat}

// How many consecutive breaching looks make the news real (#180) — the same constitutional
// figure the governed node compiles, because what counts as evidence is the society's to say.
#define WAKE_PERSIST_LOOKS {persist}

// The deviation limit (sensing:alarmDeltaFraction of the band): an in-band move of more than
// this since the last report wakes the board — a stranger's water on a comfortable pot.
#define WAKE_DELTA {delta}
"""

def generate(world: str, board: str | None = None) -> None:
    ds = ratified.dataset(world)
    rows = [r for r in ratified.rows(ds, _BOARDS_Q) if board is None or r["boardId"] == board]
    if not rows:
        raise SystemExit(
            f"orexis-firmware: no board in world {world!r}"
            + (f" called {board!r}" if board else " states mc:firmware and carries a probe"))
    b = ratified.rows(ds, _BOUNDS_Q)
    bounds = (int(b[0]["min"]), int(b[0]["max"])) if b else (5, 900)

    for row in rows:
        project = FIRMWARE_ROOT / row["firmware"]
        if not project.is_dir():
            raise SystemExit(f"{row['boardId']} states firmware {row['firmware']!r}, which is not "
                             f"a directory under firmware/")
        out = project / "include" / "config.h"
        out.parent.mkdir(parents=True, exist_ok=True)
        # Two firmwares, two temperaments, one dispatch: the governed node takes commands and
        # cadence bounds; the sentinel (#151) takes neither, and its config carries the band
        # and the heartbeat a command would otherwise have brought.
        # The outdoor sentinel is the sentinel copied onto another board with an air part
        # (#461); its config is the sentinel's template plus what `_optional_pins` adds.
        if row["firmware"] in ("moisture-sentinel", "outdoor-sentinel"):
            out.write_text(render_sentinel(world, row, ds))
        else:
            out.write_text(render(world, row, bounds, _persist_looks(ds)))
        out.chmod(0o600)  # it carries this board's password
        log.info("  wrote %s  (%s -> %s:%s, pin %s)", out.relative_to(REPO_ROOT),
                 row["boardId"], row.get("lan") or row["host"], row["port"], row["gpio"])
        for part in _untemplated(ds, row["boardId"]):
            log.warning("  ! %s carries %s, which this generator has no template for — the "
                        "header says nothing about it", row["boardId"], part)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-firmware",
        description="Generate a board's config.h from the world it belongs to.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--board", help="only this board, by its orexis:localId")
    args = p.parse_args()
    generate(args.world, args.board)


if __name__ == "__main__":
    main()
