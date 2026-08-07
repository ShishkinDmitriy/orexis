"""agora-firmware — a board's config.h, from the world it belongs to.

  agora-firmware sensing              every board in that world
  agora-firmware sensing --board esp32_fern

**Everything in a `config.h` is a per-instance deployment fact**, and every one of them was
already written down somewhere else. The broker and its port are in the world's `ag:MessageBus`;
the ids and topics are the society's; the pins are the stand's; the credential was minted by
`agora-mqtt`; the cadence bounds are the ontology's. Keeping a second copy in a C header is the
same second list this project refuses everywhere else — and it is the expensive kind, because
correcting it means physically retrieving a board.

This session paid that cost three times: a port change, a credential rotation, and a calibration
that could not be adjusted without a screwdriver.

**Two routes to one broker.** An agent reaches it at `ag:brokerHost`, which is loopback and must
be — agents are host-networked and every member has to agree on one name. A board on the wifi
cannot use that name, so it is given the `ag:lanAddress` of whichever host runs the broker. That
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
from agent.ontology import AG, ONTOLOGY_GRAPH, WORLD_GRAPH

log = logging.getLogger("firmware")

FIRMWARE_ROOT = REPO_ROOT / "firmware"
WIFI_ENV = REPO_ROOT / "infra" / "secrets" / "wifi.env"

# Every board that states which firmware it runs, with the one peripheral this generator knows
# how to describe. A board carrying something it has no template for is reported, not guessed at.
_BOARDS_Q = f"""
SELECT ?boardId ?firmware ?lan ?host ?port ?sensorId ?readTopic ?cmdTopic ?gpio ?rawDry ?rawWet
       ?ledRed ?ledGreen ?ledBlue ?airPin
WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?board a <{AG}Microcontroller> ; <{AG}localId> ?boardId ; <{AG}firmware> ?firmware ;
         <{AG}carries> ?sensor .
  ?sensor a <{AG}CapacitiveMoistureProbe> ; <{AG}localId> ?sensorId ;
          <{AG}readingTopic> ?readTopic ;
          <{AG}pin> [ <{AG}pinRole> <{AG}AnalogIn> ; <{AG}gpio> ?gpio ] ;
          <{AG}rawDry> ?rawDry ; <{AG}rawWet> ?rawWet .
  OPTIONAL {{ ?sensor <{AG}commandTopic> ?cmdTopic }}
  ?bus a <{AG}MessageBus> ; <{AG}brokerHost> ?host ; <{AG}brokerPort> ?port .
  OPTIONAL {{ ?pi a <{AG}ComputeHost> ; <{AG}lanAddress> ?lan }}

  # What else the same board carries. All OPTIONAL and all separate, because a board without a
  # status LED is an ordinary board and must still generate — the alternative is a query that
  # silently returns no rows and a generator that reports the world states no boards at all.
  OPTIONAL {{ ?board <{AG}carries> [ a <{AG}RgbLed> ;
                <{AG}pin> [ <{AG}pinRole> <{AG}Red>   ; <{AG}gpio> ?ledRed   ] ,
                          [ <{AG}pinRole> <{AG}Green> ; <{AG}gpio> ?ledGreen ] ,
                          [ <{AG}pinRole> <{AG}Blue>  ; <{AG}gpio> ?ledBlue  ] ] }}
  OPTIONAL {{ ?board <{AG}carries> [ a <{AG}TempHumiditySensor> ;
                <{AG}pin> [ <{AG}pinRole> <{AG}OneWireData> ; <{AG}gpio> ?airPin ] ] }}
}} }}"""

_BOUNDS_Q = f"""
SELECT ?min ?max WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{
  <{AG}PerceptionCapability> <{AG}minSleepS> ?min ; <{AG}maxSleepS> ?max }} }} LIMIT 1"""


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


def render(world: str, row: dict, bounds: tuple[int, int]) -> str:
    creds = world_dir(world) / "secrets" / f"mqtt-{row['sensorId']}.env"
    user, password = _env(creds, "MQTT_USERNAME"), _env(creds, "MQTT_PASSWORD")
    if not password:
        raise SystemExit(f"no credential for {row['sensorId']} in "
                         f"{creds.relative_to(REPO_ROOT)} — run `agora-mqtt {world}` first")
    ssid, wifi_pass = _wifi()
    # A board is not on the host, so loopback is meaningless to it. Fall back to the stated
    # broker host only when no ComputeHost publishes a LAN address — which will not work, and
    # says so, rather than silently writing "localhost" into a board's flash.
    broker = row.get("lan") or row["host"]
    if not row.get("lan"):
        log.warning("  ! no ag:lanAddress on any ComputeHost — writing %r, which a board on the "
                    "wifi cannot reach", broker)
    lo, hi = bounds
    return f"""// GENERATED by `agora-firmware {world}` from that world — do not edit.
//
// Every value below is a fact the world already states: the broker and its port from the
// ag:MessageBus, the ids and topics from the society, the pin from the stand, the credential
// from `agora-mqtt`, the cadence bounds from the ontology. Editing this file makes it disagree
// with the world, and the world is what the agents believe.
//
// Regenerate after any of those change:  agora-firmware {world}
#pragma once

// The site's network. Infrastructure, not a world's business — infra/secrets/wifi.env.
#define WIFI_SSID "{ssid}"
#define WIFI_PASS "{wifi_pass}"

// This world's broker, at the LAN address of the host running it. Agents reach the same broker
// at ag:brokerHost (loopback); a board cannot, so it is given the route that works from the wifi.
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
// "sensors/<plant>/moisture" rather than read from ag:readingTopic.
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
"""


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
            "// The status LED, from the stand. Three driven legs and a common return; the return",
            "// is solder rather than software and the world does not model it.",
            f"#define LED_RED_PIN {int(row['ledRed'])}",
            f"#define LED_GREEN_PIN {int(row['ledGreen'])}",
            f"#define LED_BLUE_PIN {int(row['ledBlue'])}",
        ]
    if row.get("airPin"):
        out += [
            "",
            "// Wired, and not yet published anywhere: one device reports two properties and the",
            "// model gives a sensor one. Emitted so the pin is claimed and nothing else takes it.",
            f"#define AIR_SENSOR_PIN {int(row['airPin'])}",
        ]
    return "\n".join(out) + "\n" if out else ""


def generate(world: str, board: str | None = None) -> None:
    ds = ratified.dataset(world)
    rows = [r for r in ratified.rows(ds, _BOARDS_Q) if board is None or r["boardId"] == board]
    if not rows:
        raise SystemExit(
            f"agora-firmware: no board in world {world!r}"
            + (f" called {board!r}" if board else " states ag:firmware and carries a probe"))
    b = ratified.rows(ds, _BOUNDS_Q)
    bounds = (int(b[0]["min"]), int(b[0]["max"])) if b else (5, 900)

    for row in rows:
        project = FIRMWARE_ROOT / row["firmware"]
        if not project.is_dir():
            raise SystemExit(f"{row['boardId']} states firmware {row['firmware']!r}, which is not "
                             f"a directory under firmware/")
        out = project / "include" / "config.h"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(world, row, bounds))
        out.chmod(0o600)  # it carries this board's password
        log.info("  wrote %s  (%s -> %s:%s, pin %s)", out.relative_to(REPO_ROOT),
                 row["boardId"], row.get("lan") or row["host"], row["port"], row["gpio"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-firmware",
        description="Generate a board's config.h from the world it belongs to.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--board", help="only this board, by its ag:localId")
    args = p.parse_args()
    generate(args.world, args.board)


if __name__ == "__main__":
    main()
