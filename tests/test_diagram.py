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
        "moisture_sensor_fern": "wokwi-soil-moisture-sensor",
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
    assert frozenset(("status_led_fern:COM", "esp32_fern:GND.1")) in wires


def test_a_board_leg_is_named_by_its_silkscreen(wires):
    """D34 and 3V3, not GPIO numbers and not our own identifiers."""
    assert any("esp32_fern:3V3" in pair for pair in wires)
    assert any("esp32_fern:D34" in pair for pair in wires)
    assert not any(":pin_gpio" in p for pair in wires for p in pair)


def test_a_board_leg_may_override_what_wokwi_calls_it(wires):
    """The silkscreen is NOT a unique key, which is a claim I made confidently and wrongly.

    A DevKit prints GND on three separate legs, so Wokwi disambiguates where the board does
    not — there is no pin called `GND` in its catalogue, only GND.1/.2/.3. Every ground wire
    was therefore silently dropped by the renderer while the power wires drew fine, which is a
    failure that looks like half a diagram rather than an error.
    """
    assert all("esp32_fern:GND.1" in pair or "GND" not in str(pair)
               for pair in wires if any("GND" in p for p in pair))


def test_a_wire_wears_the_colour_the_world_gives_it(wires):
    """The colour of the actual jumper, stated in the world. Nothing electrical depends on it,
    which is exactly why it is worth recording: it is how you find one wire among nine
    identical ones without tracing each to its end.

    The LED's three channels are the case that earns it — otherwise three identical jumpers
    into three adjacent pins."""
    assert wires[frozenset(("status_led_fern:R", "esp32_fern:D25"))] == "red"
    assert wires[frozenset(("status_led_fern:G", "esp32_fern:D26"))] == "green"
    assert wires[frozenset(("status_led_fern:B", "esp32_fern:D27"))] == "blue"
    assert wires[frozenset(("air_sensor_fern:SDA", "esp32_fern:D32"))] == "yellow"


def test_an_uncoloured_wire_falls_back_to_what_it_carries(tmp_path, monkeypatch):
    """A guess, and a good one — red is live, black is a return, green is signal.

    Exercised against a world with the colours stripped, because the sensing world now states
    every one of them: asserting the fallback there would be asserting the fact and calling it
    a default, which is a test that passes for the wrong reason.
    """
    import re
    import shutil

    from agent import genesis
    from onboarding.diagram import render as render_again

    dst = tmp_path / "uncoloured"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    hw = dst / "hardware.ttl"
    hw.write_text(re.sub(r' ; mc:colour "\w+"', "", hw.read_text()))
    # ratified imported world_dir BY NAME, so patching it on genesis does not reach it.
    monkeypatch.setattr("agent.ratified.world_dir", lambda w: dst)

    wires = {frozenset((a, b)): c for a, b, c, _ in render_again("x")["connections"]}
    assert wires[frozenset(("esp32_fern:3V3", "moisture_sensor_fern:VCC"))] == "red"
    assert wires[frozenset(("esp32_fern:GND.1", "moisture_sensor_fern:GND"))] == "black"
    assert wires[frozenset(("esp32_fern:D34", "moisture_sensor_fern:SIG"))] == "green"
    # and the stated colours are gone, or this is testing nothing
    assert "yellow" not in set(wires.values())


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
