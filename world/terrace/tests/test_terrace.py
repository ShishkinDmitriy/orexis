"""The terrace on Agent 0.2.0: the sentinel's one message is five observations — the probe's raw
count rescaled to a moisture through the two points the world states, the air's three values and the
battery's voltage as they come — the soil's side is concluded against the bed's range, and the agent
— holding no desire — watches and sends nothing, and keeps running, since a transport reaches it."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent import clock
from agent.ontology import OREXIS, STATE
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows
from agent.series import HISTORY, Sink, install
from agent.transport.mqtt.driver import Mqtt

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT = "http://example.org/orexis/world/terrace#terrace_agent"
#  WHAT THE BOARD PUBLISHES: the probe's count, always an array of readings — here one, 710, a fifth of the way from dry (785) to wet (410)
#  through the scaling world.ttl states of the probe — the air, and the battery.
MESSAGE = json.dumps({"moisture_raw": [{"value": 710, "age_s": 0}], "temperature": 14.5, "humidity": 0.8, "pressure": 1012,
                      "battery": 3.91}).encode()


class Broker:
    def __init__(self):
        self.subscribed, self.published = [], []

    def subscribe(self, pattern):
        self.subscribed.append(pattern)

    def publish(self, topic, payload, retain=False):
        self.published.append(topic)


@pytest.fixture
def history():
    """The history sink the environment would name, as `orexis-compose terrace` names it: what the
    packages contribute, in the order they did."""
    written = []
    install(HISTORY, Sink(HISTORY, "terrace-terrace", lambda bucket, record: written.extend(record)))
    yield written
    install(HISTORY, None)


def _terrace(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    broker = Broker()
    return Runtime(boot(WORLD, "terrace"), "terrace", transport=Mqtt(AGENT, broker)), broker


def test_booted_from_its_directory_the_agent_holds_no_hardware():
    """The hardware is onboarding's kind, which the agent's T-Box does not declare, so a boot from
    the world's directory passes over it: not one of its quads, and no row saying it exists. A
    container used to be spared only because the file was left unmounted by its name (#820)."""
    store = boot(WORLD, "terrace")
    hardware = (WORLD / "hardware.ttl").resolve().as_uri()
    held = sum(1 for _ in store.quads_for_pattern(None, None, None, ox.NamedNode(hardware)))
    rowed = sum(1 for _ in store.quads_for_pattern(ox.NamedNode(hardware), None, None))
    assert (held, rowed) == (0, 0), f"the terrace agent holds {held} hardware quads and {rowed} rows about the graph"


def test_the_agent_listens_on_the_boards_one_topic(monkeypatch):
    _, broker = _terrace(monkeypatch)
    assert broker.subscribed == ["sensors/moisture_sensor_terrace/reading"]


def test_one_message_is_five_observations_and_the_soil_is_below_the_beds_range(monkeypatch):
    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    assert runtime.run(passes=2, poll_s=0) == UNFINISHED, "it watches for good"
    beliefs = graphs_of(runtime.beliefs, OREXIS + "BeliefGraph")
    read = {r["p"].rsplit("#", 1)[-1]: float(r["v"]) for r in rows(
        runtime.beliefs, "SELECT ?p ?v WHERE { ?o sosa:madeBySensor ?s ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
        [g for g in beliefs if g in set(graphs_of(runtime.beliefs, STATE)) or g.endswith("/revisions")])}
    assert read == {"SoilMoisture": 0.2, "AirTemperature": 14.5, "AirHumidity": 0.8, "AirPressure": 1012.0,
                    "BatteryVoltage": 3.91}
    below = rows(runtime.beliefs, "SELECT DISTINCT ?o WHERE { ?o sensing:below ?r }", beliefs)
    assert [r["o"].rsplit("#", 1)[-1] for r in below] == ["obs_moisture_sensor_terrace"]
    assert broker.published == [], "nothing is wanted, so nothing is sent"


def test_a_board_that_goes_quiet_is_said_silent_with_nothing_else_arriving(monkeypatch):
    """The terrace's one board reports once and then dies. Nothing arrives after, so no pass has
    a message to take; the passes still ask what has gone missing, and once three cadences are gone
    past a reading's grace — a hundred minutes at twenty a reading (#870) — every sensor of the board
    is said silent (#843). The sentinel takes no orders, so nothing is sent."""
    from datetime import timedelta

    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.run(passes=1, poll_s=0)
    later = NOW + timedelta(minutes=100)
    monkeypatch.setattr(clock, "now", lambda: later)
    runtime.run(passes=1, poll_s=0)
    silent = rows(runtime.beliefs, "SELECT ?s WHERE { ?s sensing:silentSince ?t } ORDER BY ?s", graphs_of(runtime.beliefs, STATE))
    assert [r["s"].rsplit("#", 1)[-1] for r in silent] == [
        "air_humidity_terrace", "air_pressure_terrace", "air_temp_terrace", "battery_sensor_terrace",
        "moisture_sensor_terrace"]
    assert broker.published == []


def test_each_reading_reaches_the_series_under_its_own_property(monkeypatch, history):
    """The five values of one message are five points, each measured under the property it
    observes — the air's temperature is not soil moisture (#822) — and said by sensing as each
    observation is concluded (#825)."""
    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.drain(NOW)
    assert sorted((p["measurement"], p["tags"]["sensor"], p["fields"]["value"]) for p in history) == [
        ("AirHumidity", "air_humidity_terrace", 0.8), ("AirPressure", "air_pressure_terrace", 1012.0),
        ("AirTemperature", "air_temp_terrace", 14.5), ("BatteryVoltage", "battery_sensor_terrace", 3.91),
        ("SoilMoisture", "moisture_sensor_terrace", 0.2)]
    assert {p["tags"].get("plant") for p in history} == {"terrace_bed", "terrace_battery"}
    assert {p["time"] for p in history} == {NOW}, "at the reading's own instant"


def test_an_alarm_is_two_points_in_the_history_and_a_step_not_a_slope(monkeypatch, history):
    """The board's watcher saw the soil leave its window and woke: the alarm's array carries its last
    quiet sample, 25 seconds before, and the reading. Both are observations, both are concluded through the probe's scaling,
    and history draws the earlier at its own instant — a step, where the reading alone would be a
    slope from the last heartbeat."""
    from datetime import timedelta

    runtime, broker = _terrace(monkeypatch)
    alarm = json.dumps({"moisture_raw": [{"value": 710, "age_s": 25}, {"value": 410, "age_s": 0}],
                        "sensor": "moisture_sensor_terrace", "wake": "alarm"}).encode()
    runtime.deliver("sensors/moisture_sensor_terrace/reading", alarm, NOW)
    runtime.drain(NOW)
    soil = sorted((p["time"], p["fields"]["value"]) for p in history if p["measurement"] == "SoilMoisture")
    assert soil == [(NOW - timedelta(seconds=25), 0.2), (NOW, 1.0)]


def test_every_point_the_agent_writes_is_drawn_by_one_terrace_panel(monkeypatch, history):
    """What `orexis-dashboards terrace` generates is held to what the agent writes: each point's
    measurement and sensor are filtered for by exactly one panel, so a panel querying a
    measurement nobody writes, which is what an unshared constant would drift into, fails here."""
    from onboarding.dashboards import render

    runtime, broker = _terrace(monkeypatch)
    runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
    runtime.drain(NOW)
    queries = [t["query"] for panel in render("terrace")["panels"] for t in panel["targets"]]
    drawn = {(p["measurement"], p["tags"]["sensor"]):
             [q for q in queries if f'r._measurement == "{p["measurement"]}"' in q
              and f'r.sensor == "{p["tags"]["sensor"]}"' in q] for p in history}
    assert len(drawn) == 5 and all(len(panels) == 1 for panels in drawn.values()), drawn


def test_every_field_the_agent_writes_is_drawn_by_one_health_panel(monkeypatch):
    """The health dashboards are held to what two passes write, flushed as a stop flushes (#826,
    amended): every field of every point is drawn by exactly one panel of them all — an event's levels
    of a unit together, its count and flags together and each value's mean, max and sum together — and
    every panel reads the bucket of the agent the dashboards' variable picks. A dashboard per package
    that reports, the runtime's first, each a row per measurement and linked to the rest: sensing's
    because the terrace loads it, so its silence and its readings are drawn, and no panel draws a
    measurement nothing writes."""
    from agent.metrics import window as metrics
    from agent.series import METRICS
    from onboarding.dashboards import AGENT_VARIABLE, render_health

    written = []
    install(METRICS, Sink(METRICS, "terrace-terrace-metrics", lambda bucket, record: written.extend(record)))
    try:
        runtime, _ = _terrace(monkeypatch)
        for _ in range(2):
            runtime.deliver("sensors/moisture_sensor_terrace/reading", MESSAGE, NOW)
            runtime.run(passes=1, poll_s=0)
        metrics.flush()
    finally:
        install(METRICS, None)
        metrics.reset()
    health = render_health("terrace")
    files = [name for name, _ in health]
    assert files[0] == "runtime.json" and {"planning.json", "execution.json", "sensing.json", "belief.json"} <= set(files), files
    for name, dashboard in health:
        (variable,) = dashboard["templating"]["list"]
        assert variable["name"] == AGENT_VARIABLE and variable["query"] == "terrace"
        assert dashboard["links"][0]["includeVars"] and "health" in dashboard["links"][0]["tags"]
    (sensing,) = [d for name, d in health if name == "sensing.json"]
    assert [p["title"] for p in sensing["panels"] if p["type"] == "row"] == ["received", "silence"]
    assert len({d["uid"] for _, d in health}) == len(health)
    panels = [p for _, d in health for p in d["panels"] if p["type"] != "row"]
    queries = [[t["query"] for t in p["targets"]] for p in panels]
    assert queries and all('from(bucket: "terrace-${agent}-metrics")' in q for qs in queries for q in qs)
    wanted = {(p["measurement"], f) for p in written for f in p["fields"]}
    assert {("silence", "silent"), ("received", "interval_s_mean"), ("reroot", "count"), ("pass", "plan_s_max")} <= wanted, wanted
    for measurement, field in wanted:
        hits = [i for i, qs in enumerate(queries) if any(
            f'r._measurement == "{measurement}"' in q and (f'r._field == "{field}"' in q or "r._field ==" not in q)
            for q in qs)]
        assert len(hits) == 1, (measurement, field, [panels[i]["title"] for i in hits])
    drawn = {q.split('r._measurement == "')[1].split('"')[0] for qs in queries for q in qs}
    assert {p["measurement"] for p in written} <= drawn


#  WHERE THE TERRACE IS, as its secrets/place.ttl states it — a made-up place, since the real one is
#  not committed — and what the forecast service answers: ten millimetres in the hour to two o'clock.
PLACE = """@prefix : <http://example.org/orexis/world/terrace#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix schema: <https://schema.org/> .
<> a orexis:WorldGraph .
:terrace schema:geo [ schema:latitude 50.12 ; schema:longitude 10.34 ] .
"""
FORECAST = (b'{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00", "2026-01-01T15:00"],'
            b' "precipitation": [0.0, 10.0, 0.0]}}')
FORECAST_SENSOR = "http://example.org/orexis/world/terrace#forecast_terrace"


def _with_a_place(tmp_path):
    """The terrace's documents copied, with the place its secrets/ would hold."""
    import shutil
    world = tmp_path / "world" / "terrace"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "mosquitto", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")         # where its imports resolve
    (world / "secrets").mkdir()
    (world / "secrets" / "place.ttl").write_text(PLACE)
    return world


def test_without_its_place_the_forecast_is_not_asked_for_and_the_terrace_still_boots(monkeypatch, caplog):
    """A clone holds no secrets/: the terrace boots, loads the HTTP member for its forecast, and
    fetches nothing, saying why."""
    from agent.transport.http.driver import Http
    from agent.runtime import HTTP

    monkeypatch.setattr(clock, "now", lambda: NOW)
    store = boot(WORLD, "terrace") if not (WORLD / "secrets" / "place.ttl").exists() else None
    if store is None:
        pytest.skip("this checkout holds the terrace's place")
    runtime = Runtime(store, "terrace", transport=Mqtt(AGENT, Broker()))
    assert HTTP in runtime.packages
    asked = []
    web = Http(AGENT, runtime.deliver, asked.append, spawn=lambda work: work())
    with caplog.at_level("WARNING", logger="http"):
        web.sense_now(store, FORECAST_SENSOR)
    assert asked == [] and "secrets/" in caplog.text


def test_a_forecast_is_fetched_when_due_and_the_soils_next_prediction_carries_its_rain(monkeypatch, tmp_path):
    """THE WHOLE PATH. Started, the HTTP member polls the forecast at once for the terrace's place,
    and the body is a job the runtime hands to sensing, which writes an hour of forecast per graph.
    The soil reads 0.2, under the bed's floor, and its next reading is predicted with the rain:
    below until the shower lifts it back inside the bed's range, which drying alone never would."""
    from agent.transport.http.driver import Http
    from agent.transport.transport import Transports

    monkeypatch.setattr(clock, "now", lambda: NOW)
    world = _with_a_place(tmp_path)
    store = boot(world, "terrace")
    asked = []
    web = Http(AGENT, None, lambda url: asked.append(url) or FORECAST, spawn=lambda work: work())
    runtime = Runtime(store, "terrace", transport=Transports([Mqtt(AGENT, Broker()), web]))
    runtime.deliver((0, "sensors/moisture_sensor_terrace/reading"), MESSAGE, NOW)
    runtime.run(passes=2, poll_s=0)
    assert asked == ["https://api.open-meteo.com/v1/forecast?latitude=50.12&longitude=10.34&hourly=precipitation"
                     "&timezone=GMT&forecast_days=2"]
    hours = rows(store, "SELECT ?v WHERE { ?o sosa:madeBySensor $s ; sosa:hasSimpleResult ?v } ORDER BY ?v",
                 graphs_of(store, "http://example.org/orexis/sensing#ForecastGraph"), s=FORECAST_SENSOR)
    assert sorted(float(r["v"]) for r in hours) == [0.0, 0.0, 10.0]
    runtime.deliver((0, "sensors/moisture_sensor_terrace/reading"), MESSAGE, NOW)
    runtime.run(passes=1, poll_s=0)
    predicted = [float(r["v"]) for r in rows(
        store, "SELECT ?v ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PredictionGraph ; "
               "dcterms:temporal/orexis:start ?s } GRAPH ?g { ?o sosa:observedProperty <http://example.org/orexis/climate#SoilMoisture> ; "
               "sosa:hasSimpleResult ?v } } ORDER BY ?s", (),)]
    assert predicted[0] < 0.25 and any(0.25 <= v <= 0.60 for v in predicted[1:]), predicted
