"""agora-wokwi — this world's hardware as a Wokwi project, drawn from its own statements.

  agora-wokwi sensing        writes world/sensing/wokwi/diagram.json

A picture of what is soldered, generated rather than drawn, from exactly the triples
`agora-validate` is checking. It cannot describe a stand that does not exist and cannot go stale
without somebody editing the world — which is the whole argument for generating it. A wiring
diagram maintained by hand is wrong the first time a jumper moves, and wrong SILENTLY, which is
worse than not having one.

**Wokwi rather than a drawing, because it RUNS.** wokwi.com renders the real DevKit with its real
header and the real parts, and then simulates the firmware on it. That is a different and better
thing than a diagram: the LED logic, the cadence handling and the calibration arithmetic can be
exercised against a board that does not exist, which is the same trick `world/simulation` plays
one layer up with containers speaking the real protocol.

**A part says how it draws in its OWN package.** `vocabulary/dht11/` already states what a DHT11
is and what legs it has; that it draws as `wokwi-dht22` with SDA/VCC/GND is the same kind of
fact. Adding a part stays "adding a directory", and the directory now knows how to draw itself.
A part that says nothing about Wokwi simply does not appear — and says so on the way past,
rather than being silently dropped.

The pin names of the BOARD are not stated here. Its legs already carry `skos:notation` — D34,
3V3, GND — which is what the silkscreen says and what Wokwi calls them, because both are naming
the same physical header. One of the two had to be authoritative and the silkscreen already was.
"""

from __future__ import annotations

import argparse
import json
import logging
import re

from agent import ratified
from agent.config import REPO_ROOT
from agent.genesis import world_dir, worlds
from agent.ontology import AG, MC, ONTOLOGY_GRAPH, WORLD_GRAPH

log = logging.getLogger("wokwi")

SKOS = "http://www.w3.org/2004/02/skos/core#"
WOKWI = "http://example.org/agora/wokwi#"

# How each device draws, from its class. Two OPTIONALs deep because a device without a Wokwi
# mapping is an ordinary device — it is reported and skipped, never guessed at.
_DEVICES_Q = f"""
SELECT ?device ?deviceId ?part ?attrs WHERE {{
  GRAPH <{WORLD_GRAPH}> {{
    ?device <{MC}hasPin> ?anyPin .
    OPTIONAL {{ ?device <{AG}localId> ?deviceId }}
    ?device a ?class .
  }}
  GRAPH <{ONTOLOGY_GRAPH}> {{
    ?class <{WOKWI}part> ?part .
    OPTIONAL {{ ?class <{WOKWI}attrs> ?attrs }}
  }}
}}"""

# Which of OUR roles each of that part's legs answers to. The join between a role and a drawing.
_PART_PINS_Q = f"""
SELECT ?class ?role ?name WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{
  ?class <{WOKWI}pin> ?p .
  ?p <{MC}pinRole> ?role ; <{WOKWI}name> ?name .
}} }}"""

_PINS_Q = f"""
SELECT ?device ?pin ?notation ?wokwiName ?gpio ?role ?railVolts WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?device <{MC}hasPin> ?pin .
  OPTIONAL {{ ?pin <{MC}gpio> ?gpio }}
  OPTIONAL {{ ?pin <{SKOS}notation> ?notation }}
  OPTIONAL {{ ?pin <{WOKWI}name> ?wokwiName }}
  OPTIONAL {{ ?pin <{MC}pinRole> ?role }}
  OPTIONAL {{ ?pin <{MC}railVolts> ?railVolts }}
}} }}"""

_CLASSES_Q = f"""
SELECT ?device ?class WHERE {{ GRAPH <{WORLD_GRAPH}> {{ ?device a ?class }} }}"""

_WIRES_Q = f"""
SELECT ?a ?b ?colour WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?wire a <{MC}Wire> ; <{MC}joins> ?a , ?b .
  OPTIONAL {{ ?wire <{MC}colour> ?colour }}
  FILTER(STR(?a) < STR(?b))
}} }}"""

