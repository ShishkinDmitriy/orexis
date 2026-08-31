"""orexis-firmware — a board's config.h is derived from the world, never typed.

These are about the QUERY and what it emits, not about flashing anything. The generator reads
credentials that are gitignored and writes a file carrying a password, so the tests drive the
two pure pieces: the query that finds a board and its peripherals, and the fragment that turns
those into `#define`s.

The query is the part worth guarding. It grew OPTIONAL clauses for the LED and the air sensor,
and a malformed OPTIONAL does not error — it silently returns nothing, and the generator then
reports that the world states no boards at all. That failure looks like a missing world rather
than a broken query, which is how it would survive a review.
"""

from __future__ import annotations

import pytest
import rdflib

from agent import ratified
from orexis_agent_progression.ontology import WORLD_GRAPH
from onboarding.namespaces import SENSING
from onboarding.firmware import _BOARDS_Q, _optional_pins


@pytest.fixture(scope="module")
def board():
    """The one real board, as the generator sees it."""
    rows = ratified.rows(ratified.dataset("sensing"), _BOARDS_Q)
    assert len(rows) == 1, "the sensing world states exactly one board"
    return rows[0]


def test_the_probe_still_comes_through(board):
    """The guard against an OPTIONAL that took the whole query down with it."""
    assert board["boardId"] == "esp32_fern"
    assert int(board["gpio"]) == 34
    assert board["readTopic"] and board["cmdTopic"]


def test_the_status_led_comes_through(board):
    """Three legs, and they must not be interchangeable — a red on the blue pin is a wiring
    bug that looks exactly like the board being asleep, from across the room."""
    assert (int(board["ledRed"]), int(board["ledGreen"]), int(board["ledBlue"])) == (25, 26, 27)


def test_the_air_sensor_comes_through(board):
    assert int(board["airPin"]) == 32


def test_a_board_with_no_led_still_generates():
    """A board without a status LED is an ordinary board.

    This is what the OPTIONALs are for, and it is not hypothetical — every board in this
    repository before this one had no LED. Checked by removing it from a copy of the world
    rather than by trusting that OPTIONAL means what it says.
    """
    ds = ratified.dataset("sensing")
    # Unwiring means editing the DEPLOYMENT since #99 — hosting is entailed from it, so the
    # premise goes (the deployment stops deploying the LED) and, because the dataset has
    # already computed its closure, the conclusion is removed where it landed. A real rewiring
    # edits hardware.ttl and the next genesis entails the smaller hosting by itself.
    from orexis_agent_progression.ontology import WORLD_ENTAILED_GRAPH
    ds.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?d <http://www.w3.org/ns/ssn/deployedSystem> ?led }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?d <http://www.w3.org/ns/ssn/deployedSystem> ?led .
                  ?led a <http://example.org/orexis/rgb-led#RgbLed> }} }}""")
    ds.update(f"""
        DELETE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?b <http://www.w3.org/ns/sosa/hosts> ?led }} }}
        WHERE  {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?b <http://www.w3.org/ns/sosa/hosts> ?led }}
                  GRAPH <{WORLD_GRAPH}> {{ ?led a <http://example.org/orexis/rgb-led#RgbLed> }} }}""")

    rows = ratified.rows(ds, _BOARDS_Q)
    assert len(rows) == 1, "losing the LED must not lose the board"
    assert int(rows[0]["gpio"]) == 34
    assert not rows[0].get("ledRed")


def test_absent_peripherals_emit_no_defines():
    """Absent rather than zero, deliberately: the firmware guards on #ifdef, and GPIO 0 is a
    strapping pin — a board driving it holds itself in bootloader mode at the next reset."""
    assert _optional_pins({"gpio": 34}) == ""


def test_present_peripherals_emit_their_pins():
    out = _optional_pins({"ledRed": 25, "ledGreen": 26, "ledBlue": 27, "airPin": 32})
    assert "#define LED_RED_PIN 25" in out
    assert "#define LED_GREEN_PIN 26" in out
    assert "#define LED_BLUE_PIN 27" in out
    assert "#define AIR_SENSOR_PIN 32" in out


