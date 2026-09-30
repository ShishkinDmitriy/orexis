"""The pipeline: bytes to a document by the codec, to a number by the pointer — over the pot's
probe and over a board's peripherals, and every way it refuses, which is None and a warning, never
a number. What quantity a number is, sensing's rules conclude."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.sensing.pipeline import (CODECS, DEFAULT_POINTER, Codec, CodecError, JsonCodec,
                                    PointerError, decode, decode_series, reads_series, resolve)

WORLDS = Path(__file__).parent / "worlds"
POT = WORLDS / "a_pot_and_its_probe.trig"
BOARD = WORLDS / "a_board_and_its_peripherals.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"

#  ONE BOARD, THREE PERIPHERALS, ONE MESSAGE: what a DHT11 beside a moisture probe publishes.
BOARD_MESSAGE = b'{"temperature": 21.5, "humidity": 0.61, "soil": {"moisture": 0.22}}'


def test_json_then_the_default_pointer_then_identity(snapshots):
    """The pot's probe states no binding at all, and reads as every board here speaks."""
    assert decode(snapshots.stand_in(POT), PROBE, b'{"value": 0.183}') == 0.183


def test_two_sensors_on_one_board_take_their_own_values_from_one_message(snapshots):
    """A board carrying several peripherals is one client publishing one document; each sensor
    is bound to its own pointer and reads its own number out of the same bytes."""
    store = snapshots.stand_in(BOARD)
    assert decode(store, TEST + "thermo", BOARD_MESSAGE) == 21.5
    assert decode(store, TEST + "hygro", BOARD_MESSAGE) == 0.61
    assert decode(store, PROBE, BOARD_MESSAGE) == 0.22


def test_a_member_from_elsewhere_serves_by_the_term_it_declares(snapshots, monkeypatch):
    """What a codec package would ship: a term the world declares as an instance of the family, a
    class implementing the contract under that term, and a sensor bound to it — found by the term,
    never by the class, so two pipelines run side by side."""
    class Csv(Codec):
        TERM = TEST + "Csv"

        def decode(self, payload: bytes):
            return [float(x) for x in payload.decode().split(",")]

        def encode(self, document) -> bytes:
            return ",".join(str(x) for x in document).encode()

    monkeypatch.setitem(CODECS, Csv.TERM, Csv)
    store = snapshots.stand_in(BOARD)
    assert decode(store, TEST + "gauge", b"10130,225") == 225
    assert decode(store, TEST + "thermo", b"10130,225") is None, "the thermometer's bytes are JSON, whatever the gauge's are"


def test_a_missing_field_is_unread(snapshots, caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(snapshots.stand_in(POT), PROBE, b'{"temperature": 21}') is None
    assert "unread" in caplog.text


def test_bytes_that_are_no_document_are_unread(snapshots, caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(snapshots.stand_in(POT), PROBE, b"\xff\xfe") is None
    assert "unread" in caplog.text


def test_a_codec_nothing_here_implements_is_said(snapshots, caplog):
    """The barometer is bound to a codec the world declares and nothing implements."""
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(snapshots.stand_in(BOARD), TEST + "barometer", b"\xa1") is None
    assert "codec nothing here implements" in caplog.text


def test_the_pointer_is_rfc_6901():
    assert resolve("/a/0/b~1c", {"a": [{"b/c": 3}]}) == 3
    with pytest.raises(PointerError):
        resolve("value", {"value": 1})
    with pytest.raises(PointerError):
        resolve("/a", {"a": {"whole": "document"}})
    with pytest.raises(PointerError):
        resolve("/a/9", {"a": [1]})


def test_the_json_codec_codes_both_ways():
    assert JsonCodec().decode(JsonCodec().encode({"value": 1})) == {"value": 1}
    with pytest.raises(CodecError):
        JsonCodec().decode(b"{")
    assert DEFAULT_POINTER == "/value"


SERIES = Path(__file__).parent / "received" / "a_forecast_is_a_graph_per_stretch_ahead.trig"


def _at(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=timezone.utc)


def test_an_ends_pointer_makes_each_value_the_stretch_up_to_its_instant(snapshots):
    """The weather service states an ends pointer: the amount at one o'clock is what falls from
    noon to one, and the first stretch is as long as its neighbour."""
    store = snapshots.stand_in(SERIES)
    assert reads_series(store, TEST + "weather") and not reads_series(store, TEST + "probe")
    got = decode_series(store, TEST + "weather", b'{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00"],'
                                                   b' "precipitation": [0.4, 0.0]}}')
    assert got == [(_at(12), _at(13), 0.4), (_at(13), _at(14), 0.0)]


def test_a_starts_pointer_and_epoch_instants_make_each_value_the_stretch_from_its_instant(snapshots):
    store = snapshots.stand_in(SERIES)
    store.update("""PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX : <http://example.org/test#>
                    DELETE WHERE { GRAPH :world { :weather sensing:endsPointer ?p } } ;
                    INSERT DATA { GRAPH :world { :weather sensing:startsPointer "/hourly/time" } }""")
    noon = int(_at(12).timestamp())
    got = decode_series(store, TEST + "weather", f'{{"hourly": {{"time": [{noon}, {noon + 3600}], "precipitation": [1, 2]}}}}'.encode())
    assert got == [(_at(12), _at(13), 1.0), (_at(13), _at(14), 2.0)]


def test_a_series_whose_arrays_disagree_is_unread(snapshots, caplog):
    store = snapshots.stand_in(SERIES)
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode_series(store, TEST + "weather", b'{"hourly": {"time": ["2026-01-01T13:00"], "precipitation": [1, 2]}}') is None
    assert "unread series" in caplog.text

