"""The askables an agent answers: read off its askable graphs — sensing's and execution's as they ship, beside one of
the case's own that takes a field — each a tool of its fields, answered by its own select over the kinds it reads
with what the asker filled, writing nothing; and the status, every askable that takes no field, a section each."""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

from agent.ontology import ASKABLE_GRAPH, OREXIS
from agent.store import catalogue_of
from agent.translation.askable import answered, askables, lines, said, status, tool_of

ROOT = Path(__file__).resolve().parents[3]
WORLD = Path(__file__).parent / "worlds" / "two_readings_and_an_intention.trig"
ME = "http://example.org/test#keeper"
SHIPPED = [ROOT / "agent" / "sensing" / "askables.ttl", ROOT / "agent" / "execution" / "askables.ttl"]


def _store(snapshots):
    """The case, with sensing's and execution's askables as the boot would hold them: each its own graph, said to
    be an askable graph."""
    store = snapshots.stand_in(WORLD)
    catalogue = ox.NamedNode(catalogue_of(store))
    for path in SHIPPED:
        store.load(path.read_text(), format=ox.RdfFormat.TURTLE, base_iri=path.as_uri(), to_graph=ox.NamedNode(path.as_uri()))
        for kind in (ASKABLE_GRAPH, OREXIS + "Graph"):
            store.add(ox.Quad(ox.NamedNode(path.as_uri()), ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                              ox.NamedNode(kind), catalogue))
    return store


def test_the_askables_are_read_off_every_askable_graph_with_their_fields_and_kinds(snapshots):
    known = {a.name: a for a in askables(_store(snapshots))}
    assert set(known) == {"observes", "does", "reading_of"}
    assert known["observes"].reads == ("http://example.org/orexis/sensing#ObservationGraph",) and not known["observes"].fields
    (field,) = known["reading_of"].fields
    assert field.name == "sensor" and field.required and dict(field.choices) == {
        "the probe": "http://example.org/test#probe", "thermo": "http://example.org/test#thermo"}
    assert tool_of(known["reading_of"]) == {
        "name": "reading_of", "description": "what one sensor last read",
        "input_schema": {"type": "object", "properties": {"sensor": {"type": "string", "enum": ["the probe", "thermo"],
                                                                     "description": "which sensor"}},
                         "required": ["sensor"], "additionalProperties": False}}


def test_an_askable_is_answered_by_its_own_select_with_what_was_filled_and_writes_nothing(snapshots):
    store = _store(snapshots)
    known = {a.name: a for a in askables(store)}
    before = len(store)
    assert answered([store], known["reading_of"], {"sensor": "the probe"}) == [{"reading": "0.2", "at": "2026-01-01T12:00:00Z"}]
    assert answered([store], known["reading_of"], {"sensor": "a sensor nobody states"}) is None, "a label the world does not state"
    assert answered([store], known["reading_of"], {}) is None, "a field it requires"
    assert lines(answered([store], known["observes"])) == [
        "observed: SoilMoisture, of: bed, reading: 0.2, sensor: probe, at: 2026-01-01 12:00 UTC",
        "reading: 14.5, sensor: thermo, at: 2026-01-01 11:59 UTC"], "the latest percept of each sensor"
    assert len(store) == before, "an askable writes nothing"


def test_the_status_is_every_askable_that_takes_no_field_a_section_each(snapshots):
    store = _store(snapshots)
    known = askables(store)
    assert status([store, None], known, ME, snapshots.NOW).split("\n") == [
        "keeper at 2026-01-01 12:00 UTC",
        "does:",
        " - pursues: water_the_bed, since: 2026-01-01 11:00 UTC, at: dose",
        "observes:",
        " - observed: SoilMoisture, of: bed, reading: 0.2, sensor: probe, at: 2026-01-01 12:00 UTC",
        " - reading: 14.5, sensor: thermo, at: 2026-01-01 11:59 UTC",
    ], "the intention standing and not the one resolved; and no section for the askable that takes a field"
    assert status([store], [], ME, snapshots.NOW) == "keeper at 2026-01-01 12:00 UTC\nnothing to say yet"


def test_a_value_is_said_as_a_person_reads_it():
    assert said("http://example.org/test#bed") == "bed" and said("2026-01-01T12:00:00+00:00") == "2026-01-01 12:00 UTC"
    assert said("14.5") == "14.5" and said("2026-01-01T12:00:00+02:00") == "2026-01-01 12:00"
