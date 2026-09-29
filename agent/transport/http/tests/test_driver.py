"""The HTTP driver over a balcony and its weather service, with a stand-in client: which sensors are
its, where one is read, how a nudge becomes one fetch and the body becomes forecast graphs through
sensing — and what it does when the location is not there or the service does not answer."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import clock
from agent.transport.http import driver
from agent.transport.http.driver import Http, fill

WORLD = Path(__file__).parent / "worlds" / "a_forecast_for_a_balcony.trig"
TEST = "http://example.org/test#"
WEATHER, PROBE = TEST + "weather", TEST + "probe"
BODY = (b'{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00"], "precipitation": [0.4, 1.5]}}')


@pytest.fixture
def web(monkeypatch, snapshots):
    """The member over the balcony: a client recording what it was asked, answering `BODY`; a spawn
    that runs the fetch at once; and a deliver that queues, as the container's does."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    asked, queued = [], []

    def client(url):
        asked.append(url)
        return BODY

    member = Http(TEST + "keeper", lambda *message: queued.append(message), client, spawn=lambda work: work())
    return snapshots.stand_in(WORLD), member, asked, queued


def test_the_members_sensors_are_the_agents_things_with_a_form(web):
    store, member, _, _ = web
    assert member.open(store) == [WEATHER]
    assert member.reaches(store, WEATHER) and not member.reaches(store, PROBE)


def test_a_nudge_fetches_the_target_filled_from_the_place_and_the_body_becomes_forecast(web, snapshots):
    store, member, asked, queued = web
    member.sense_now(store, WEATHER)
    assert asked == ["https://forecast.example/v1?latitude=52.52&longitude=13.4&hourly=precipitation"]
    [(channel, body, at)] = queued
    written = member.handle(store, channel, body, at)
    assert [sensor for sensor, _ in written] == [WEATHER, WEATHER], "one graph per hour still ahead"


def test_a_sensor_is_fetched_once_and_not_again_within_the_retry(web, monkeypatch):
    store, member, asked, _ = web
    member.sense_now(store, WEATHER)
    member.sense_now(store, WEATHER)
    assert len(asked) == 1
    real = driver.time.monotonic
    monkeypatch.setattr(driver.time, "monotonic", lambda: real() + driver.RETRY_S + 1)
    member.sense_now(store, WEATHER)
    assert len(asked) == 2


def test_with_no_location_nothing_is_fetched_and_it_says_so(web, caplog):
    store, member, asked, _ = web
    store.update("PREFIX schema: <https://schema.org/> PREFIX : <http://example.org/test#> "
                 "DELETE WHERE { GRAPH :world { :balcony schema:geo ?g } }")
    with caplog.at_level("WARNING", logger="http"):
        member.sense_now(store, WEATHER)
    assert asked == [] and "secrets/" in caplog.text


def test_a_service_that_does_not_answer_is_said_and_delivers_nothing(web, caplog):
    store, member, _, queued = web

    def down(url):
        raise OSError("connection refused")

    member.client = down
    with caplog.at_level("WARNING", logger="http"):
        member.sense_now(store, WEATHER)
    assert queued == [] and "would not answer" in caplog.text


def test_a_template_is_filled_by_name_and_refused_where_a_name_is_missing():
    assert fill("https://x/?a={a}&b={b}", {"a": "1", "b": "two words"}) == "https://x/?a=1&b=two%20words"
    assert fill("https://x/?a={a}", {}) is None
