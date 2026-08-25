"""orexis-wokwi — this world's hardware as a Wokwi project, drawn from its own statements.

  orexis-wokwi sensing        writes world/sensing/wokwi/diagram.json

A picture of what is soldered, generated rather than drawn, from exactly the triples
`orexis-validate` is checking. It cannot describe a stand that does not exist and cannot go stale
without somebody editing the world — which is the whole argument for generating it. A wiring
diagram maintained by hand is wrong the first time a jumper moves, and wrong SILENTLY, which is
worse than not having one.

**Wokwi rather than a drawing, because it RUNS.** wokwi.com renders the real DevKit with its real
header and the real parts, and then simulates the firmware on it. That is a different and better
thing than a diagram: the LED logic, the cadence handling and the calibration arithmetic can be
exercised against a board that does not exist, which is the same trick `world/simulation` plays
one layer up with containers speaking the real protocol.

**A part says how it draws in its OWN package.** `packages/part/dht11/` already states what a DHT11
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
from pathlib import Path

from agent.genesis import world_dir, worlds
from agent.ontology import AG, ONTOLOGY_GRAPH, WORLD_GRAPH
from .namespaces import DHT11, ESP32, I2C, MC, ONEWIRE, PROBE, RGBLED


log = logging.getLogger("wokwi")

SKOS = "http://www.w3.org/2004/02/skos/core#"
WOKWI = "http://example.org/orexis/wokwi#"

# How each device draws, from its class. Two OPTIONALs deep because a device without a Wokwi
# mapping is an ordinary device — it is reported and skipped, never guessed at.
_DEVICES_Q = f"""
SELECT ?device ?deviceId ?part ?attrs WHERE {{
  
    ?device <{MC}hasPin> ?anyPin .
    OPTIONAL {{ ?device <{AG}localId> ?deviceId }}
    ?device a ?class .
  
  
    ?class <{WOKWI}part> ?part .
    OPTIONAL {{ ?class <{WOKWI}attrs> ?attrs }}
  
}}"""

# Which of OUR roles each of that part's legs answers to. The join between a role and a drawing.
_DEVICES_PARTS_Q = f"""
SELECT ?class ?part WHERE {{ 
  ?class <{WOKWI}part> ?part  }}"""

_PART_PINS_Q = f"""
SELECT ?class ?role ?name WHERE {{ 
  ?class <{WOKWI}pin> ?p .
  ?p <{MC}pinRole> ?role ; <{WOKWI}name> ?name .
 }}"""

_PINS_Q = f"""
SELECT ?device ?pin ?notation ?wokwiName ?gpio ?role ?railVolts WHERE {{ 
  ?device <{MC}hasPin> ?pin .
  OPTIONAL {{ ?pin <{MC}gpio> ?gpio }}
  OPTIONAL {{ ?pin <{SKOS}notation> ?notation }}
  OPTIONAL {{ ?pin <{WOKWI}name> ?wokwiName }}
  OPTIONAL {{ ?pin <{MC}pinRole> ?role }}
  OPTIONAL {{ ?pin <{MC}railVolts> ?railVolts }}
 }}"""

_CLASSES_Q = f"""
SELECT ?device ?class WHERE {{  ?device a ?class  }}"""

_WIRES_Q = f"""
SELECT ?a ?b ?colour WHERE {{ 
  ?wire a <{MC}Wire> ; <{MC}joins> ?a , ?b .
  OPTIONAL {{ ?wire <{MC}colour> ?colour }}
  FILTER(STR(?a) < STR(?b))
 }}"""

_BOARDS_Q = f"""
SELECT ?device WHERE {{ 
  ?device a <{MC}Microcontroller>  }}"""

# Wokwi's canvas is pixels from the top-left. Every pin this stand uses is on the board's LEFT
# header, so the parts go to its left — a part on the right means every one of its wires crosses
# the whole board to reach a pin, which is what made them all trace the same corridor.
#
# Staggered in both axes rather than stacked in a column, for the same reason: parts at one
# `left` put their wires in one channel whatever their `top` is.
_BOARD_AT = (0, 0)
_PART_TOP = -140
_PART_STEP = 170
_PART_LEFT = (-260, -360)   # alternating, so neighbouring parts do not share a lane


def _local(uri: str) -> str:
    return uri.rstrip("#/").split("#")[-1].split("/")[-1]


def _ident(uri: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", _local(uri))


def _slug(name: str) -> str:
    """A Wokwi pin name as a Turtle-safe suffix. GND.1 is a legal pin and not a legal name."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name).lower()