def test_the_board_is_told_who_it_is_and_not_what_it_watches(board):
    """A probe does not know which plant it sits in, and has no use for the answer.

    It carried a PLANT_ID until the subject's local id was removed from this query — a leftover
    from when topics were built as "sensors/<plant>/moisture" instead of read from
    mqtt:readingTopic. Which subject a reading is ABOUT is the world's statement and the agent's
    to apply; the board is handed exactly one identifier, its own, the same way an agent process
    is. Asserted on the query rather than on the header, so it cannot come back through either.
    """
    assert board["sensorId"] == "moisture_sensor_fern"
    assert "subjectId" not in board


def test_a_pin_appears_exactly_once_across_the_whole_board(board):
    """The shapes forbid two legs on one GPIO in the graph; this checks the GENERATOR did not
    reintroduce a collision by mapping two different roles onto one #define."""
    pins = [int(board[k]) for k in ("gpio", "ledRed", "ledGreen", "ledBlue", "airPin")]
    assert len(pins) == len(set(pins)), f"a pin is claimed twice: {sorted(pins)}"


def test_the_persistence_figure_reaches_both_temperaments():
    """The constitutional debounce (#180): one breaching look is an ADC glitch, N are the
    news, and N is the society's figure — so both firmwares must compile the same answer,
    read from the ontology and never typed into a header."""
    from onboarding.firmware import _crossing, _persist_looks

    ds = ratified.dataset("sensing")
    n = _persist_looks(ds)
    assert n == 2, "sensing:alarmPersistenceLooks — the family's stated figure"
    governed = _crossing({"alarm": True}, n)
    assert "#define WAKE_ON_ALARM 1" in governed
    assert f"#define WAKE_PERSIST_LOOKS {n}" in governed
    assert _crossing({}, n) == "", (
        "a board whose world makes no alarm promise carries neither define — absence stays "
        "a statement in the firmware exactly as in the graph")


#  The terrace (world/terrace): the same query, a different temperament and a different air
#  part. Its board runs the OUTDOOR SENTINEL — moisture-sentinel copied onto a FireBeetle 2
#  ESP32-E with a BME280 (#461) — so it is rendered through `render_sentinel`, which had never
#  run for a real world before (#323 stays open until a world deploys moisture-sentinel itself).
#  A BME280 hangs off two I2C lines rather than one one-wire leg, and the header needs both
#  numbers and the unit's address — so the OPTIONAL that finds it is a second place the query
#  can silently lose a board, guarded the same way as the first.

@pytest.fixture(scope="module")
def terrace():
    rows = ratified.rows(ratified.dataset("terrace"), _BOARDS_Q)
    assert len(rows) == 1, "the terrace states exactly one board"
    return rows[0]


def test_the_terrace_board_runs_the_outdoor_sentinel(terrace):
    """Entailed from the device's class, never stated on the board: the third firmware's
    ontology names its directory, and the generator dispatches on that name."""
    assert terrace["firmware"] == "outdoor-sentinel"
    assert not terrace.get("cmdTopic"), "a sentinel takes no orders — no command topic"


def test_the_bme280_comes_through_with_its_address(terrace):
    assert terrace["boardId"] == "esp32_terrace"
    assert int(terrace["gpio"]) == 34
    assert (int(terrace["bmeSda"]), int(terrace["bmeScl"])) == (21, 22)
    assert int(terrace["bmeAddr"]) == 0x76
    # And NOT the DHT path: the terrace wires no one-wire leg.
    assert not terrace.get("airPin")


def test_the_bme280_emits_its_defines_in_hex():
    out = _optional_pins({"bmeSda": 21, "bmeScl": 22, "bmeAddr": 119})
    assert "#define BME280_SDA_PIN 21" in out
    assert "#define BME280_SCL_PIN 22" in out
    assert "#define BME280_ADDR 0x77" in out
    assert "AIR_SENSOR_PIN" not in out


