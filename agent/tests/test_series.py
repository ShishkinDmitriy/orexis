"""The series store: an observation written as the point the 0.1.0 agent wrote — `soil_moisture`,
field `value`, tagged plant, sensor and property, at the reading's own time — and a refusal said in
the log, never raised."""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox

from agent.series import Series
from agent.store import update

T = "http://example.org/test#"


def _store():
    st = ox.Store()
    update(st, f"""INSERT DATA {{
  GRAPH <{T}world> {{ <{T}bed> orexis:localId "terrace_bed" . <{T}probe> orexis:localId "moisture_sensor_terrace" . }}
  GRAPH <{T}observed> {{ <{T}o> sosa:hasSimpleResult 0.2 ; sosa:resultTime "2026-01-01T12:00:00+00:00"^^xsd:dateTime ;
      sosa:observedProperty <http://example.org/orexis/climate#SoilMoisture> ; sosa:hasFeatureOfInterest <{T}bed> ;
      sosa:madeBySensor <{T}probe> }}
  GRAPH <{T}catalogue> {{ <{T}catalogue> a orexis:CatalogueGraph . <{T}world> a orexis:PublicGraph . }} }}""")
    return st


def test_an_observation_is_the_point_the_panels_draw():
    written = []
    series = Series("terrace-terrace", lambda bucket, record: written.append((bucket, record)))
    assert series.record(_store(), T + "observed") == 1
    (bucket, (point,)), = written
    assert bucket == "terrace-terrace"
    assert point == {"measurement": "soil_moisture", "fields": {"value": 0.2},
                     "tags": {"property": "SoilMoisture", "plant": "terrace_bed", "sensor": "moisture_sensor_terrace"},
                     "time": datetime(2026, 1, 1, 12, tzinfo=timezone.utc)}


def test_a_store_that_refuses_costs_the_agent_nothing(caplog):
    def refuse(bucket, record):
        raise ConnectionError("down")
    assert Series("b", refuse).record(_store(), T + "observed") == 0
    assert "refused" in caplog.text


def test_no_store_named_is_no_series():
    assert Series.from_environment({}) is None
