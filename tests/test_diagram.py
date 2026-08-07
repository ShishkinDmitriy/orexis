"""agora-diagram — the stand as a Wokwi project, drawn from the world and never by hand.

A hand-maintained wiring diagram is wrong the first time a jumper moves, and wrong SILENTLY,
which is worse than not having one. These check the generated one says what the world says,
because a picture that quietly drops a wire is the picture you would then trust.

Nothing here opens wokwi.com. They check the document.
"""

from __future__ import annotations

import json

import pytest

from agent.genesis import world_dir
from onboarding.diagram import render


@pytest.fixture(scope="module")
def doc():
    out = render("sensing")
    assert out is not None, "the sensing world has hardware and must draw"
    return out


@pytest.fixture(scope="module")
def wires(doc):
    return {frozenset((a, b)): colour for a, b, colour, _ in doc["connections"]}


def test_a_world_with_no_hardware_draws_nothing():
    """Two of the three shipped worlds have no boards. An empty diagram is a picture of nothing
    that looks like a picture of a broken generator."""
    assert render("society") is None
    assert render("simulation") is None


def test_every_part_is_drawn_as_what_its_own_package_says(doc):
    """The mapping lives with the part, so adding one stays 'adding a directory'."""
    drawn = {p["id"]: p["type"] for p in doc["parts"]}
    assert drawn == {
        "esp32_fern": "board-esp32-devkit-c-v4",
        "moisture_sensor_fern": "wokwi-potentiometer",
        "status_led_fern": "wokwi-rgb-led",
        "air_sensor_fern": "wokwi-dht22",
    }


def test_the_led_polarity_is_derived_from_the_wire(doc, tmp_path, monkeypatch):
    """Which polarity it is decides whether every colour comes out as itself or as its
    complement, so the simulation must be told — and it must be told the TRUTH.

    It was briefly declared on the RGB LED's class, which is wrong twice: it is a fact about the
    part soldered here rather than about RGB LEDs, and stating it beside the wire that
    determines it is how the two get to disagree. The common leg's wire is the fact. Ground
    means cathode, a rail means anode.
    """
    led = next(p for p in doc["parts"] if p["id"] == "status_led_fern")
    assert led["attrs"] == {"common": "cathode"}, "as wired: the common leg goes to ground"

    # And it must actually FLIP, or it is a constant wearing a derivation's clothes.
    import shutil

    from agent import genesis
    src = genesis.world_dir("sensing")
    dst = tmp_path / "anode"
    shutil.copytree(src, dst)
    hw = dst / "hardware.ttl"
    hw.write_text(hw.read_text().replace("mc:joins ag:led_common , ag:pin_gnd",
                                         "mc:joins ag:led_common , ag:pin_3v3"))
    monkeypatch.setattr(genesis, "world_dir", lambda w: dst)
    monkeypatch.setattr("agent.ratified.world_dir", lambda w: dst, raising=False)

    from onboarding.diagram import render as render_again
    flipped = next(p for p in render_again("anode")["parts"] if p["id"] == "status_led_fern")
    assert flipped["attrs"] == {"common": "anode"}, "on a rail it is a common-anode part"


def test_every_wire_in_the_world_is_a_connection(wires):
    assert len(wires) == 10
    assert frozenset(("esp32_fern:D34", "moisture_sensor_fern:SIG")) in wires
    assert frozenset(("air_sensor_fern:SDA", "esp32_fern:D32")) in wires
    assert frozenset(("status_led_fern:COM", "esp32_fern:GND")) in wires


def test_a_board_leg_is_named_by_its_silkscreen(wires):
    """D34 and 3V3, not GPIO numbers and not our own identifiers. Wokwi names the same physical
    header the silkscreen does, so one of the two had to be authoritative and it already was —
    which is why no board pin names are stated in the Wokwi vocabulary at all."""
    assert any("esp32_fern:3V3" in pair for pair in wires)
    assert not any(":pin_gpio" in p for pair in wires for p in pair)


def test_a_wire_is_coloured_by_what_it_carries(wires):
    """The first thing anyone tracing a breadboard wants: red is live, black is ground."""
    assert wires[frozenset(("esp32_fern:3V3", "moisture_sensor_fern:VCC"))] == "red"
    assert wires[frozenset(("esp32_fern:GND", "moisture_sensor_fern:GND"))] == "black"
    assert wires[frozenset(("esp32_fern:D34", "moisture_sensor_fern:SIG"))] == "green"


def test_the_committed_picture_is_in_step_with_the_world():
    """The failure this approach exists to prevent, guarded rather than trusted.

    `diagram.json` is committed, which is most of its value — a change to the wiring then
    arrives in a pull request as a picture. The cost is that it can be left behind: edit
    `hardware.ttl`, forget to regenerate, and the repository carries a confident drawing of a
    stand that does not exist. Nothing about a stale picture looks stale.
    """
    committed = json.loads((world_dir("sensing") / "wokwi" / "diagram.json").read_text())
    assert committed == render("sensing"), (
        "world/sensing/wokwi/diagram.json is out of step — run `agora-diagram sensing`")
