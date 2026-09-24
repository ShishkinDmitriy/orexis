"""The pipeline: bytes to a document by the codec, to a raw value by the pointer, to a quantity
by the scaling — and every way it refuses, which is None and a warning, never a number."""

from __future__ import annotations

import pytest

from pathlib import Path

from agent.sensing.pipeline import (DEFAULT_POINTER, CodecError, JsonCodec, PointerError, decode,
                                    resolve)
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
    store = _bound(snapshots, "<http://example.org/orexis/codec#decodedBy> <http://example.org/orexis/codec#Cbor>")
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
