"""orexis-firmware — a board's config.h, from the world it belongs to.

  orexis-firmware sensing              every board in that world
  orexis-firmware sensing --board esp32_fern

**Everything in a `config.h` is a per-instance deployment fact**, and every one of them was
already written down somewhere else. The broker's port is the `schema:url` on the world's
`mqtt4ssn:Broker`; the ids and topics are the world's, in MQTT4SSN's words; the pins and the
calibration are the hardware's; the credential was minted by `orexis-mqtt`; a sentinel's heartbeat
is its sensor's stated `ssn-system:Frequency`. The world is read as an Agent 0.2.0 boot reads it
(`agent.runtime.world_of`). Keeping a second copy in a C header is the
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

from agent.runtime import world_of
from agent.store import graphs_of, rows as _rows_of
from .worlds import REPO_ROOT
from .worlds import world_dir, worlds
from .mqtt import broker
from .namespaces import BME280, DHT11, ESP32, I2C, MC, ONEWIRE, PROBE, RGBLED

OREXIS = "http://example.org/orexis#"
SENSING = "http://example.org/orexis/sensing#"
SOSA = "http://www.w3.org/ns/sosa/"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
PUBLIC = OREXIS + "PublicGraph"

#  THE SOCIETY'S FIGURES for a sentinel, which the 0.1.0 sensing capability stated and Agent 0.2.0
#  has no capability to state them on: a move of a quarter of the band since the last report wakes
#  the board, two breaching looks in a row make the news real, and a governed board's cadence stays
#  between ten seconds and fifteen minutes.
WAKE_DELTA_FRACTION = 0.25
PERSIST_LOOKS = 2
SLEEP_BOUNDS_S = (10, 900)


def _world(world: str):
    return world_of(world_dir(world))


def _rows(store, text: str) -> list[dict]:
    return _rows_of(store, text, graphs_of(store, PUBLIC))



log = logging.getLogger("firmware")

FIRMWARE_ROOT = REPO_ROOT / "firmware"
WIFI_ENV = REPO_ROOT / "infra" / "secrets" / "wifi.env"

# Every board that states which firmware it runs, with the probe every such board carries and
# the OPTIONAL parts this generator has a template for — an LED, a DHT11, a BME280. A board
# carrying something it has no template for is reported (_untemplated), not guessed at.
_BOARDS_Q = f"""
SELECT ?boardId ?firmware ?lan ?sensorId ?readTopic ?cmdTopic ?gpio ?rawDry ?rawWet
       ?alarm
       ?ledRed ?ledGreen ?ledBlue ?airPin ?bmeSda ?bmeScl ?bmeAddr ?ws2812
