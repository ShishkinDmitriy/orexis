"""What sensing contributes to history: an observation as one point, measured under its property's
own name — field `value`, tagged with the subject's and the sensor's ids, at the reading's own time
— contributed by `received` as it writes the observation, and nothing where no sink is loaded."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.sensing.history import FIELD, measurement_of, observation_point
from agent.sensing.received import received
from agent.series import HISTORY, Sink, install
from agent.store import update

T = "http://example.org/test#"
CLIMATE = "http://example.org/orexis/climate#"
AT = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
CASE = Path(__file__).parent / "received" / "a_first_reading_becomes_an_observation.trig"


@pytest.fixture
def history():
    written = []
    install(HISTORY, Sink(HISTORY, "b", lambda bucket, record: written.extend(record)))
    yield written
    install(HISTORY, None)


def _store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}world> {{ <{T}bed> orexis:localId "terrace_bed" . <{T}probe> orexis:localId "moisture_sensor_terrace" . }}
  GRAPH <{T}catalogue> {{ <{T}catalogue> a orexis:CatalogueGraph . <{T}world> a orexis:PublicGraph . }} }}""")
    return st


def test_an_observation_is_measured_under_its_propertys_name():
    point = observation_point(_store(), T + "bed", CLIMATE + "SoilMoisture", T + "probe", 0.2, AT)
    assert point == {"measurement": "SoilMoisture", "fields": {"value": 0.2},
                     "tags": {"plant": "terrace_bed", "sensor": "moisture_sensor_terrace"}, "time": AT}


def test_a_temperature_is_not_measured_as_soil_moisture():
    """The 0.1.0 shape wrote every property as `soil_moisture`; one measurement per property now."""
    assert measurement_of(CLIMATE + "AirTemperature") == "AirTemperature"
    assert FIELD == "value"


def test_a_subject_and_a_sensor_stating_no_id_are_not_tagged():
    point = observation_point(_store(), T + "elsewhere", CLIMATE + "SoilMoisture", T + "nameless", 0.5, AT)
    assert point["tags"] == {}


def test_received_contributes_the_observation_it_writes(monkeypatch, snapshots, history):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    assert received(store, snapshots.ME, T + "probe", b'{"value": 0.22}', snapshots.NOW)
    assert history == [{"measurement": "moisture", "fields": {"value": 0.22}, "tags": {}, "time": snapshots.NOW}]


def test_bytes_that_hold_no_reading_contribute_nothing(monkeypatch, snapshots, history):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASE)
    assert received(store, snapshots.ME, T + "probe", b'{"temperature": 21}', snapshots.NOW) is None
    assert history == []