_BOARDS_Q = f"""
SELECT ?device WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?device a <{MC}Microcontroller> }} }}"""

# Wokwi's canvas is in pixels from the top-left of the board. Laid out rather than computed:
# a generated position is a guess either way, and these put the parts clear of the header so the
# wires are followable before anyone drags anything.
_BOARD_AT = (0, 0)
_PART_ORIGIN = (-120, 300)
_PART_STEP = 130


def _local(uri: str) -> str:
    return uri.rstrip("#/").split("#")[-1].split("/")[-1]


def _ident(uri: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", _local(uri))


def render(world: str) -> dict | None:
    """The stand as a Wokwi diagram.json, or None where a world declares no hardware."""
    ds = ratified.dataset(world)
    pins = ratified.rows(ds, _PINS_Q)
    if not pins:
        return None

    boards = {r["device"] for r in ratified.rows(ds, _BOARDS_Q)}
    rails = {r["pin"] for r in pins if r.get("railVolts")}
    classes: dict[str, set] = {}
    for r in ratified.rows(ds, _CLASSES_Q):
        classes.setdefault(r["device"], set()).add(r["class"])

    # role -> wokwi pin name, per drawable class
    part_pins: dict[str, dict[str, str]] = {}
    for r in ratified.rows(ds, _PART_PINS_Q):
        part_pins.setdefault(r["class"], {})[r["role"]] = r["name"]

    drawable = {r["device"]: r for r in ratified.rows(ds, _DEVICES_Q)}
    for device in sorted(set(classes) & {p["device"] for p in pins} - set(drawable)):
        log.warning("  %s says nothing about how it draws — omitted", _local(device))

    # Wokwi's `common` attribute asks what the common leg is tied to, and the wiring answers.
    # It was briefly declared on the RGB LED's class, which is wrong twice over: it is a fact
    # about the part soldered here rather than about RGB LEDs, and stating it beside the wire
    # that determines it is how the two get to disagree. A rail means anode, ground means
    # cathode, and getting it backwards inverts every colour — which is the visible symptom,
    # and now a derived one.
    def _common(device: str) -> dict:
        for cls in classes.get(device, ()):
            if part_pins.get(cls, {}) and "COM" in part_pins[cls].values():
                for r in pins:
                    if r["device"] != device or not r.get("role"):
                        continue
                    if part_pins[cls].get(r["role"]) != "COM":
                        continue
                    for w in ratified.rows(ds, _WIRES_Q):
                        far = (w["b"] if w["a"] == r["pin"]
                               else w["a"] if w["b"] == r["pin"] else None)
                        if far is not None:
                            return {"common": "anode" if far in rails else "cathode"}
        return {}

    parts, top = [], _PART_ORIGIN[0]
    for device in sorted(drawable, key=lambda d: (d not in boards, d)):
        row = drawable[device]
        is_board = device in boards
        parts.append({
            "type": row["part"],
            "id": _ident(device),
            "top": _BOARD_AT[0] if is_board else top,
            "left": _BOARD_AT[1] if is_board else _PART_ORIGIN[1],
            "attrs": (json.loads(row["attrs"]) if row.get("attrs") else {}) | _common(device),
        })
        if not is_board:
            top += _PART_STEP

    # Every pin, resolved to the "partId:PIN" Wokwi wants. A board leg answers to its silkscreen;
    # a part leg answers to whatever that part's package says its role is called.
    named: dict[str, str] = {}
    for r in pins:
        device = r["device"]
        if device not in drawable:
            continue
        # wokwi:name, and nothing clever. It is what the simulator calls this leg, which is a
        # different fact from what is printed on it: Wokwi says 34 where the board says D34, and
        # GND.1/.2/.3 where the board says GND on all three legs. They agree on 3V3, which is
        # exactly how the mismatch went unnoticed — that was the one wire that drew.
        #
        # The bare number was briefly derived from mc:gpio here. It gave the right answer and
        # was the wrong shape: a rule about Wokwi's naming conventions, living in Python, where
        # nothing in the graph would show it and nothing would contradict it the day they change.
        # Stated on the pin, or — for a peripheral leg, which has no silkscreen of its own —
        # from what its part's package calls that role. Never from the notation: 3V3 is the one
        # leg where the two agree, and falling back to it would leave a rule in place that is
        # right once and silently wrong everywhere else.
        if r.get("wokwiName"):
            named[r["pin"]] = f"{_ident(device)}:{r['wokwiName']}"
        elif r.get("role"):
            for cls in classes.get(device, ()):
                if (name := part_pins.get(cls, {}).get(r["role"])):
                    named[r["pin"]] = f"{_ident(device)}:{name}"
                    break

    connections, unresolved = [], []
    for r in ratified.rows(ds, _WIRES_Q):
        a, b = named.get(r["a"]), named.get(r["b"])
        if a and b:
            # The colour the jumper actually is, where the world says. Otherwise a guess from
            # what the wire carries: red is live, black is a return, green is signal. Stating
            # it replaces a guess about the bench with a fact about it — which is what makes
            # the picture usable for finding one wire among nine identical ones.
            role = next((p.get("role") for p in pins if p["pin"] in (r["a"], r["b"])
                         and p.get("role")), "")
            colour = r.get("colour") or ("red" if role.endswith("PowerPinRole")
                                         else "black" if role.endswith("GroundPinRole")
                                         else "green")
            connections.append([a, b, colour, []])
        else:
            unresolved.append((_local(r["a"]), _local(r["b"])))
    for a, b in unresolved:
        log.warning("  %s -- %s could not be named for Wokwi — omitted", a, b)

    # Wokwi's serial monitor, wired to whichever board there is. Not in our graph and it should
    # not be: it is not a thing on the windowsill, it is the simulator's console. But this
    # firmware's whole diagnostic story is the serial line — the moisture reading and its raw
    # count, the air sensor, which attempt the broker refused — so a simulation without it
    # would run and tell you nothing.
    for board in sorted(boards & set(drawable)):
        connections += [[f"{_ident(board)}:TX", "$serialMonitor:RX", "", []],
                        [f"{_ident(board)}:RX", "$serialMonitor:TX", "", []]]

    return {
        "version": 1,
        "author": "agora-wokwi",
        "editor": "wokwi",
        "parts": parts,
        "connections": sorted(connections),
    }


def generate(world: str) -> None:
    doc = render(world)
    if doc is None:
        log.info("  %s declares no hardware — nothing to draw", world)
        return
    out_dir = world_dir(world) / "wokwi"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diagram.json").write_text(json.dumps(doc, indent=2) + "\n")
    (out_dir / "README.md").write_text(
        f"# {world} — the stand, on wokwi.com\n\n"
        "GENERATED by `agora-wokwi " + world + "` from that world's own statements.\n"
        "Do not edit: rewire in `hardware.ttl` and regenerate, or the picture starts lying.\n\n"
        "Open <https://wokwi.com/projects/new/esp32>, then paste `diagram.json` over the\n"
        "project's own. The parts and every wire come from the world; where they SIT is a\n"
        "starting layout and yours to drag.\n\n"
        "**The soil sensor is a custom chip, not a catalogue part.** Its `chip-` prefix means\n"
        "the project must also carry `soil-moisture-sensor.chip.json` and `.chip.c` — take\n"
        "them from any published soil-moisture project. Without them the diagram fails to\n"
        "load with nothing pointing at the cause.\n\n"
        "It simulates, which is the point of choosing Wokwi over a drawing: build\n"
        "`firmware/moisture-sensor` and the LED logic, the cadence handling and the\n"
        "calibration arithmetic can be exercised against a board that does not exist. The\n"
        "serial monitor is wired, because this firmware's whole diagnostic story is that\n"
        "line — the reading and its raw count, the air sensor, which attempt the broker\n"
        "refused.\n")
    log.info("  wrote %s  (%d parts, %d wires)",
             (out_dir / "diagram.json").relative_to(REPO_ROOT),
             len(doc["parts"]), len(doc["connections"]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-wokwi",
        description="Draw this world's stand as a Wokwi project, from its own statements.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