WHERE {{
  ?board a <{MC}Microcontroller> ; <{OREXIS}localId> ?boardId ; <{MQTT4SSN}hosts> ?sensor .
  # The firmware name: stated on the board directly, or — since #175 — entailed onto the
  # board's connecting DEVICE from its firmware class, and reached through the hosting the
  # deployment produces. Two spellings of one fact, and either satisfies the query.
  {{ ?board <{MC}firmware> ?firmware }}
  UNION
  {{ ?board <{MQTT4SSN}hosts> ?fwBearer . ?fwBearer <{MC}firmware> ?firmware }}
  ?sensor a <{PROBE}CapacitiveMoistureProbe> ; <{OREXIS}localId> ?sensorId ;
          <{MQTT4SSN}observesTopic> ?topic ;
          <{PROBE}rawDry> ?rawDry ; <{PROBE}rawWet> ?rawWet .
  ?filter <{MQTT4SSN}matchesTopic> ?topic ; <{MQTT4SSN}hasFilterPattern> ?readTopic .
  OPTIONAL {{ ?board <{MQTT4SSN}listensToTopic> ?cmd . ?cmdFilter <{MQTT4SSN}matchesTopic> ?cmd ;
                     <{MQTT4SSN}hasFilterPattern> ?cmdTopic }}
  #  Whether the board promises announce-on-crossing (#151), stated on the sensor.
  OPTIONAL {{ ?sensor <http://www.w3.org/ns/ssn/implements> <{SENSING}AlarmProcedure> . BIND(true AS ?alarm) }}
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
  OPTIONAL {{ ?board <{MQTT4SSN}hosts> ?led . ?led a <{RGBLED}RgbLed> ;
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
  OPTIONAL {{ ?board <{MQTT4SSN}hosts> ?air .
             ?air <{MC}hasPin> ?airLeg .
             ?airLeg <{MC}pinRole> <{ONEWIRE}DataPinRole> .
             ?aw <{MC}joins> ?airLeg, ?airPinNode . ?airPinNode <{MC}gpio> ?airPin }}
  # The BME280, matched on its CLASS and not only on the I2C roles — the roles say which two
  # lines to open a bus on, and the class says what to say down it. An I2C part this firmware
  # has no driver for must be reported (see _untemplated), not driven as a BME280 because it
  # happens to have an SDA leg. The address is the unit's, by its SDO strap, and defaults in
  # the firmware to 0x76 when the world states none.
  OPTIONAL {{ ?board <{MQTT4SSN}hosts> ?bme . ?bme a <{BME280}Bme280> ;
                <{MC}hasPin> ?sdaLeg, ?sclLeg .
             ?sdaLeg <{MC}pinRole> <{I2C}DataPinRole>  . ?sdaW <{MC}joins> ?sdaLeg, ?sdaPin . ?sdaPin <{MC}gpio> ?bmeSda .
             ?sclLeg <{MC}pinRole> <{I2C}ClockPinRole> . ?sclW <{MC}joins> ?sclLeg, ?sclPin . ?sclPin <{MC}gpio> ?bmeScl .
             OPTIONAL {{ ?bme <{I2C}address> ?bmeAddr }} }}
  # A BUILT-IN status LED, from no wire: a FireBeetle 2 ESP32-E carries a WS2812 on GPIO 5 by
  # construction, and the world's hardware.ttl states it of the board.
  OPTIONAL {{ ?board <{ESP32}ws2812Gpio> ?ws2812 }}
 }}"""

# Every part a board hosts that has legs, with its classes — so a part this generator has no
# template for is REPORTED rather than silently left out of the header it would have needed
# a line in. The templates are the OPTIONAL blocks above; this is their complement.
_HOSTED_Q = f"""
SELECT ?boardId ?partId ?class WHERE {{
  ?board a <{MC}Microcontroller> ; <{OREXIS}localId> ?boardId ; <{MQTT4SSN}hosts> ?part .
  ?part <{MC}hasPin> ?leg ; a ?class .
  OPTIONAL {{ ?part <{OREXIS}localId> ?partId }}
 }}"""

# The classes the header above knows how to describe. A part whose classes meet none of these
# gets a warning naming it, which is the whole of what this generator can honestly do for it.
_TEMPLATED = (f"{PROBE}CapacitiveMoistureProbe", f"{RGBLED}RgbLed", f"{DHT11}Dht11",
              f"{BME280}Bme280")

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


def _untemplated(store, board: str) -> list[str]:
    """The parts on this board the header says nothing about, by id."""
    classes: dict[str, set[str]] = {}
    for r in _rows(store, _HOSTED_Q):
        if r["boardId"] == board:
            classes.setdefault(r.get("partId") or "(unnamed)", set()).add(r["class"])
    return sorted(p for p, c in classes.items() if not c & set(_TEMPLATED))



_SENTINEL_Q = """
SELECT ?lo ?hi ?every ?unit WHERE {{
  ?s <{OREXIS}localId> "{sensor_id}" ; <{SOSA}isHostedBy> ?subject ; <{SOSA}observes> ?p .
  ?subject <http://www.w3.org/ns/ssn/systems/hasOperatingRange>/<http://www.w3.org/ns/ssn/systems/inCondition> ?c .
  ?c <http://www.w3.org/ns/ssn/forProperty> ?p ; <https://schema.org/minValue> ?lo ; <https://schema.org/maxValue> ?hi .
  OPTIONAL {{ ?s <http://www.w3.org/ns/ssn/systems/hasSystemCapability>/<http://www.w3.org/ns/ssn/systems/hasSystemProperty> ?f .
             ?f a <http://www.w3.org/ns/ssn/systems/Frequency> ; <https://schema.org/value> ?every ;
                <https://schema.org/unitCode> ?unit }} }} LIMIT 1"""

_SECONDS = {"SEC": 1, "MIN": 60, "HR": 3600, "HUR": 3600, "DAY": 86400}


def render_sentinel(world: str, row: dict, store) -> str:
    """config.h for the SECOND firmware (#151): a sentinel takes no orders, so its config
    carries what a command would have — the deviation limit, sized from the WORLD's operating range
    for the subject it watches, and a heartbeat that is the cadence the world states for it.

    The rest of what the board carries — an LED, a DHT11, a BME280, a built-in WS2812 — is the
    same wiring question for either temperament, so `_optional_pins` answers it for both."""
    creds = world_dir(world) / "secrets" / f"mqtt-{row['sensorId']}.env"
    user, password = _env(creds, "MQTT_USERNAME"), _env(creds, "MQTT_PASSWORD")
    if not password:
        raise SystemExit(f"no credential for {row['sensorId']} — run `orexis-mqtt {world}` first")
    ssid, wifi_pass = _wifi()
    broker = row.get("lan") or row["host"]

    found = _rows(store, _SENTINEL_Q.format(OREXIS=OREXIS, SOSA=SOSA, sensor_id=row["sensorId"]))
    if not found:
        raise SystemExit(f"{row['sensorId']}: a sentinel watches the world's operating range, "
                         f"and its subject states none for the observed property")
    lo, hi = float(found[0]["lo"]), float(found[0]["hi"])
    if not found[0].get("every"):
        raise SystemExit(f"{row['sensorId']}: a sentinel's heartbeat is the cadence the world states "
                         f"for it, and it states no ssn-system:Frequency")
    heartbeat = int(float(found[0]["every"]) * _SECONDS.get(found[0]["unit"].rsplit("/", 1)[-1], 1))
    delta = round(WAKE_DELTA_FRACTION * (hi - lo), 3)
    persist = PERSIST_LOOKS

    return f"""// GENERATED by `orexis-firmware {world}` for {row['boardId']} — do not edit.
//
// A SENTINEL's config carries what a command would have (#151): this board takes no orders,
// so the band comes from the world's own operating range and the heartbeat is the cadence the
// world states for this sensor. Regenerate after either changes.
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

// The cadence the world states for this sensor (its ssn-system:Frequency): the agent expects a
// reading this often and calls one missed past it, so board and agent keep one heartbeat.
#define HEARTBEAT_S {heartbeat}

// How many consecutive breaching looks make the news real (#180) — the society's figure, the
// same the governed node compiles, because what counts as evidence is the society's to say.
#define WAKE_PERSIST_LOOKS {persist}

// The deviation limit (a quarter of the band, the society's figure): an in-band move of more than
// this since the last report wakes the board — a stranger's water on a comfortable pot.
#define WAKE_DELTA {delta}
"""

def generate(world: str, board: str | None = None) -> None:
    store = _world(world)
    host, port, _ = broker(world)
    rows = [{**r, "host": host, "port": port}
            for r in _rows(store, _BOARDS_Q) if board is None or r["boardId"] == board]
    if not rows:
        raise SystemExit(
            f"orexis-firmware: no board in world {world!r}"
            + (f" called {board!r}" if board else " states mc:firmware and carries a probe"))
    bounds = SLEEP_BOUNDS_S

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
            out.write_text(render_sentinel(world, row, store))
        else:
            out.write_text(render(world, row, bounds, PERSIST_LOOKS))
        out.chmod(0o600)  # it carries this board's password
        log.info("  wrote %s  (%s -> %s:%s, pin %s)", out.relative_to(REPO_ROOT),
                 row["boardId"], row.get("lan") or row["host"], row["port"], row["gpio"])
        for part in _untemplated(store, row["boardId"]):
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