def _placed(world: str) -> dict[str, dict]:
    """Where the parts already sit, if this world has been drawn before.

    Wokwi rewrites top/left as you drag, so a regeneration that ignored them would throw away
    the arranging every time the wiring changed — which is exactly when you would want the
    picture and least want to redo it.
    """
    out = world_dir(world) / "wokwi" / "diagram.json"
    if not out.exists():
        return {}
    try:
        doc = json.loads(out.read_text())
    except json.JSONDecodeError:
        return {}
    return {p["id"]: {"top": p["top"], "left": p["left"]}
            for p in doc.get("parts", []) if "top" in p and "left" in p}


def render(world: str) -> dict | None:
    """The stand as a Wokwi diagram.json, or None where a world declares no hardware."""
    ds = ratified.dataset(world)
    keep = _placed(world)
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

    parts, n = [], 0
    for device in sorted(drawable, key=lambda d: (d not in boards, d)):
        row = drawable[device]
        is_board = device in boards
        # Where a part SITS is the one thing here a person is better at deciding than a
        # generator, and Wokwi writes it back when you drag. So a position already on disk wins:
        # the generator owns what is connected, you own where it sits, and regenerating after a
        # rewire does not undo an afternoon of arranging.
        placed = keep.get(_ident(device))
        parts.append({
            "type": row["part"],
            "id": _ident(device),
            "top": placed["top"] if placed else (
                _BOARD_AT[0] if is_board else _PART_TOP + n * _PART_STEP),
            "left": placed["left"] if placed else (
                _BOARD_AT[1] if is_board else _PART_LEFT[n % len(_PART_LEFT)]),
            "attrs": (json.loads(row["attrs"]) if row.get("attrs") else {}) | _common(device),
        })
        if not is_board:
            n += 1

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
        "author": "orexis-wokwi",
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
        "GENERATED by `orexis-wokwi " + world + "` from that world's own statements.\n"
        "Do not edit: rewire in `hardware.ttl` and regenerate, or the picture starts lying.\n\n"
        "Open <https://wokwi.com/projects/new/esp32>, then paste `diagram.json` over the\n"
        "project's own.\n\n"
        "**Drag the parts about.** The generator owns what is connected; you own where it\n"
        "sits. Wokwi rewrites `top`/`left` as you drag, and regenerating keeps whatever is\n"
        "already there — so rewiring does not undo an afternoon of arranging. The starting\n"
        "layout is only a guess, and a guess about a picture is worth less than one look.\n\n"
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
    written = out_dir / "diagram.json"
    # relative where it can be, absolute otherwise. relative_to RAISES rather than falling back,
    # so a world outside the checkout — which is only ever a test, but still — turned a log line
    # into a crash after the file had already been written.
    log.info("  wrote %s  (%d parts, %d wires)",
             written.relative_to(REPO_ROOT) if written.is_relative_to(REPO_ROOT) else written,
             len(doc["parts"]), len(doc["connections"]))


# ------------------------------------------------------------------------------------------
# The other direction: a drawing DRAFTS a stand. It never becomes one.
#
# See knowledge/decisions/wokwi-drafts-it-the-world-ratifies-it.md. The short of it: the mapping
# above is invertible, so reading a diagram back is cheap — but Wokwi recovers the SHAPE of a
# wiring and none of its meaning. No calibration, no rails, no topics, no sense mode, no name a
# person would recognise. That is fine for a draft and disqualifying for a source.
#
# So what cannot be derived is emitted as an explicit marker rather than guessed. A draft that
# VALIDATES is worse than one that does not: it is the one nobody re-reads.
# ------------------------------------------------------------------------------------------

