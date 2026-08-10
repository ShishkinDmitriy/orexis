"""Bytes become a quantity in three stages, and two of them are families.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[calibration]→ quantity

The pointer has its own file (`test_reading_pointer.py`) because it is a function, not a family.
What is tested here is the two families around it: that a member is selected from what the
BINDING declares, that an explicit statement can never be overruled by a default, and that a
build which could answer one question two ways is refused rather than resolved.

See knowledge/decisions/bytes-become-a-quantity-in-stages.md and issue #26.
"""

import pytest

from agent import loader
from agent.calibration import Calibration, calibration_for
from agent.calibrations.identity.terms import IDENTITY, LINEAR
from agent.codec import Codec, CodecError, codec_for
from agent.codecs.json.codec import JsonCodec
from agent.codecs.json.terms import CBOR, JSON
from agent.world import Sensor, load_self

from conftest import genesis_store, query_fn


def sensor(**binding) -> Sensor:
    """A sensor with only the binding fields a selection test cares about."""
    return Sensor(uri="urn:s", local_id="s", subject="urn:p", subject_id="p",
                  observes="urn:Moisture", **binding)


# --- what a binding that says nothing gets ---------------------------------

def test_a_binding_that_names_nothing_gets_the_defaults():
    """Every shipped world states neither, so this is what keeps them all reading."""
    assert isinstance(codec_for(sensor()), JsonCodec)
    assert calibration_for(sensor()).TERM == IDENTITY


def test_the_identity_calibration_changes_nothing():
    """Not `float(raw)` and not a rounding — the contract is that nothing happens."""
    calibration = calibration_for(sensor())
    for raw in (0.183, 0.0, 21.4, -5.5, 1e-9):
        assert calibration.apply(sensor(), raw) == raw


# --- the trap: a default must never shadow an explicit choice --------------

class _Defaulting(Codec):
    TERM = "urn:test:Defaulting"
    DEFAULT = True

    def decode(self, payload):
        return {"which": "default"}


class _Named(Codec):
    TERM = CBOR

    def decode(self, payload):
        return {"which": "named"}


def test_naming_a_codec_beats_the_default_even_when_the_default_is_asked_first(monkeypatch):
    """The failure this guards is invisible and total.

    Selection walks the members and takes the first that claims. A default written as "claim
    anything nobody else wanted" claims EVERYTHING when it is reached first, so every binding in
    the society would silently decode through it however carefully the world named another —
    and nothing would raise, because a wrong document still parses into some pointer's miss.

    So the default is deliberately put FIRST here, which is the order that breaks a naive
    implementation and the order `PROVIDES` gives no guarantee about anyway.
    """
    monkeypatch.setattr(loader, "codecs", lambda: (_Defaulting, _Named))

    chosen = codec_for(sensor(encoding=CBOR))
    assert isinstance(chosen, _Named), "a default overruled a binding that named a member"
    assert chosen.decode(b"")["which"] == "named"

    # and the mirror: silence still reaches the default, wherever it sits
    assert isinstance(codec_for(sensor()), _Defaulting)


def test_the_same_holds_for_calibrations(monkeypatch):
    class _DefaultingCal(Calibration):
        TERM = "urn:test:DefaultingCal"
        DEFAULT = True

        def apply(self, sensor, raw):
            return -1.0

    class _NamedCal(Calibration):
        TERM = LINEAR

        def apply(self, sensor, raw):
            return raw * 2

    monkeypatch.setattr(loader, "calibrations", lambda: (_DefaultingCal, _NamedCal))
    assert calibration_for(sensor(calibration=LINEAR)).apply(sensor(), 3.0) == 6.0


def test_a_binding_naming_a_member_this_build_lacks_is_reported_not_raised():
    """A leaner build is a deployment fact, the same shape as a capability nobody implements.

    The cost is one unread sensor and a warning — not an agent that will not start, which would
    turn a world naming an optional format into a society that cannot boot.
    """
    assert codec_for(sensor(encoding=CBOR)) is None
    assert calibration_for(sensor(calibration=LINEAR)) is None


