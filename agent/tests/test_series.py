"""The series store: an observation written as a point measured under its property's own name —
field `value`, tagged plant and sensor, at the reading's own time — and a refusal said in the log,
never raised."""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox

from agent.series import Series
from agent.store import update

T = "http://example.org/test#"


def _store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}world> {{ <{T}bed> orexis:localId "terrace_bed" . <{T}probe> orexis:localId "moisture_sensor_terrace" .
                      <{T}thermometer> orexis:localId "air_temp_terrace" . }}
  GRAPH <{T}observed> {{ <{T}o> sosa:hasSimpleResult 0.2 ; sosa:resultTime "2026-01-01T12:00:00+00:00"^^xsd:dateTime ;
      sosa:observedProperty <http://example.org/orexis/climate#SoilMoisture> ; sosa:hasFeatureOfInterest <{T}bed> ;
      sosa:madeBySensor <{T}probe> }}
  GRAPH <{T}warm> {{ <{T}t> sosa:hasSimpleResult 14.5 ; sosa:resultTime "2026-01-01T12:00:00+00:00"^^xsd:dateTime ;
      sosa:observedProperty <http://example.org/orexis/climate#AirTemperature> ; sosa:hasFeatureOfInterest <{T}bed> ;
      sosa:madeBySensor <{T}thermometer> }}
  GRAPH <{T}catalogue> {{ <{T}catalogue> a orexis:CatalogueGraph . <{T}world> a orexis:PublicGraph . }} }}""")
    return st


def test_an_observation_is_measured_under_its_propertys_name():
    written = []
    series = Series("terrace-terrace", lambda bucket, record: written.append((bucket, record)))
    assert series.record(_store(), T + "observed") == 1
    (bucket, (point,)), = written
    assert bucket == "terrace-terrace"
    assert point == {"measurement": "SoilMoisture", "fields": {"value": 0.2},
                     "tags": {"plant": "terrace_bed", "sensor": "moisture_sensor_terrace"},
                     "time": datetime(2026, 1, 1, 12, tzinfo=timezone.utc)}


def test_a_temperature_is_not_measured_as_soil_moisture():
    """The 0.1.0 shape wrote every property as `soil_moisture`; one measurement per property now."""
    written = []
    series = Series("b", lambda bucket, record: written.extend(record))
    store = _store()
    series.record(store, T + "observed")
    series.record(store, T + "warm")
    assert sorted((p["measurement"], p["fields"]["value"]) for p in written) == [
        ("AirTemperature", 14.5), ("SoilMoisture", 0.2)]


def test_a_store_that_refuses_costs_the_agent_nothing(caplog):
    def refuse(bucket, record):
        raise ConnectionError("down")
    assert Series("b", refuse).record(_store(), T + "observed") == 0
    assert "refused" in caplog.text


def test_no_store_named_is_no_series():
    assert Series.from_environment({}) is None
