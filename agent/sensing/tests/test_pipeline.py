"""The pipeline: bytes to a document by the codec, to a raw value by the pointer, to a quantity
by the scaling — and every way it refuses, which is None and a warning, never a number."""

from __future__ import annotations

import pytest

from pathlib import Path

from agent.sensing.pipeline import (CODECS, DEFAULT_POINTER, SCALINGS, Codec, CodecError, JsonCodec,
                                    PointerError, Scaling, decode, resolve)
from agent.store import update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
TEST = "http://example.org/test#"
PROBE = TEST + "probe"


def _bound(snapshots, *triples: str):
    """The pot's world, with what the world says of the probe's bytes added — nothing, by
    default, which is JSON, `/value` and the raw number."""
    store = snapshots.stand_in(WORLD)
    if triples:
        update(store, "PREFIX : <http://example.org/test#>\nINSERT DATA { GRAPH :world { "
               + " . ".join(f":probe {t}" for t in triples) + " } }")
    return store


#  ONE BOARD, THREE PERIPHERALS, ONE MESSAGE: what a DHT11 beside a moisture probe publishes.
BOARD_MESSAGE = b'{"temperature": 21.5, "humidity": 0.61, "soil": {"moisture": 0.22}}'


def test_two_sensors_on_one_board_take_their_own_values_from_one_message(snapshots):
    """A board carrying several peripherals is one client publishing one document; each sensor
    is bound to its own pointer and reads its own number out of the same bytes."""
    store = _bound(snapshots, 'sensing:readingPointer "/soil/moisture"')
    update(store, """PREFIX : <http://example.org/test#>
INSERT DATA { GRAPH :world {
  :thermo a sosa:Sensor ; sosa:observes :warmth ; sosa:isHostedBy :zz ; sensing:readingPointer "/temperature" .
  :hygro a sosa:Sensor ; sosa:observes :humidity ; sosa:isHostedBy :zz ; sensing:readingPointer "/humidity" } }""")
    assert decode(store, TEST + "thermo", BOARD_MESSAGE) == 21.5
    assert decode(store, TEST + "hygro", BOARD_MESSAGE) == 0.61
    assert decode(store, PROBE, BOARD_MESSAGE) == 0.22


def test_a_member_from_elsewhere_serves_by_the_term_it_declares(snapshots, monkeypatch):
    """What a codec or a scaling package would ship: a term declared as an instance of the
    family, a class implementing the contract under that term, and a sensor bound to it —
    found by the term, never by the class, so two pipelines run side by side."""
    class Csv(Codec):
        TERM = TEST + "Csv"

        def decode(self, payload: bytes):
            return [float(x) for x in payload.decode().split(",")]

        def encode(self, document) -> bytes:
            return ",".join(str(x) for x in document).encode()

    class Tenths(Scaling):
        TERM = TEST + "Tenths"

        def apply(self, sensor: str, raw: float) -> float:
            return raw / 10

    monkeypatch.setitem(CODECS, Csv.TERM, Csv)
    monkeypatch.setitem(SCALINGS, Tenths.TERM, Tenths)
    store = _bound(snapshots, "sensing:scaledBy :Tenths")
    update(store, """PREFIX : <http://example.org/test#>
INSERT DATA { GRAPH :world {
  :Csv a sensing:Codec . :Tenths a sensing:Scaling .
  :gauge a sosa:Sensor ; sosa:observes :pressure ; sosa:isHostedBy :zz ;
         sensing:decodedBy :Csv ; sensing:scaledBy :Tenths ; sensing:readingPointer "/1" } }""")
    assert decode(store, TEST + "gauge", b"10130,225") == 22.5
    assert decode(store, PROBE, b'{"value": 2.5}') == 0.25
    assert decode(store, PROBE, b"10130,225") is None, "the probe's bytes are JSON, whatever the gauge's are"


def test_json_then_the_default_pointer_then_identity(snapshots):
    assert decode(_bound(snapshots), PROBE, b'{"value": 0.183}') == 0.183


def test_a_stated_pointer_takes_this_sensors_field_of_a_shared_message(snapshots):
    store = _bound(snapshots, 'sensing:readingPointer "/soil/moisture"')
    assert decode(store, PROBE, b'{"soil": {"moisture": 0.2, "temp": 21}}') == 0.2


def test_a_missing_field_is_unread(snapshots, caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(_bound(snapshots), PROBE, b'{"temperature": 21}') is None
    assert "unread" in caplog.text


def test_bytes_that_are_no_document_are_unread(snapshots, caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(_bound(snapshots), PROBE, b"\xff\xfe") is None
    assert "unread" in caplog.text


def test_a_codec_nothing_here_implements_is_said(snapshots, caplog):
    store = _bound(snapshots, "sensing:decodedBy :Cbor")
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(store, PROBE, b"\xa1") is None
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