_TODO = "### TODO ###"


def _inverse(ds) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """part type -> our class, and per class, wokwi pin name -> our role.

    Refuses an ambiguous part rather than choosing. `wokwi-dht22` is `dht11:Dht11` today and
    would be ambiguous the day a real DHT22 is added, and picking one silently is how a draft
    comes out describing a part nobody owns.
    """
    by_part: dict[str, str] = {}
    for r in ratified.rows(ds, _DEVICES_PARTS_Q):
        if by_part.setdefault(r["part"], r["class"]) != r["class"]:
            raise SystemExit(
                f"orexis-wokwi: {r['part']!r} is claimed by more than one class "
                f"({by_part[r['part']]} and {r['class']}) — nothing says which to prefer")
    roles: dict[str, dict[str, str]] = {}
    for r in ratified.rows(ds, _PART_PINS_Q):
        roles.setdefault(r["class"], {})[r["name"]] = r["role"]
    return by_part, roles


def _qname(uri: str) -> str:
    """A prefixed name for a term, for readable output. Only the namespaces a draft can emit."""
    for pfx, ns in (("mc", MC), ("onewire", ONEWIRE), ("i2c", I2C), ("dht11", DHT11),
                    ("rgbled", RGBLED), ("probe", PROBE), ("esp32", ESP32), ("ag", AG)):
        if uri.startswith(ns):
            return f"{pfx}:{uri[len(ns):]}"
    return f"<{uri}>"


