"""Bytes become a quantity in three stages, and two of them are derived at genesis.

    bytes ─[codec]→ document ─[pointer]→ raw value ─[scaling]→ quantity

The pointer has its own file (`test_reading_pointer.py`) because it is a function, not a family.
What is tested here is the two families around it: that which member serves a sensor is DERIVED
from what the world states — or from its silence — exactly as a capability is, and that the
runtime looks the answer up rather than searching for it.

These run the real rules over the real worlds, so they check the thing the design rests on: a
sensor's pipeline is a fact in the graph, not the outcome of a Python loop over imported classes.

See knowledge/decisions/bytes-become-a-quantity-in-stages.md and issue #26.
"""

import pytest

from agent import genesis

from assembly import loader
from packages.capability.sensing.scaling import scaling_for
from packages.scaling.identity.terms import IDENTITY, LINEAR
from packages.capability.sensing.codec import Codec, CodecError, codec_for
from packages.codec.json.codec import JsonCodec
from packages.codec.json.terms import CBOR, JSON
from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH
from agent.store import PREFIXES, bindings

from conftest import genesis_store, query_fn, load_wired


def sensors_of(world="sensing", agent="fern"):
    return {s.local_id: s for s in load_wired(query_fn(genesis_store(world=world)), agent).sensors}


# --- what genesis writes when a world states nothing -----------------------

def test_every_sensor_is_given_a_codec_and_a_calibration():
    """No world states either, so all six facts here are the derivation's own work.

    That is the whole point of deriving a default rather than applying one in Python: before
    this, every sensor in every world was decoded as JSON by a flag on a class — true,
    load-bearing, and impossible to query. Now the graph says so.
    """
    for sensor in sensors_of().values():
        assert sensor.decoded_by == JSON
        assert sensor.scaled_by == IDENTITY


def test_the_conclusions_land_in_the_derived_graph_not_the_world():
    """A world states premises; genesis writes conclusions. The same rule that keeps
    `ag:hasCapability` out of `world.ttl` applies to a fact borne by a binding."""
    store = genesis_store(world="sensing")
    asserted = bindings(store.query(PREFIXES + f"""
        SELECT ?s WHERE {{ GRAPH <{WORLD_GRAPH}> {{
          {{ ?s codec:decodedBy ?a }} UNION {{ ?s scaling:scaledBy ?b }} }} }}"""))
    assert asserted == [], "a conclusion was stated in the world rather than derived"

    # Two, not three: `sensing` has three sensors and TWO streams — one reading topic the
    # board publishes on and one command topic it listens to. That the count fell is the
    # change: an encoding used to be copied onto every sensor and is now stated once per
    # stream, which is the only place it was ever a fact about.
    derived = bindings(store.query(PREFIXES + f"""
        SELECT ?s WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{ ?s codec:decodedBy ?c }} }}"""))
    assert len(derived) == 2


def test_the_other_worlds_get_them_too():
    """Nothing about this is specific to the world that grew a second peripheral."""
    for world, agent in (("sensing", "fern"), ("simulation", "tomato")):
        for sensor in sensors_of(world, agent).values():
            assert sensor.decoded_by == JSON and sensor.scaled_by == IDENTITY


# --- an explicit statement beats the default, and the rule decides it ------

AIR = ("<http://example.org/orexis/world/sensing#air_temp_fern>", "<http://example.org/orexis/world/sensing#air_humidity_fern>")
BOARD = ("<http://example.org/orexis/world/sensing#moisture_sensor_fern>",) + AIR


