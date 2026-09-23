"""orexis-wokwi — the stand as a Wokwi project, drawn from the world and never by hand.

A hand-maintained wiring diagram is wrong the first time a jumper moves, and wrong SILENTLY,
which is worse than not having one. These check the generated one says what the world says,
because a picture that quietly drops a wire is the picture you would then trust.

Nothing here opens wokwi.com. They check the document.
"""

from __future__ import annotations

import json

import pytest

from agent_old.genesis import world_dir
from onboarding.wokwi import render


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
    assert render("simulation") is None
    assert render("simulation") is None


def test_every_part_is_drawn_as_what_its_own_package_says(doc):
    """The mapping lives with the part, so adding one stays 'adding a directory'."""
    drawn = {p["id"]: p["type"] for p in doc["parts"]}
    assert drawn == {
        "esp32_fern": "board-esp32-devkit-c-v4",
        "moisture_sensor_fern": "chip-soil-moisture-sensor",
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

    from agent_old import genesis
    src = genesis.world_dir("sensing")
    dst = tmp_path / "anode"
    shutil.copytree(src, dst)
    hw = dst / "hardware.ttl"
    hw.write_text(hw.read_text().replace("mc:joins :led_common , :pin_gnd",
                                         "mc:joins :led_common , :pin_3v3"))
    monkeypatch.setattr("agent_old.ratified.world_dir", lambda w: dst)
    monkeypatch.setattr("onboarding.wokwi.world_dir", lambda w: dst)

    from onboarding.wokwi import render as render_again
    flipped = next(p for p in render_again("anode")["parts"] if p["id"] == "status_led_fern")
    assert flipped["attrs"] == {"common": "anode"}, "on a rail it is a common-anode part"


def test_the_serial_monitor_is_wired(wires):
    """Not in our graph and it should not be — it is the simulator's console, not a thing on
    the windowsill. But this firmware's whole diagnostic story is that line, so a simulation
    without it would run and tell you nothing."""
    assert frozenset(("esp32_fern:TX", "$serialMonitor:RX")) in wires
    assert frozenset(("esp32_fern:RX", "$serialMonitor:TX")) in wires


def test_every_wire_in_the_world_is_a_connection(wires):
    assert len([w for w in wires if "$serialMonitor" not in str(w)]) == 10
    assert frozenset(("esp32_fern:34", "moisture_sensor_fern:SIG")) in wires
    assert frozenset(("air_sensor_fern:SDA", "esp32_fern:32")) in wires
    assert frozenset(("status_led_fern:COM", "esp32_fern:GND.1")) in wires


def test_a_board_leg_is_named_by_what_wokwi_calls_it_and_nothing_else(wires):
    """Two naming systems, neither derived from the other, both stated.

    `skos:notation` is what is PRINTED beside the leg — for a person with a jumper. `wokwi:name`
    is what the SIMULATOR calls it. They disagree more often than they agree: Wokwi says 34
    where the board prints D34, and GND.1/.2/.3 where the board prints GND on all three legs, so
    the silkscreen does not even identify a pin uniquely.

    They agree on 3V3, which is exactly how the mismatch went unnoticed — that was the one wire
    that drew, and the whole diagram looked like a sparse circuit rather than a broken one.
    """
    assert any("esp32_fern:34" in pair for pair in wires)
    assert any("esp32_fern:GND.1" in pair for pair in wires)
    assert any("esp32_fern:3V3" in pair for pair in wires)
    assert not any(":D" in p or ":pin_gpio" in p for pair in wires for p in pair)


def test_a_leg_with_no_wokwi_name_is_reported_rather_than_guessed(tmp_path, monkeypatch, caplog):
    """The bare number was briefly computed from mc:gpio. It gave the right answer and was the
    wrong shape — a rule about Wokwi's naming conventions living in Python, where nothing in the
    graph shows it and nothing contradicts it the day they change. Omission is now visible."""
    import logging
    import re
    import shutil

    from agent_old import genesis
    from onboarding.wokwi import render as render_again

    dst = tmp_path / "unnamed"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    hw = dst / "hardware.ttl"
    hw.write_text(re.sub(r' ;\s*wokwi:name "34"', "", hw.read_text()))
    monkeypatch.setattr("agent_old.ratified.world_dir", lambda w: dst)
    monkeypatch.setattr("onboarding.wokwi.world_dir", lambda w: dst)

    with caplog.at_level(logging.WARNING):
        doc = render_again("x")
    assert not any("moisture_sensor_fern:SIG" in str(c) for c in doc["connections"])
    assert any("could not be named" in r.getMessage() for r in caplog.records)


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
    assert wires[frozenset(("status_led_fern:R", "esp32_fern:25"))] == "red"
    assert wires[frozenset(("status_led_fern:G", "esp32_fern:26"))] == "green"
    assert wires[frozenset(("status_led_fern:B", "esp32_fern:27"))] == "blue"
    assert wires[frozenset(("air_sensor_fern:SDA", "esp32_fern:32"))] == "yellow"


def test_an_uncoloured_wire_falls_back_to_what_it_carries(tmp_path, monkeypatch):
    """A guess, and a good one — red is live, black is a return, green is signal.

    Exercised against a world with the colours stripped, because the sensing world now states
    every one of them: asserting the fallback there would be asserting the fact and calling it
    a default, which is a test that passes for the wrong reason.
    """
    import re
    import shutil

    from agent_old import genesis
    from onboarding.wokwi import render as render_again

    dst = tmp_path / "uncoloured"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    hw = dst / "hardware.ttl"
    hw.write_text(re.sub(r' ; mc:colour "\w+"', "", hw.read_text()))
    # Both modules imported world_dir BY NAME, so patching it on genesis reaches neither.
    monkeypatch.setattr("agent_old.ratified.world_dir", lambda w: dst)
    monkeypatch.setattr("onboarding.wokwi.world_dir", lambda w: dst)

    wires = {frozenset((a, b)): c for a, b, c, _ in render_again("x")["connections"]}
    assert wires[frozenset(("esp32_fern:3V3", "moisture_sensor_fern:VCC"))] == "red"
    assert wires[frozenset(("esp32_fern:GND.1", "moisture_sensor_fern:GND"))] == "black"
    assert wires[frozenset(("esp32_fern:34", "moisture_sensor_fern:SIG"))] == "green"
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
        "world/sensing/wokwi/diagram.json is out of step — run `orexis-wokwi sensing`")