def test_a_bme280_with_no_stated_address_defaults_to_the_common_strap():
    assert "#define BME280_ADDR 0x76" in _optional_pins({"bmeSda": 21, "bmeScl": 22})


def test_a_part_the_generator_has_no_template_for_is_reported():
    """The generator reports what it cannot describe rather than guessing — asserted by making
    the terrace's air part something the header knows nothing about, and checking it is named.
    Both halves: with the type in place nothing is reported, which is what makes the second
    half a finding rather than a constant."""
    from onboarding.firmware import _untemplated

    ds = ratified.dataset("terrace")
    assert _untemplated(ds, "esp32_terrace") == []
    ds.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?p a <http://example.org/orexis/bme280#Bme280> }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?p a <http://example.org/orexis/bme280#Bme280> }} }}""")
    assert _untemplated(ds, "esp32_terrace") == ["air_sensor_terrace"]


def test_the_firebeetles_own_led_comes_from_its_class(terrace, board):
    """A FireBeetle 2 ESP32-E carries a WS2812 on GPIO 5 by construction, stated once as a
    restriction on the board class and reached through the closure — so the terrace renders it
    with nothing in its hardware.ttl saying so, and the sensing world's DevKitC, which has no
    such lamp, renders nothing and compiles the code away."""
    assert int(terrace["ws2812"]) == 5
    assert not board.get("ws2812")
    out = _optional_pins({"ws2812": 5})
    assert "#define STATUS_LED_WS2812_PIN 5" in out
    assert "LED_RED_PIN" not in out


def test_the_sentinel_template_renders_the_terrace(terrace, monkeypatch):
    """The sentinel template's first real run. The credential and the wifi are stubbed — they
    are the two things this test must not need — and everything else is read from the world:
    the band from the bed's operating range, the delta as the family's fraction of its width,
    the heartbeat under the polling agent's OWN freshness belief, and the parts.

    The heartbeat is the finding. The template asked the ratified dataset for
    `sensing:maxReadingAgeS`, which is a belief and lives in no public graph, so it bound
    nothing and every sentinel would have compiled the 750 s default: 600 s, above the 300 s
    the terrace agent actually believes, so a healthy board would have been read as dead.
    Asserting 1200 is asserting that the belief was read."""
    from onboarding import firmware

    monkeypatch.setattr(firmware, "_env", lambda path, key: {"MQTT_USERNAME": "u",
                                                             "MQTT_PASSWORD": "p"}.get(key))
    monkeypatch.setattr(firmware, "_wifi", lambda: ("ssid", "pass"))
    out = firmware.render_sentinel("terrace", terrace, ratified.dataset("terrace"))
    assert "#define HEARTBEAT_S 1200" in out           # max(60, 0.8 * 1500)
    assert "#define WAKE_DELTA 0.087" in out           # 0.25 * (0.60 - 0.25), rounded
    assert "#define WAKE_PERSIST_LOOKS 2" in out
    assert "#define MOISTURE_PIN 34" in out
    assert "#define BME280_SDA_PIN 21" in out
    assert "#define BME280_ADDR 0x76" in out
    assert "#define STATUS_LED_WS2812_PIN 5" in out
    assert "CMD_TOPIC" not in out and "MIN_SLEEP_S" not in out


def test_the_governed_template_is_unchanged_for_the_sensing_world(board, monkeypatch):
    """The sensing world's DevKitC still renders as it did: no BME280, no WS2812, and the
    governed node's cadence bounds and command topic."""
    from onboarding import firmware

    monkeypatch.setattr(firmware, "_env", lambda path, key: {"MQTT_USERNAME": "u",
                                                             "MQTT_PASSWORD": "p"}.get(key))
    monkeypatch.setattr(firmware, "_wifi", lambda: ("ssid", "pass"))
    out = firmware.render("sensing", board, (10, 900))
    assert "BME280" not in out and "WS2812" not in out
    assert "#define AIR_SENSOR_PIN 32" in out
    assert "#define CMD_TOPIC" in out and "#define MIN_SLEEP_S 10" in out
