"""orexis-wireviz — the wiring as a WireViz harness, from the world's own statements.

  orexis-wireviz sensing        writes world/sensing/wiring.yaml

Documentation of what is actually plugged in where, generated rather than drawn. It comes from
exactly the triples `orexis-validate` checks, so it cannot describe a stand that does not exist
and cannot go stale without somebody editing the world.

**WireViz because our model is already a harness.** Its vocabulary is connectors with named pins
and cables with coloured wires, which is what `mc:Pin`, `mc:Wire` and `mc:colour` are. Nothing
has to be flattened or invented to say it — unlike a node graph, which had no way to express a
pin belonging to a device, or a simulator, which wanted behaviour we do not have.

It renders to SVG, PNG and HTML, and needs Graphviz to do it:

    pip install wireviz && apt install graphviz
    wireviz world/sensing/wiring.yaml

The YAML is committed and the render is not. The YAML is the thing that diffs — a changed wire
is one changed line in a pull request — and a rendered SVG of a graph layout diffs as noise.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from agent import ratified
from agent.config import REPO_ROOT
from agent.genesis import world_dir, worlds
from orexis_modality_graph.ontology import AG, ONTOLOGY_GRAPH, WORLD_GRAPH
from .namespaces import DHT11, ESP32, I2C, MC, ONEWIRE, PROBE, RGBLED, SOSA



log = logging.getLogger("wireviz")

SKOS = "http://www.w3.org/2004/02/skos/core#"

# WireViz names colours by two-letter code. Ours are the words on the jumper, so they are
# translated here rather than stored in their form: the world should say "red" because that is
# what the wire IS, not "RD" because that is what one renderer calls it.
_COLOURS = {
    "black": "BK", "brown": "BN", "red": "RD", "orange": "OG", "yellow": "YE",
    "green": "GN", "blue": "BU", "violet": "VT", "purple": "VT", "grey": "GY",
    "gray": "GY", "white": "WH", "pink": "PK", "turquoise": "TQ",
}

_PINS_Q = f"""
SELECT ?device ?deviceId ?model ?pin ?notation ?gpio ?role WHERE {{ 
  ?device <{MC}hasPin> ?pin .
  OPTIONAL {{ ?device <{AG}localId> ?deviceId }}
  OPTIONAL {{ ?device <{MC}model> ?model }}
  OPTIONAL {{ ?pin <{SKOS}notation> ?notation }}
  OPTIONAL {{ ?pin <{MC}gpio> ?gpio }}
  OPTIONAL {{ ?pin <{MC}pinRole> ?role }}
 }}"""

# ORDER BY is load-bearing, not tidiness. This feeds a COMMITTED artefact, and SPARQL promises
# nothing about the order of an unordered result — so the harness's wire order was whatever the
# store happened to scan, and a diff appeared the moment public knowledge became five graphs
# instead of one. `colors:` and the pins it pairs with are both built from these rows, so they
# stay consistent whatever the order; what was missing was any guarantee it would not change
# under the next unrelated edit.
_WIRES_Q = f"""
SELECT ?a ?b ?colour WHERE {{
  ?wire a <{MC}Wire> ; <{MC}joins> ?a , ?b .
  OPTIONAL {{ ?wire <{MC}colour> ?colour }}
  FILTER(STR(?a) < STR(?b))
 }} ORDER BY ?a ?b"""

_BOARDS_Q = f"""
SELECT ?device WHERE {{ 
  ?device a <{MC}Microcontroller>  }}"""


def _local(uri: str) -> str:
    return uri.rstrip("#/").split("#")[-1].split("/")[-1]


def _label(row: dict) -> str:
    """What to print against the pin: the silkscreen where there is one, the role otherwise.

    The same split the wiring itself has. A board leg is identified by what is printed on it;
    a peripheral leg has no marking of its own and is known by what it is for.
    """
    if row.get("notation"):
        return row["notation"]
    if row.get("role"):
        return _local(row["role"]).replace("PinRole", "")
    return _local(row["pin"])


def render(world: str) -> str | None:
    """The stand as WireViz YAML, or None where a world declares no hardware."""
    ds = ratified.dataset(world)
    pins = ratified.rows(ds, _PINS_Q)
    if not pins:
        return None
    boards = {r["device"] for r in ratified.rows(ds, _BOARDS_Q)}
    wires = ratified.rows(ds, _WIRES_Q)

    by_device: dict[str, list[dict]] = {}
    for r in pins:
        by_device.setdefault(r["device"], []).append(r)

    partner = {}
    for w in wires:
        partner[w["a"]] = w["b"]
        partner[w["b"]] = w["a"]

    def board_key(r: dict) -> tuple:
        # Power and ground first, then ascending GPIO — the order you wire in, and the order
        # somebody checking a board reads the header in.
        role = _local(r.get("role") or "")
        return (0 if role in ("PowerPinRole", "GroundPinRole") else 1,
                int(r["gpio"]) if r.get("gpio") else 0, _label(r))

    order: dict[str, list[dict]] = {}
    for device, rows in by_device.items():
        if device in boards:
            order[device] = sorted(rows, key=board_key)
    for device, rows in by_device.items():
        if device in boards:
            continue
        # A peripheral's legs are listed in the order of the board pins they reach, so the two
        # connectors read down the page together and a wire crossing is a wire crossing rather
        # than an artefact of two arbitrary sortings.
        board_at = {r["pin"]: i for b in order for i, r in enumerate(order[b])}
        order[device] = sorted(rows, key=lambda r: board_at.get(partner.get(r["pin"], ""), 99))

    names = {d: (rows[0].get("deviceId") or _local(d)) for d, rows in order.items()}
    index = {r["pin"]: i + 1 for rows in order.values() for i, r in enumerate(rows)}

    out = [f"# GENERATED by `orexis-wireviz {world}` from that world's own statements.",
           "# Do not edit: rewire in hardware.ttl and regenerate, or the document starts lying.",
           "#",
           "#   pip install wireviz && apt install graphviz",
           f"#   wireviz world/{world}/wiring.yaml",
           "",
           "connectors:"]
    for device in sorted(order, key=lambda d: (d not in boards, names[d])):
        rows = order[device]
        model = rows[0].get("model")
        out.append(f"  {names[device]}:")
        if model:
            out.append(f"    type: {model}")
        out.append("    pinlabels: [" + ", ".join(_label(r) for r in rows) + "]")

    # One cable per pair of devices rather than one per jumper. That is what it looks like on
    # the bench — three leads to the same module run together — and it turns ten anonymous
    # wires into four labelled runs.
    runs: dict[tuple[str, str], list[dict]] = {}
    for w in wires:
        da = next(d for d, rows in order.items() if any(r["pin"] == w["a"] for r in rows))
        db = next(d for d, rows in order.items() if any(r["pin"] == w["b"] for r in rows))
        key = (da, db) if (da in boards or db not in boards) else (db, da)
        runs.setdefault(key, []).append(w)

    out.append("")
    out.append("cables:")
    for (da, db), ws in sorted(runs.items(), key=lambda kv: (names[kv[0][0]], names[kv[0][1]])):
        colours = [_COLOURS.get((w.get("colour") or "").lower(), "WH") for w in ws]
        out += [f"  {names[da]}-to-{names[db]}:",
                f"    wirecount: {len(ws)}",
                "    colors: [" + ", ".join(colours) + "]"]

    out.append("")
    out.append("connections:")
    for (da, db), ws in sorted(runs.items(), key=lambda kv: (names[kv[0][0]], names[kv[0][1]])):
        cable = f"{names[da]}-to-{names[db]}"
        ends = [(w["a"], w["b"]) if _owner(order, w["a"]) == da else (w["b"], w["a"])
                for w in ws]
        left = [index[a] for a, _ in ends]
        right = [index[b] for _, b in ends]
        out += ["  -",
                f"    - {names[da]}: [" + ", ".join(str(i) for i in left) + "]",
                f"    - {cable}: [" + ", ".join(str(i + 1) for i in range(len(ws))) + "]",
                f"    - {names[db]}: [" + ", ".join(str(i) for i in right) + "]"]
    return "\n".join(out) + "\n"


def _owner(order: dict[str, list[dict]], pin: str) -> str:
    return next(d for d, rows in order.items() if any(r["pin"] == pin for r in rows))


# ------------------------------------------------------------------------------------------
# The other direction: a harness DRAFTS a stand. It never becomes one.
#
# Same principle as the Wokwi import, and recorded in the same place —
# decisions/wokwi-drafts-it-the-world-ratifies-it.md. WireViz suits drafting better than a
# diagram does, because its YAML is meant to be TYPED: it carries the names you chose and the
# models you wrote, where a drawing gave back `sen1` and nothing else.
#
# What it still cannot say is what a part IS. `type: KY-015 (DHT11)` is free text; nothing in it
# picks dht11:Dht11 out of the vocabulary, and guessing from a string is how a draft acquires a
# device nobody owns. That, and everything in world.ttl, is marked rather than invented.
# ------------------------------------------------------------------------------------------

_TODO = "### TODO ###"

# What a part is CALLED in a catalogue, and therefore what an authoring tool will have written
# in its `type:` field. This is the link that turns free text into a class without guessing.
_MODELS_Q = f"""
SELECT ?class ?name ?board WHERE {{ 
  ?class <{MC}modelName> ?name .
  OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#subClassOf>*
                     <{MC}Microcontroller> . BIND(true AS ?board) }}
 }}"""

_ROLES_Q = f"""
SELECT ?role WHERE {{ 
  ?role a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <{MC}PinRole>  }}"""


def _roles(ds) -> dict[str, str]:
    """label as this module prints it -> the role IRI. The inverse of _label()."""
    out = {}
    for r in ratified.rows(ds, _ROLES_Q):
        out[_local(r["role"]).replace("PinRole", "")] = r["role"]
    return out


def draft(world: str, harness: Path) -> str:
    """Turn a WireViz harness into a hardware.ttl draft. Never authoritative."""
    import yaml

    doc = yaml.safe_load(harness.read_text())
    ds = ratified.dataset(world)
    roles = _roles(ds)

    conns = doc.get("connectors", {})
    cables = doc.get("cables", {})

    models, is_board_class = {}, set()
    for r in ratified.rows(ds, _MODELS_Q):
        models[r["name"]] = r["class"]
        if r.get("board"):
            is_board_class.add(r["class"])

    # Which connector is the BOARD stops being a guess as soon as its type resolves: a class
    # under mc:Microcontroller IS the board. Only where nothing resolves does this fall back to
    # the connector every cable touches, which is the usual answer and still a guess.
    resolved = {n: models.get((s or {}).get("type", "")) for n, s in conns.items()}
    board = next((n for n, c in resolved.items() if c in is_board_class), None)
    guessed = board is None
    if guessed:
        touched: dict[str, int] = {}
        for group in doc.get("connections", []):
            for entry in group:
                for key in entry:
                    if key in conns:
                        touched[key] = touched.get(key, 0) + 1
        board = max(touched, key=touched.get) if touched else None

    out = [f"# DRAFT, from {harness.name}. Not a world yet.",
           "#",
           "# A harness says what is plugged into what. It does not say what anything IS: the",
           "# part classes, the rails, the calibration and everything in world.ttl are absent",
           f"# from it by nature. Every {_TODO} is one of those.",
           "#",
           "# Left deliberately unvalidatable. A draft that passes orexis-validate is the one",
           "# nobody re-reads.",
           "",
           "@prefix ag:    <http://example.org/orexis#> .",
           # The DRAFT's own individuals go into the world's namespace (a world owns
           # its individuals; ag: is the vocabulary's), spelled with the empty prefix.
           f"@prefix : <http://example.org/orexis/world/{world}#> .",
           "@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .",
           f"@prefix mc:      <{MC}> .",
           f"@prefix onewire: <{ONEWIRE}> .",
           f"@prefix i2c:     <{I2C}> .",
           f"@prefix dht11:   <{DHT11}> .",
           f"@prefix rgbled:  <{RGBLED}> .",
           f"@prefix probe:   <{PROBE}> .",
           f"@prefix esp32:   <{ESP32}> .",
           f"@prefix sosa:    <{SOSA}> .",
           ""]

    pin_id: dict[tuple[str, int], str] = {}
    for name, spec in conns.items():
        labels = spec.get("pinlabels") or spec.get("pins") or []
        cls = resolved.get(name)
        kind = _qname(cls) if cls else ("mc:Microcontroller" if name == board else "mc:Peripheral")
        note = ("   # GUESSED: nothing here resolved to a board, so this is the connector every"
                " cable touches" if name == board and guessed else "")
        out += [f":{name} a {kind} ;{note}",
                f'    ag:localId "{name}" ;']
        if spec.get("type"):
            out.append(f'    mc:model "{spec["type"]}" ;')
        if not cls:
            out.append(f"    # {_TODO} its class — nothing states mc:modelName "
                       f"{spec.get('type', '')!r}")
        if name == board:
            out.append(f"    mc:logicVolts {_TODO} ;   # decides what rail a part may take")
        if name == board:
            # What the board CARRIES, derived from what is wired to it. Not the same statement
            # as a wire — carrying is mounting, and a peripheral can be carried and unwired —
            # but a harness only knows connections, and every generator that walks a board
            # starts from sosa:hosts. Leaving it out drafted a stand nothing downstream could
            # find its parts in.
            carried = sorted(n for n in conns if n != board)
            if carried:
                out.append("    sosa:hosts " + " , ".join(f":{c}" for c in carried) + " ;")
        out.append("    mc:hasPin " + " , ".join(f":{name}_{i+1}"
                                                 for i in range(len(labels))) + " .")
        out.append("")
        if name == board:
            out.append("# A board's general-purpose leg has no role — it is general purpose until")
            out.append("# something is wired to it. A RAIL leg does: give it mc:PowerPinRole and")
            out.append("# mc:railVolts, or mc:GroundPinRole, or the rail check has nothing to read.")
        for i, label in enumerate(labels):
            pin_id[(name, i + 1)] = f":{name}_{i+1}"
            role = roles.get(str(label))
            gpio = f" mc:gpio {label} ;" if str(label).isdigit() else ""
            if role:
                out.append(f":{name}_{i+1} a mc:Pin ;{gpio} mc:pinRole {_qname(role)} .")
            elif name == board:
                out.append(f'ag:{name}_{i+1} a mc:Pin ;{gpio} skos:notation "{label}" .')
            else:
                out.append(f'ag:{name}_{i+1} a mc:Pin ; mc:pinRole {_TODO}   # labelled {label!r}')
        out.append("")

    out.append("# The wires, which are the part a harness is actually good at.")
    n = 0
    for group in doc.get("connections", []):
        ends, colours = [], []
        for entry in group:
            for key, pins in entry.items():
                if key in conns:
                    ends.append([(key, p) for p in pins])
                elif key in cables:
                    colours = cables[key].get("colors") or []
        if len(ends) != 2:
            continue
        inverse = {v: k for k, v in _COLOURS.items()}
        for i, (a, b) in enumerate(zip(*ends)):
            n += 1
            colour = inverse.get(colours[i] if i < len(colours) else "", "")
            col = f' ; mc:colour "{colour}"' if colour else ""
            out.append(f"ag:w{n} a mc:Wire ; mc:joins {pin_id[a]} , {pin_id[b]}{col} .")
    return "\n".join(out) + "\n"


def _qname(uri: str) -> str:
    for pfx, ns in (("mc", MC), ("onewire", ONEWIRE), ("i2c", I2C), ("dht11", DHT11),
                    ("rgbled", RGBLED), ("probe", PROBE), ("esp32", ESP32)):
        if uri.startswith(ns):
            return f"{pfx}:{uri[len(ns):]}"
    return f"<{uri}>"


def import_harness(world: str, harness: Path) -> None:
    out = world_dir(world) / "hardware.ttl"
    if out.exists():
        raise SystemExit(
            f"orexis-wireviz: {out} already exists. An import DRAFTS a stand; it does not "
            f"reconcile one. Move it aside if you mean to start over.")
    out.write_text(draft(world, harness))
    log.info("  drafted %s", out)
    log.warning("  %d things a harness cannot say — it will not validate until you say them",
                out.read_text().count(_TODO))


def generate(world: str) -> None:
    body = render(world)
    if body is None:
        log.info("  %s declares no hardware — nothing to document", world)
        return
    out = world_dir(world) / "wiring.yaml"
    out.write_text(body)
    log.info("  wrote %s", out.relative_to(REPO_ROOT) if out.is_relative_to(REPO_ROOT) else out)
    log.info("  render it:  wireviz %s", out)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-wireviz",
        description="Document this world's wiring as a WireViz harness, from its own statements.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--import", dest="source", type=Path, metavar="HARNESS",
                   help="the other direction: DRAFT a hardware.ttl from a WireViz harness. "
                        "Never authoritative — see decisions/"
                        "wokwi-drafts-it-the-world-ratifies-it.md")
    args = p.parse_args()
    if args.source:
        import_harness(args.world, args.source)
    else:
        generate(args.world)


if __name__ == "__main__":
    main()
