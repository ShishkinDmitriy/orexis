"""agora-wireviz — the wiring documented as a harness, and drafted back from one.

WireViz's vocabulary is connectors with named pins and cables with coloured wires, which is
what `mc:Pin`, `mc:Wire` and `mc:colour` already are. Nothing is flattened or invented in
either direction, which is why the round trip is the sharpest test here.
"""

from __future__ import annotations

import pytest

from agent.genesis import world_dir
from onboarding.wireviz import draft, render


@pytest.fixture(scope="module")
def harness():
    out = render("sensing")
    assert out is not None, "the sensing world has hardware and must document"
    return out


@pytest.fixture(scope="module")
def parsed(harness):
    import yaml
    return yaml.safe_load(harness)


def test_a_world_with_no_hardware_documents_nothing():
    assert render("society") is None
    assert render("simulation") is None


def test_wireviz_itself_accepts_it(harness):
    """The only check that matters for an output format nobody here can eyeball. It is easy to
    emit YAML that parses and that the tool then rejects."""
    from wireviz import wireviz as wv

    h = wv.parse(harness, return_types="harness")
    assert set(h.connectors) == {"esp32_fern", "air_sensor_fern",
                                 "moisture_sensor_fern", "status_led_fern"}
    assert len(h.cables) == 3


def test_a_connector_is_a_device_and_a_cable_is_a_run(parsed):
    """One cable per pair of devices rather than one per jumper. That is what it looks like on
    the bench — three leads to the same module run together — and it turns ten anonymous wires
    into three labelled runs."""
    assert parsed["connectors"]["esp32_fern"]["type"] == "ESP32-WROOM-32D"
    assert sum(c["wirecount"] for c in parsed["cables"].values()) == 10


def test_a_wire_keeps_the_colour_the_world_gave_it(parsed):
    """Translated at the edge, not stored in WireViz's form: the world says "red" because that
    is what the wire IS; RD is what one renderer calls it."""
    led = parsed["cables"]["esp32_fern-to-status_led_fern"]
    assert led["colors"] == ["RD", "GN", "BU", "BK"]


def test_a_board_leg_reads_as_its_silkscreen_and_a_part_leg_as_its_role(parsed):
    """The same split the wiring has. A board leg is identified by what is printed on it; a
    peripheral leg has no marking of its own and is known by what it is for."""
    assert "D34" in parsed["connectors"]["esp32_fern"]["pinlabels"]
    assert parsed["connectors"]["status_led_fern"]["pinlabels"] == ["Common", "Red", "Green", "Blue"]


# --- the other direction: a harness DRAFTS a stand -------------------------------------------


@pytest.fixture(scope="module")
def drafted():
    return draft("sensing", world_dir("sensing") / "wiring.yaml")


def test_every_role_survives_the_round_trip(drafted):
    """The inverse of the label. It found only two roles at first, because they are instances
    of SUBCLASSES of mc:PinRole — onewire:DataPinRole is a mc:BidirectionalRole — and the
    runtime does not run RDFS (#27, which has now cost five sessions). A property path closes
    it without inference.
    """
    for role in ("mc:PowerPinRole", "mc:GroundPinRole", "onewire:DataPinRole",
                 "mc:AnalogInPinRole", "rgbled:RedPinRole", "rgbled:CommonPinRole"):
        assert f"mc:pinRole {role} ." in drafted, f"{role} was not recovered"


def test_a_board_leg_is_not_asked_for_a_role_it_should_not_have(drafted):
    """A general-purpose leg has no role — it is general purpose until something is wired to
    it. Marking that absent as a TODO would ask the draft to invent the thing the model
    deliberately leaves out."""
    assert 'ag:esp32_fern_7 a mc:Pin ; skos:notation "D34" .' in drafted


def test_names_and_models_survive_where_a_drawing_lost_them(drafted):
    """What a harness is better at than a diagram: its YAML is meant to be TYPED, so it carries
    the names you chose and the models you wrote. A Wokwi import gave back `sen1`."""
    assert 'ag:localId "air_sensor_fern"' in drafted
    assert 'mc:model "KY-015 (DHT11)"' in drafted


def test_a_part_class_is_resolved_from_its_catalogue_name(drafted):
    """One triple turned a draft into a compilable source. `type: KY-015 (DHT11)` is free text
    until a package says that is what a dht11:Dht11 is CALLED — the mirror of wokwi:part, which
    already says how the same part is identified in the other tool."""
    assert "a dht11:Dht11 ;" in drafted
    assert "a probe:CapacitiveMoistureProbe ;" in drafted
    assert "a rgbled:RgbLed ;" in drafted


def test_the_board_is_identified_rather_than_guessed(drafted):
    """A type resolving to something under mc:Microcontroller IS the board. The old heuristic —
    whichever connector every cable touches — survives only where nothing resolves."""
    assert "a esp32:DevKitC ;" in drafted
    assert "GUESSED" not in drafted


def test_the_board_declares_what_it_carries(drafted):
    """Not the same statement as a wire — carrying is mounting, and a part can be carried and
    unwired — but every generator that walks a board starts from mc:carries. Leaving it out
    drafted a stand nothing downstream could find its parts in."""
    assert "mc:carries ag:air_sensor_fern , ag:moisture_sensor_fern , ag:status_led_fern" in drafted


def test_only_what_belongs_to_the_board_MODEL_is_left_over(drafted):
    """Eighteen markers became one, and the one left is not a gap in the harness. logicVolts is
    a fact about the DevKitC rather than about our DevKitC, so it belongs on the class — #55."""
    body = drafted.split("@prefix")[-1]
    assert body.count("### TODO ###") == 1
    assert "mc:logicVolts ### TODO ###" in body


def test_an_import_refuses_to_overwrite_a_world(tmp_path, monkeypatch):
    import shutil

    from agent import genesis
    from onboarding.wireviz import import_harness

    dst = tmp_path / "already"
    shutil.copytree(genesis.world_dir("sensing"), dst)
    monkeypatch.setattr("onboarding.wireviz.world_dir", lambda w: dst)

    with pytest.raises(SystemExit, match="already exists"):
        import_harness("sensing", dst / "wiring.yaml")


def test_the_committed_harness_is_in_step_with_the_world():
    """It is committed because it is the thing that DIFFS — a changed wire is one changed line
    in a pull request. The cost of committing it is that it can be left behind, so CI
    regenerates and compares."""
    committed = (world_dir("sensing") / "wiring.yaml").read_text()
    assert render("sensing") == committed, (
        "world/sensing/wiring.yaml is out of step — run `agora-wireviz sensing`")