def test_a_dragged_part_keeps_where_you_put_it(tmp_path, monkeypatch):
    """The generator owns WHAT is connected; you own WHERE it sits.

    Wokwi rewrites top/left as you drag, and a regeneration that ignored them would throw away
    the arranging every time the wiring changed — which is exactly when you want the picture and
    least want to redo it. A default layout is a guess; a position on disk is a decision.
    """
    import json
    import shutil

    from agent_old import genesis
    from onboarding.wokwi import generate, render as render_again

    dst = tmp_path / "dragged"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    monkeypatch.setattr("agent_old.ratified.world_dir", lambda w: dst)
    monkeypatch.setattr("onboarding.wokwi.world_dir", lambda w: dst)

    generate("x")
    out = dst / "wokwi" / "diagram.json"
    doc = json.loads(out.read_text())
    for part in doc["parts"]:
        if part["id"] == "status_led_fern":
            part["top"], part["left"] = 999, -999
    out.write_text(json.dumps(doc, indent=2) + "\n")

    again = render_again("x")
    led = next(p for p in again["parts"] if p["id"] == "status_led_fern")
    assert (led["top"], led["left"]) == (999, -999), "an arranged part must stay arranged"
    assert len([c for c in again["connections"] if "$serialMonitor" not in str(c)]) == 10, (
        "and the wiring must still be regenerated in full")


# --- the other direction: a drawing DRAFTS a stand, and never becomes one ----------------------


@pytest.fixture(scope="module")
def drafted():
    """Our own diagram, read back. A round trip is the sharpest test of an inverse mapping."""
    from pathlib import Path

    from agent_old.genesis import world_dir
    from onboarding.wokwi import draft

    return draft("sensing", world_dir("sensing") / "wokwi" / "diagram.json")


def test_the_mapping_inverts(drafted):
    """`wokwi:part` and `wokwi:name` are a two-column table, and reading it backwards is most of
    the importer. SDA is a one-wire data leg, SIG is an analog input, and neither fact is in the
    diagram — both come from the part's own package."""
    assert "a dht11:Dht11 ;" in drafted
    assert "a probe:CapacitiveMoistureProbe ;" in drafted
    assert "mc:pinRole onewire:DataPinRole" in drafted
    assert "mc:pinRole mc:AnalogInPinRole" in drafted


def test_every_wire_survives_the_round_trip(drafted):
    """The wires are the part a diagram is actually good at, so losing one here would be losing
    the only thing worth importing."""
    assert drafted.count("a mc:Wire ;") == 10
    assert 'mc:colour "yellow"' in drafted   # and the colours, which Wokwi does carry


def test_the_console_is_not_imported_as_hardware(drafted):
    """Wokwi's serial monitor is one of its own parts, not a thing on the windowsill. Its two
    connections are dropped — and with them the board's TX and RX, which would otherwise arrive
    as legs no wire reaches."""
    assert "$serialMonitor" not in drafted
    assert "_tx a mc:Pin" not in drafted and "_rx a mc:Pin" not in drafted


def test_what_wokwi_cannot_say_is_marked_and_not_guessed(drafted):
    """The draft is deliberately unvalidatable.

    A diagram carries no calibration, no rails, no topics and no name a person would recognise.
    Emitting a plausible value for those would produce a draft that PASSES orexis-validate, which
    is the one nobody re-reads — so each is an explicit marker instead.
    """
    assert "### TODO ###" in drafted
    assert drafted.count("### TODO ###") > 10
    # the specific ones that would be most tempting to invent
    assert 'mc:model "### TODO ###"' in drafted
    assert "mc:logicVolts ### TODO ###" in drafted


def test_an_import_refuses_to_overwrite_a_world(tmp_path, monkeypatch):
    """It drafts a stand; it does not reconcile one. There is no merge rule between a drawing
    and a world, and inventing one silently is how the world stops being the source."""
    import shutil

    from agent_old import genesis
    from onboarding.wokwi import import_diagram

    dst = tmp_path / "already"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    monkeypatch.setattr("onboarding.wokwi.world_dir", lambda w: dst)

    with pytest.raises(SystemExit, match="already exists"):
        import_diagram("sensing", dst / "wokwi" / "diagram.json")
