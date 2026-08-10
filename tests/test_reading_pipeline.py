"""Bytes become a quantity in three stages, and two of them are derived at genesis.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[calibration]→ quantity

The pointer has its own file (`test_reading_pointer.py`) because it is a function, not a family.
What is tested here is the two families around it: that which member serves a sensor is DERIVED
from what the world states — or from its silence — exactly as a capability is, and that the
runtime looks the answer up rather than searching for it.

These run the real rules over the real worlds, so they check the thing the design rests on: a
sensor's pipeline is a fact in the graph, not the outcome of a Python loop over imported classes.

See knowledge/decisions/bytes-become-a-quantity-in-stages.md and issue #26.
"""

import pytest

from agent import genesis, loader
from agent.calibration import calibration_for
from agent.calibrations.identity.terms import IDENTITY, LINEAR
from agent.codec import Codec, CodecError, codec_for
from agent.codecs.json.codec import JsonCodec
from agent.codecs.json.terms import CBOR, JSON
from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH
from agent.store import PREFIXES, bindings
from agent.world import load_self

from conftest import genesis_store, query_fn


def sensors_of(world="sensing", agent="fern"):
    return {s.local_id: s for s in load_self(query_fn(genesis_store(world=world)), agent).sensors}


# --- what genesis writes when a world states nothing -----------------------

def test_every_sensor_is_given_a_codec_and_a_calibration():
    """No world states either, so all six facts here are the derivation's own work.

    That is the whole point of deriving a default rather than applying one in Python: before
    this, every sensor in every world was decoded as JSON by a flag on a class — true,
    load-bearing, and impossible to query. Now the graph says so.
    """
    for sensor in sensors_of().values():
        assert sensor.decoded_by == JSON
        assert sensor.calibrated_by == IDENTITY


def test_the_conclusions_land_in_the_derived_graph_not_the_world():
    """A world states premises; genesis writes conclusions. The same rule that keeps
    `ag:hasCapability` out of `world.ttl` applies to a fact borne by a binding."""
    store = genesis_store(world="sensing")
    asserted = bindings(store.query(PREFIXES + f"""
        SELECT ?s WHERE {{ GRAPH <{WORLD_GRAPH}> {{
          {{ ?s codec:decodedBy ?a }} UNION {{ ?s calibration:calibratedBy ?b }} }} }}"""))
    assert asserted == [], "a conclusion was stated in the world rather than derived"

    derived = bindings(store.query(PREFIXES + f"""
        SELECT ?s WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{ ?s codec:decodedBy ?c }} }}"""))
    assert len(derived) == 3


def test_the_other_worlds_get_them_too():
    """Nothing about this is specific to the world that grew a second peripheral."""
    for world, agent in (("society", "fern"), ("simulation", "tomato")):
        for sensor in sensors_of(world, agent).values():
            assert sensor.decoded_by == JSON and sensor.calibrated_by == IDENTITY


# --- an explicit statement beats the default, and the rule decides it ------

