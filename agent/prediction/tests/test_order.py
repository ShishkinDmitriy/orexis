"""`order`: the properties in the order their keys are predicted (#996) — read off the drift texts, a
property after every property its drifts read, a cycle refused, a text that cannot be read reading
every property."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.prediction.order import Cycle, order
from agent.store import update

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
T = "http://example.org/test#"
MOISTURE, HUMIDITY, WARMTH, LIGHT = T + "moisture", T + "humidity", T + "warmth", T + "light"


def _drift(store, name: str, moves: str, reads: str = "", text: str | None = None) -> None:
    """A drift moving `moves` whose rate reads an observation of `reads`, or says `text`."""
    rate = text if text is not None else f"""PREFIX : <{T}>
        SELECT ?rate WHERE {{ ?o sosa:hasFeatureOfInterest ?x ; sosa:observedProperty <{reads}> ; sosa:hasSimpleResult ?v .
                              BIND(xsd:double(?v) / 86400.0 AS ?rate) }}"""
    rate = rate.replace('"""', "'")
    update(store, f"""PREFIX prediction: <http://example.org/orexis/prediction#>
INSERT DATA {{ GRAPH <{T}actions> {{ <{T}{name}> a prediction:Drift ; prediction:moves <{moves}> ; prediction:rate \"\"\"{rate}\"\"\" }} }}""")


def test_a_property_is_predicted_after_every_property_its_drifts_read(snapshots):
    """The pot's drying reads nothing: one property, itself. Add the air, whose humidity moves by
    nothing another key says, and a soil drift reading the air: the air comes first, whatever the IRIs'
    order; and a drift reading its own property — the dose reads the soil it lifts — is no dependency."""
    store = snapshots.stand_in(WORLD)
    assert order(store) == [MOISTURE]
    _drift(store, "Evaporating", MOISTURE, HUMIDITY)
    _drift(store, "Humidifying", HUMIDITY, text="SELECT ?rate WHERE { BIND(0.1 AS ?rate) }")
    _drift(store, "Dosed", MOISTURE, MOISTURE)
    assert order(store) == [HUMIDITY, MOISTURE], "humidity sorts after moisture by IRI, and is read by it"
    assert order(store, {MOISTURE, HUMIDITY, LIGHT}) == [HUMIDITY, LIGHT, MOISTURE], "a property nobody moves has no place to wait for"


def test_after_an_arrival_the_keys_that_depend_on_it_are_walked_and_no_other(snapshots):
    """`after`: the air's percept arriving makes the air stale and the soil with it, which reads the air;
    the soil's arriving makes the soil alone stale; the warmth, which nothing reads and which reads
    nothing, waits for neither."""
    store = snapshots.stand_in(WORLD)
    _drift(store, "Evaporating", MOISTURE, HUMIDITY)
    _drift(store, "Humidifying", HUMIDITY, text="SELECT ?rate WHERE { BIND(0.1 AS ?rate) }")
    _drift(store, "Warming", WARMTH, text="SELECT ?rate WHERE { BIND(0.1 AS ?rate) }")
    assert order(store, after={HUMIDITY}) == [HUMIDITY, MOISTURE]
    assert order(store, after={MOISTURE}) == [MOISTURE]
    assert order(store, after={WARMTH}) == [WARMTH]
    assert order(store, after=set()) == []


def test_two_properties_whose_drifts_read_each_other_are_a_cycle_and_refused(snapshots):
    store = snapshots.stand_in(WORLD)
    _drift(store, "Evaporating", MOISTURE, HUMIDITY)
    _drift(store, "Condensing", HUMIDITY, MOISTURE)
    with pytest.raises(Cycle, match="humidity, moisture"):
        order(store)


def test_a_text_that_cannot_be_read_reads_every_property_and_is_predicted_last(snapshots):
    """A variable where the property stands, or a text the parser refuses: the safe side is that it reads
    everything, so it comes last — and two such texts are a cycle, said rather than guessed at."""
    store = snapshots.stand_in(WORLD)
    _drift(store, "Humidifying", HUMIDITY, text="SELECT ?rate WHERE { BIND(0.1 AS ?rate) }")
    _drift(store, "Warming", WARMTH, text="SELECT ?rate WHERE { ?o sosa:observedProperty ?any . BIND(0.1 AS ?rate) }")
    assert order(store) == [HUMIDITY, MOISTURE, WARMTH]
    _drift(store, "Lighting", LIGHT, text="SELECT ?rate WHERE { this will not parse")
    with pytest.raises(Cycle, match="light, warmth"):
        order(store)