def _world_stating(premise: str, obj: str, subjects=("<http://example.org/orexis/world/sensing#moisture_sensor_fern>",)):
    """The sensing world with one premise added to some devices, re-derived.

    `subjects` exists because the two families have different bearers. A curve is the SENSOR's,
    so stating it on one probe is a complete world. An encoding is the STREAM's, and those three
    devices share one — so stating it on one of them is a world where two devices disagree about
    one topic, which is exactly what the shape now refuses. Agreement has to be stated by
    everyone on the stream, and that is the model being honest rather than the test being
    awkward.

    Only the RATIFIED half is edited — the premise — and then the conclusions are cleared and
    recomputed, exactly as `refresh_public` does. Skipping the clear would leave the previous
    answer sitting beside the new one, which is how a derivation test passes while asserting
    nothing.
    """
    store = genesis_store(world="sensing")
    triples = " . ".join(f"{s} {premise} {obj}" for s in subjects)
    store.update(PREFIXES + f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ {triples} }} }}
        WHERE {{}}""")
    store.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        store.update(genesis.substitute(rule.read_text(), store))
    return store


def test_stating_an_encoding_beats_the_default():
    """The trap this replaces was a Python one — a default class claiming anything nobody else
    wanted, resolved by `PROVIDES` iteration order, which guarantees nothing. The two rules are
    disjoint by `FILTER NOT EXISTS`, so there is no order left to get wrong.

    Stated by every device on the stream, because the conclusion is the stream's. All three
    sensors then read through the same channel and all three see CBOR — which is the point: an
    encoding is not something one sensor can have and its neighbour not, when the bytes are the
    same bytes.
    """
    store = _world_stating("codec:encoding", "codec:Cbor", subjects=BOARD)
    me = load_wired(query_fn(store), "fern")
    assert {s.decoded_by for s in me.sensors} == {CBOR}, \
        "the default overruled a world that named a member"


def test_one_device_disagreeing_about_a_shared_stream_is_refused():
    """The hole this move exists to close.

    Three sensors publish on one topic. Give ONE of them an encoding and the other two are not
    silent — silence is a claim of JSON — so the stream carries two conclusions. While the fact
    sat on each sensor there was nothing to compare and this validated clean; the disagreement
    would have surfaced as a board's readings decoding through the wrong format at the first
    message.
    """
    store = _world_stating("codec:encoding", "codec:Cbor")  # the probe alone
    rows = bindings(store.query(PREFIXES + f"""
        SELECT ?c WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
          ?ch a mqtt:Channel ; mqtt:channelTopic "sensors/moisture_sensor_fern/reading" ;
              codec:decodedBy ?c }} }}"""))
    assert len(rows) == 2, "a stream with two claims on it must show both, for the shape to see"


def test_stating_a_curve_beats_the_default():
    me = load_wired(query_fn(_world_stating("scaling:curve", "scaling:Linear")), "fern")
    probe = {s.local_id: s for s in me.sensors}["moisture_sensor_fern"]
    assert probe.scaled_by == LINEAR


def test_a_stated_premise_produces_exactly_one_conclusion():
    """Both rules firing for one sensor is what a second package claiming the default would
    look like, and it is what the shape refuses. Here it must not happen at all."""
    store = _world_stating("codec:encoding", "codec:Cbor", subjects=BOARD)
    rows = bindings(store.query(PREFIXES + f"""
        SELECT ?c WHERE {{ GRAPH <{WORLD_DERIVED_GRAPH}> {{
          ?ch a mqtt:Channel ; mqtt:channelTopic "sensors/moisture_sensor_fern/reading" ;
              codec:decodedBy ?c }} }}"""))
    assert len(rows) == 1


# --- the runtime looks it up, and says so when it cannot -------------------

def test_the_lookup_finds_the_implementation():
    probe = sensors_of()["moisture_sensor_fern"]
    assert isinstance(codec_for(probe), JsonCodec)
    assert scaling_for(probe).TERM == IDENTITY


def test_a_member_this_build_does_not_implement_is_reported_not_raised():
    """A world may name a declared-but-unimplemented member — `codec:Cbor` is exactly the
    position `sensing:Polling` and `review:Consulting` hold. The shapes deliberately allow it, so the
    honest cost is one unread sensor and a warning rather than a world that cannot start."""
    probe = sensors_of()["moisture_sensor_fern"]
    assert codec_for(probe.__class__(**{**vars(probe), "decoded_by": CBOR})) is None
    assert scaling_for(probe.__class__(**{**vars(probe), "scaled_by": LINEAR})) is None


def test_the_identity_calibration_changes_nothing():
    """Not `float(raw)` and not a rounding — the contract is that nothing happens."""
    probe = sensors_of()["moisture_sensor_fern"]
    calibration = scaling_for(probe)
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
    import_name = "packages.codec.test"

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

    Before this the distinction lived in prose — `packages/plant/water` saying the valuation is
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
        assert scaling_for(sensor).apply(sensor, 0.183) == 0.183
