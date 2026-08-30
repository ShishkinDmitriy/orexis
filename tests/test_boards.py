"""Each part's own Wokwi board, held to what the vocabulary says that part is.

A drawing lives with the package that owns the part — `packages/orexis-part-rgb-led/wokwi/` — so it is
found by looking and deleted with it, rather than sitting in a tree of its own that nothing
would prune.

These are hand-written rather than generated: the geometry is measured once off a drawing and
never changes, and Wokwi needs the files at exact paths in its own format. What CAN drift is the
part of them that overlaps our model — which chip a board delegates to, and what its legs are
called — and that drift is the exact complaint that caused these boards to exist: Wokwi's RGB LED
is not wired in the order ours is.

So the overlap is checked and the geometry is not.
"""

from __future__ import annotations

import json

import pytest

from assembly import loader

from agent import ratified
from agent.config import REPO_ROOT
from orexis_modality_graph.ontology import ONTOLOGY_GRAPH
from onboarding.namespaces import MC
# Found by looking, like everything else: a part that has a Wokwi drawing keeps it beside its
# ontology, so `packages/orexis-part-rgb-led/wokwi/` travels with the package and is deleted with it.
# Keyed by the PART, which is the thing the vocabulary names — the vendor's "KY-016" appears
# only inside the files.
BOARDS = {p.name: p.path / "wokwi" for p in loader.of_kind("part")
          if (p.path / "wokwi" / "board.json").exists()}
WOKWI = "http://example.org/orexis/wokwi#"

_MAPPING_Q = f"""
SELECT ?part ?name ?role WHERE {{ 
  ?class <{WOKWI}part> ?part ; <{WOKWI}pin> ?p .
  ?p <{MC}pinRole> ?role ; <{WOKWI}name> ?name .
 }}"""


@pytest.fixture(scope="module")
def mapping():
    """part type -> {wokwi pin name -> our role}, as the vocabulary states it."""
    out: dict[str, dict[str, str]] = {}
    for r in ratified.rows(ratified.dataset("sensing"), _MAPPING_Q):
        out.setdefault(r["part"], {})[r["name"]] = r["role"]
    return out


def _board(part: str) -> dict:
    return json.loads((BOARDS[part] / "board.json").read_text())


def test_some_part_actually_carries_a_board():
    """The parametrisation below is discovered, so an empty discovery would pass every case
    below by having none. See issue #106."""
    assert BOARDS, "no part package carries a wokwi/board.json — this file checks nothing"


@pytest.mark.parametrize("name", sorted(BOARDS))
def test_a_board_is_complete(name):
    """Wokwi reads all of these, and a board missing one fails to load with a console error
    rather than anything pointing at the file."""
    doc = _board(name)
    assert {"name", "version", "width", "height", "chips", "pins"} <= set(doc)
    assert doc["chips"] and doc["pins"]
    assert (BOARDS[name] / "board.svg").exists()


@pytest.mark.parametrize("name", sorted(BOARDS))
def test_the_svg_claims_the_millimetres_the_board_claims(name):
    """Wokwi scales a board by what its SVG says it is, so the two must agree. The Joy-IT
    originals carry a 1920x1017 render size that matches neither the viewBox nor the part."""
    doc = _board(name)
    svg = (BOARDS[name] / "board.svg").read_text(errors="ignore")[:600]
    assert f'width="{doc["width"]}mm"' in svg
    assert f'height="{doc["height"]}mm"' in svg


@pytest.mark.parametrize("name", sorted(BOARDS))
def test_every_pin_lands_on_the_board(name):
    """A pin outside the outline is a pin you cannot click."""
    doc = _board(name)
    for pin, at in doc["pins"].items():
        assert 0 <= at["x"] <= doc["width"], f"{name}:{pin} x is off the board"
        assert 0 <= at["y"] <= doc["height"], f"{name}:{pin} y is off the board"


@pytest.mark.parametrize("name", sorted(BOARDS))
def test_a_board_targets_only_pins_its_chip_has(name, mapping):
    """The drift this guards. A board re-maps its own leg order onto a chip's pin NAMES, so a
    target the chip does not have is a wire that silently never connects — which is how the
    whole diagram once drew as two power leads."""
    doc = _board(name)
    chip_type = doc["chips"][0]["type"]
    known = set(mapping.get(chip_type, {}))
    assert known, f"nothing in the vocabulary states pins for {chip_type}"

    for pin, at in doc["pins"].items():
        target = at["target"].split(":", 1)[1]
        assert target in known, (
            f"{name}:{pin} targets {chip_type}:{target}, which that chip has no pin for — "
            f"it has {sorted(known)}")


def test_the_led_board_exists_because_its_order_differs():
    """The reason this module needed a board of its own, asserted so it survives a tidy-up.

    Ours reads R G B GND left to right; Wokwi's part calls its common leg COM and does not
    share that order. `target` is the re-mapping, and it is the whole point.
    """
    doc = _board("rgb_led")
    order = [p for p, _ in sorted(doc["pins"].items(), key=lambda kv: kv[1]["x"])]
    assert order == ["R", "G", "B", "GND"]
    assert doc["pins"]["GND"]["target"].endswith(":COM")


def test_the_dht_board_says_what_its_delegation_is_and_is_not_good_for():
    """It targets wokwi-dht22 while the firmware asks for a DHT11, and those do not encode
    alike. That costs nothing while these boards are a VISUAL model — the delegation only
    supplies pin names for `target` to map onto — and would cost everything the day anything
    runs. Asserted so the caveat stays attached to the file rather than becoming folklore.
    """
    assert _board("dht11")["chips"][0]["type"] == "wokwi-dht22"
    # Beside the board it is about, rather than in a shared README two directories away — which
    # is the whole reason a part carries its own drawing.
    readme = (BOARDS["dht11"] / "README.md").read_text()
    assert "DHT11" in readme and "visual model" in readme
