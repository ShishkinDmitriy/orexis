"""What sensing says happened: an observation, which is history as one point measured under its
property's own name — field `value`, tagged with the subject's and the sensor's ids, at the reading's
own time — and a metric by its interval and the sensor; and the silence, a level."""

from __future__ import annotations

from datetime import datetime, timezone

from agent.metrics import measurement, reported
from agent.sensing import events
from agent.sensing.events import FIELD, Observed, measurement_of

CLIMATE = "http://example.org/orexis/climate#"
AT = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_an_observation_is_measured_under_its_propertys_name():
    said = Observed(CLIMATE + "SoilMoisture", 0.2, AT, sensor="moisture_sensor_terrace",
                    sensor_id="moisture_sensor_terrace", subject_id="terrace_bed")
    assert said.point() == {"measurement": "SoilMoisture", "fields": {"value": 0.2},
                            "tags": {"plant": "terrace_bed", "sensor": "moisture_sensor_terrace"}, "time": AT}


def test_a_temperature_is_not_measured_as_soil_moisture():
    """The 0.1.0 shape wrote every property as `soil_moisture`; one measurement per property now."""
    assert measurement_of(CLIMATE + "AirTemperature") == "AirTemperature"
    assert FIELD == "value"


def test_a_subject_and_a_sensor_stating_no_id_are_not_tagged():
    assert Observed(CLIMATE + "SoilMoisture", 0.5, AT, sensor="nameless").point()["tags"] == {}


def test_what_is_reported_is_the_interval_by_sensor_and_the_silence():
    assert {measurement(c) for c in reported(events)} == {"received", "silence"}
