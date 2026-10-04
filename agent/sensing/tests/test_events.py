"""What sensing says happened: an observation, which is history as one point measured under its
property's own name — field `value`, tagged with the subject's and the sensor's ids, at the reading's
own time — and a metric by its interval and the sensor; and the silence, a level."""

from __future__ import annotations

from datetime import datetime, timezone

from agent.metrics import LEVEL, TAG, counted, fields_of, marked, measurement, reported
from agent.sensing import events
from agent.sensing.events import FIELD, RAW, Doubted, Observed, measurement_of

CLIMATE = "http://example.org/orexis/climate#"
AT = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_an_observation_is_measured_under_its_propertys_name():
    """Tagged for the SOSA roles — `feature`, what it is of, and `sensor`, what made it — and the
    subject's tag is no longer `plant`, the domain word #834 took out of the shape as #822 took it
    out of the measurement. An observation with no raw number writes `value` alone, as every point
    before #894 did."""
    said = Observed(CLIMATE + "SoilMoisture", 0.2, AT, sensor="moisture_sensor_terrace",
                    sensor_id="moisture_sensor_terrace", feature_id="terrace_bed")
    assert said.point() == {"measurement": "SoilMoisture", "fields": {"value": 0.2},
                            "tags": {"feature": "terrace_bed", "sensor": "moisture_sensor_terrace"}, "time": AT}
    assert "plant" not in said.point()["tags"]


def test_the_raw_count_rides_beside_the_reading_and_is_no_metric():
    """A probe reading 0.2 through a scaling of counts: the point carries the count the sensor gave
    beside the reading, so reflection can ask the history for a count that has not moved without
    going through the scaling under doubt (#894). The field is the point's and not the metric's: the
    `received` metric reports the interval and the cadence as before."""
    said = Observed(CLIMATE + "SoilMoisture", 0.2, AT, sensor="probe", sensor_id="probe", feature_id="bed", raw=1930.0)
    assert said.point()["fields"] == {FIELD: 0.2, RAW: 1930.0}
    assert "raw" not in marked(Observed) and set(marked(Observed)) == {"sensor", "interval_s", "cadence_s"}


def test_a_doubted_sensor_is_a_level_per_sensor():
    """Silent and stuck, each as it stands, tagged by the sensor: a report of state and not a count,
    so a window writes the last said and a sensor nobody doubts is on no point."""
    assert measurement(Doubted) == "doubted" and not counted(Doubted)
    assert fields_of(Doubted, TAG) == ("sensor",) and fields_of(Doubted, LEVEL) == ("silent", "stuck")
    assert Doubted(sensor="probe") == Doubted(sensor="probe", silent=0, stuck=0)


def test_a_temperature_is_not_measured_as_soil_moisture():
    """The 0.1.0 shape wrote every property as `soil_moisture`; one measurement per property now."""
    assert measurement_of(CLIMATE + "AirTemperature") == "AirTemperature"
    assert FIELD == "value"


def test_a_subject_and_a_sensor_stating_no_id_are_not_tagged():
    assert Observed(CLIMATE + "SoilMoisture", 0.5, AT, sensor="nameless").point()["tags"] == {}


def test_what_is_reported_is_the_interval_by_sensor_the_silence_and_the_sensors_doubted():
    assert {measurement(c) for c in reported(events)} == {"received", "silence", "doubted"}
