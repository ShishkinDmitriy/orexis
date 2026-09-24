"""The pipeline: bytes to a document by the codec, to a raw value by the pointer, to a quantity
by the scaling — and every way it refuses, which is None and a warning, never a number."""

from __future__ import annotations

import pytest

from agent.sensing.pipeline import (DEFAULT_POINTER, CodecError, JsonCodec, PointerError, decode,
                                    resolve)
from agent.sensing.wiring import Sensor

TEST = "http://example.org/test#"


def _sensor(**fields) -> Sensor:
    return Sensor(uri=TEST + "probe", subject=TEST + "zz", observes=TEST + "moisture", **fields)


def test_json_then_the_default_pointer_then_identity():
    assert decode(_sensor(), b'{"value": 0.183}') == 0.183


def test_a_stated_pointer_takes_this_sensors_field_of_a_shared_message():
    assert decode(_sensor(pointer="/soil/moisture"), b'{"soil": {"moisture": 0.2, "temp": 21}}') == 0.2


def test_a_missing_field_is_unread(caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(_sensor(), b'{"temperature": 21}') is None
    assert "unread" in caplog.text


def test_bytes_that_are_no_document_are_unread(caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(_sensor(), b"\xff\xfe") is None
    assert "unread" in caplog.text


def test_a_codec_nothing_here_implements_is_said(caplog):
    with caplog.at_level("WARNING", logger="pipeline"):
        assert decode(_sensor(decoded_by="http://example.org/orexis/codec#Cbor"), b"\xa1") is None
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