def _world_stating(premise: str, obj: str):
    """The sensing world with one premise added to the moisture probe, re-derived.

    Only the RATIFIED half is edited — the premise — and then the conclusions are cleared and
    recomputed, exactly as `refresh_public` does. Skipping the clear would leave the previous
    answer sitting beside the new one, which is how a derivation test passes while asserting
    nothing.
    """
    store = genesis_store(world="sensing")
    store.update(PREFIXES + f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern {premise} {obj} }} }}
        WHERE {{}}""")
    store.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        store.update(genesis.substitute(rule.read_text(), store))
    return store


def test_stating_an_encoding_beats_the_default():
    """The trap this replaces was a Python one — a default class claiming anything nobody else
    wanted, resolved by `PROVIDES` iteration order, which guarantees nothing. The two rules are
    disjoint by `FILTER NOT EXISTS`, so there is no order left to get wrong."""
    me = load_self(query_fn(_world_stating("codec:encoding", "codec:Cbor")), "fern")
    probe = {s.local_id: s for s in me.sensors}["moisture_sensor_fern"]
    assert probe.decoded_by == CBOR, "the default overruled a world that named a member"

    # and its neighbours on the same board are untouched
    others = {s.decoded_by for s in me.sensors if s.local_id != "moisture_sensor_fern"}
    assert others == {JSON}


def test_stating_a_curve_beats_the_default():
    me = load_self(query_fn(_world_stating("calibration:curve", "calibration:Linear")), "fern")
    probe = {s.local_id: s for s in me.sensors}["moisture_sensor_fern"]
    assert probe.calibrated_by == LINEAR


def test_a_stated_premise_produces_exactly_one_conclusion():
    """Both rules firing for one sensor is what a second package claiming the default would
    look like, and it is what the shape refuses. Here it must not happen at all."""
    store = _world_stating("codec:encoding", "codec:Cbor")
    rows = bindings(store.query(PREFIXES + f"""
        SELECT ?c WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
          ag:moisture_sensor_fern codec:decodedBy ?c }} }}"""))
    assert len(rows) == 1


# --- the runtime looks it up, and says so when it cannot -------------------

def test_the_lookup_finds_the_implementation():
    probe = sensors_of()["moisture_sensor_fern"]
    assert isinstance(codec_for(probe), JsonCodec)
    assert calibration_for(probe).TERM == IDENTITY


def test_a_member_this_build_does_not_implement_is_reported_not_raised():
    """A world may name a declared-but-unimplemented member — `codec:Cbor` is exactly the
    position `ag:Polling` and `ag:Consulting` hold. The shapes deliberately allow it, so the
    honest cost is one unread sensor and a warning rather than a society that cannot start."""
    probe = sensors_of()["moisture_sensor_fern"]
    assert codec_for(probe.__class__(**{**vars(probe), "decoded_by": CBOR})) is None
    assert calibration_for(probe.__class__(**{**vars(probe), "calibrated_by": LINEAR})) is None


def test_the_identity_calibration_changes_nothing():
    """Not `float(raw)` and not a rounding — the contract is that nothing happens."""
    probe = sensors_of()["moisture_sensor_fern"]
    calibration = calibration_for(probe)
    for raw in (0.183, 0.0, 21.4, -5.5, 1e-9):
        assert calibration.apply(probe, raw) == raw


# --- a build that could answer one question twice is refused ---------------

def test_one_term_implemented_twice_is_refused(monkeypatch):
    class _A(Codec):
        TERM = JSON

    class _B(Codec):
        TERM = JSON

    monkeypatch.setattr(loader, "of_kind", lambda kind: (_FakePackage((_A, _B)),))
    with pytest.raises(RuntimeError, match="One term, one member"):
        loader._members(loader.CODECS)


def test_a_member_that_names_no_term_is_refused(monkeypatch):
    class _Nameless(Codec):
        pass

    monkeypatch.setattr(loader, "of_kind", lambda kind: (_FakePackage((_Nameless,)),))
    with pytest.raises(RuntimeError, match="names no TERM"):
        loader._members(loader.CODECS)


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
    units = {name: s.quantity_unit for name, s in sensors_of().items()}
    assert units == {
        "moisture_sensor_fern": "http://qudt.org/vocab/unit/UNITLESS",
        "air_temp_fern": "http://qudt.org/vocab/unit/DEG_C",
        "air_humidity_fern": "http://qudt.org/vocab/unit/UNITLESS",
    }


def test_stating_a_unit_converted_nothing():
    """Identity stays identity. This is the assertion that this change declared meaning and did
    not touch a single number — #26 is where conversion would arrive, deliberately not here, and
    a calibration that quietly scaled would make every band in every world wrong."""
    for sensor in sensors_of().values():
        assert calibration_for(sensor).apply(sensor, 0.183) == 0.183
