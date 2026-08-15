"""agora-firmware — a board's config.h is derived from the world, never typed.

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
from agent.ontology import SENSING, WORLD_GRAPH
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
    from agent.ontology import WORLD_ENTAILED_GRAPH
    ds.update(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ?d <http://www.w3.org/ns/ssn/deployedSystem> ?led }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ?d <http://www.w3.org/ns/ssn/deployedSystem> ?led .
                  ?led a <http://example.org/agora/rgb-led#RgbLed> }} }}""")
    ds.update(f"""
        DELETE {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?b <http://www.w3.org/ns/sosa/hosts> ?led }} }}
        WHERE  {{ GRAPH <{WORLD_ENTAILED_GRAPH}> {{ ?b <http://www.w3.org/ns/sosa/hosts> ?led }}
                  GRAPH <{WORLD_GRAPH}> {{ ?led a <http://example.org/agora/rgb-led#RgbLed> }} }}""")

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