# --- a build that could answer one question twice is refused ---------------

def test_two_defaults_are_refused_rather_than_resolved(monkeypatch):
    """The worse of the two ambiguities, because it needs no world to trigger it: every
    existing binding names nothing, so the wrong default is what the whole fleet gets."""
    class _A(Codec):
        TERM = "urn:test:A"
        DEFAULT = True

    class _B(Codec):
        TERM = "urn:test:B"
        DEFAULT = True

    monkeypatch.setattr(loader, "of_kind", lambda kind: (_FakePackage((_A, _B)),))
    with pytest.raises(RuntimeError, match="One default, or none"):
        loader._selectable(loader.CODECS)


def test_one_term_implemented_twice_is_refused(monkeypatch):
    class _A(Codec):
        TERM = JSON

    class _B(Codec):
        TERM = JSON

    monkeypatch.setattr(loader, "of_kind", lambda kind: (_FakePackage((_A, _B)),))
    with pytest.raises(RuntimeError, match="One term, one member"):
        loader._selectable(loader.CODECS)


def test_a_member_that_names_no_term_is_refused(monkeypatch):
    class _Nameless(Codec):
        pass

    monkeypatch.setattr(loader, "of_kind", lambda kind: (_FakePackage((_Nameless,)),))
    with pytest.raises(RuntimeError, match="names no TERM"):
        loader._selectable(loader.CODECS)


class _FakePackage:
    import_name = "agent.codecs.test"

    def __init__(self, classes):
        self._classes = classes

    def provides(self):
        return self._classes


# --- the codec actually decodes, and says so when it cannot ----------------

def test_the_json_codec_codes_both_ways():
    """A codec, not a parser: an agent instructs its boards as well as listening to them."""
    codec = JsonCodec()
    assert codec.decode(b'{"value": 0.183}') == {"value": 0.183}
    assert codec.decode(codec.encode({"sleep_s": 30})) == {"sleep_s": 30}


@pytest.mark.parametrize("payload", [b"", b"{", b"\xff\xfe not utf-8", b'{"a": }'])
def test_bytes_that_are_not_a_document_raise_one_error(payload):
    """Every way `json.loads` can fail becomes one `CodecError` — the caller does not care
    which, because a payload that is not a document has no reading in it either way."""
    with pytest.raises(CodecError):
        JsonCodec().decode(payload)


# --- the world states what its numbers mean --------------------------------

def test_the_sensing_world_states_a_unit_for_every_sensor():
    """Two of these three are fractions and look identical; the third is degrees.

    Before this the distinction lived in prose — `vocabulary/water` saying the valuation is
    "denominated in soil moisture" — while the store held all three as bare decimals. A unit is
    the only thing that says 0.46 humidity and 21.4 degrees are not the same kind of number.
    """
    me = load_self(query_fn(genesis_store(world="sensing")), "fern")
    units = {s.local_id: s.quantity_unit for s in me.sensors}
    assert units == {
        "moisture_sensor_fern": "http://qudt.org/vocab/unit/UNITLESS",
        "air_temp_fern": "http://qudt.org/vocab/unit/DEG_C",
        "air_humidity_fern": "http://qudt.org/vocab/unit/UNITLESS",
    }


def test_stating_a_unit_converted_nothing():
    """Identity stays identity. This is the assertion that this change declared meaning and
    did not touch a single number — #26 is where conversion would arrive, deliberately not
    here, and a calibration that quietly scaled would make every band in the world wrong."""
    me = load_self(query_fn(genesis_store(world="sensing")), "fern")
    for s in me.sensors:
        assert s.calibration is None                      # none stated -> identity
        assert calibration_for(s).TERM == IDENTITY
        assert calibration_for(s).apply(s, 0.183) == 0.183