def draft(world: str, diagram: Path) -> str:
    """Turn a Wokwi diagram into a hardware.ttl draft. Never authoritative."""
    doc = json.loads(diagram.read_text())
    ds = ratified.dataset(world)
    by_part, roles = _inverse(ds)

    # A board is whatever Wokwi drew as one. Its legs are named by the connections rather than
    # declared, because a diagram lists only the pins something is wired to.
    boards = {p["id"] for p in doc.get("parts", []) if p["type"].startswith("board-")}
    unknown = sorted({p["type"] for p in doc.get("parts", [])
                      if p["type"] not in by_part and p["id"] not in boards})

    # A pin is "used" only where a wire joins two REAL things. Wokwi's serial monitor is one of
    # its own parts rather than something on the windowsill, so its connections are dropped —
    # and with them the board's TX and RX, which would otherwise arrive as legs no wire reaches.
    used: dict[str, set[str]] = {}
    for a, b, *_ in doc.get("connections", []):
        if a.startswith("$") or b.startswith("$") or ":" not in a or ":" not in b:
            continue
        for end in (a, b):
            part, pin = end.split(":", 1)
            used.setdefault(part, set()).add(pin)

    out = [f"# DRAFT, from {diagram.name}. Not a world yet.",
           "#",
           "# `orexis-wokwi --import` recovers the SHAPE of a wiring and none of its meaning: a",
           f"# diagram carries no calibration, no rails, no topics and no name a person would",
           f"# recognise. Every {_TODO} below is something Wokwi cannot say and you must.",
           "#",
           "# It is left deliberately unvalidatable. A draft that passes orexis-validate is the",
           "# one nobody re-reads.",
           "",
           "@prefix ag:    <http://example.org/orexis#> .",
           # The DRAFT's own individuals go into the world's namespace (a world owns
           # its individuals; ag: is the vocabulary's), spelled with the empty prefix.
           f"@prefix : <http://example.org/orexis/world/{world}#> .",
           "@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .",
           "@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .",
           f"@prefix mc:    <{MC}> .",
           f"@prefix wokwi: <{WOKWI}> .",
           f"@prefix onewire: <{ONEWIRE}> .",
           f"@prefix dht11: <{DHT11}> .",
           f"@prefix rgbled: <{RGBLED}> .",
           f"@prefix probe: <{PROBE}> .",
           ""]
    if unknown:
        out += [f"# NOT IMPORTED — no package claims these Wokwi parts: {', '.join(unknown)}",
                "# Add a directory under vocabulary/ that states wokwi:part for each, then",
                "# re-import. Guessing a class from a part name is how a draft acquires a",
                "# device nobody owns.", ""]

    for part in doc.get("parts", []):
        pid, ptype = part["id"], part["type"]
        if pid in boards:
            out += [f":{pid} a mc:Microcontroller ;",
                    f'    ag:localId "{pid}" ;   # {_TODO} a name a person would use',
                    f'    mc:model "{_TODO}" ;',
                    f"    mc:logicVolts {_TODO} ;   # 3.3 for an ESP32; it decides what rail a part may take",
                    f"    mc:hasPin " + " , ".join(f":{pid}_{_slug(p)}"
                                                   for p in sorted(used.get(pid, ()))) + " .",
                    ""]
            for pin in sorted(used.get(pid, ())):
                gpio = f" mc:gpio {pin} ;" if pin.isdigit() else ""
                notation = pin.split(".")[0]
                out.append(f'ag:{pid}_{_slug(pin)} a mc:Pin ;{gpio} wokwi:name "{pin}" ; '
                           f'skos:notation "{notation}" .   # {_TODO} check the silkscreen')
            out.append("")
            continue
        if ptype not in by_part:
            continue
        cls = by_part[ptype]
        legs = roles.get(cls, {})
        out += [f":{pid} a {_qname(cls)} ;",
                f'    ag:localId "{pid}" ;   # {_TODO} a name a person would use',
                f'    mc:model "{_TODO}" ;',
                f"    mc:hasPin " + " , ".join(f":{pid}_{_slug(p)}"
                                               for p in sorted(used.get(pid, ()))) + " .",
                ""]
        for pin in sorted(used.get(pid, ())):
            role = legs.get(pin)
            out.append(f":{pid}_{_slug(pin)} a mc:Pin ; mc:pinRole "
                       + (_qname(role) if role else f"{_TODO}   # Wokwi calls this leg {pin!r}")
                       + " .")
        out.append("")

    out.append("# The wires, which are the part a diagram is actually good at.")
    for i, conn in enumerate(doc.get("connections", [])):
        a, b, colour = conn[0], conn[1], (conn[2] if len(conn) > 2 else "")
        if a.startswith("$") or b.startswith("$"):
            continue   # the simulator's console, not a thing on the windowsill
        pa, pina = a.split(":", 1)
        pb, pinb = b.split(":", 1)
        if pa not in used or pb not in used:
            continue
        col = f' ; mc:colour "{colour}"' if colour else ""
        out.append(f"ag:w{i} a mc:Wire ; mc:joins ag:{pa}_{_slug(pina)} , "
                   f":{pb}_{_slug(pinb)}{col} .")
    return "\n".join(out) + "\n"


def import_diagram(world: str, diagram: Path) -> None:
    out = world_dir(world) / "hardware.ttl"
    if out.exists():
        raise SystemExit(
            f"orexis-wokwi: {out} already exists. An import DRAFTS a stand; it does not "
            f"reconcile one. Move it aside if you mean to start over.")
    out.write_text(draft(world, diagram))
    todos = out.read_text().count(_TODO)
    log.info("  drafted %s", out)
    log.warning("  %d things Wokwi cannot say — the draft will not validate until you say them",
                todos)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-wokwi",
        description="Draw this world's stand as a Wokwi project, from its own statements.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--import", dest="source", type=Path, metavar="DIAGRAM",
                   help="the other direction: DRAFT a hardware.ttl from a Wokwi diagram.json. "
                        "Never authoritative — see decisions/wokwi-drafts-it-the-world-"
                        "ratifies-it.md")
    args = p.parse_args()
    if args.source:
        import_diagram(args.world, args.source)
    else:
        generate(args.world)


if __name__ == "__main__":
    main()
