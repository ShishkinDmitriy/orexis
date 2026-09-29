"""Sensing's part: once started it asks every minute of the timeline what has fallen due, whether
or not anything arrived, and reports its gauge."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agent import clock
from agent.sensing.missed import SILENT_AFTER
from agent.sensing.received import received
from agent.sensing.create import EVERY_S, create
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
PROBE = "http://example.org/test#probe"


def test_its_part_asks_after_silence_every_minute_and_reports_its_gauge(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW + timedelta(seconds=900 * (1 + SILENT_AFTER)))
    create(runtime).start(runtime)
    [(seconds, ask)] = runtime.timers
    assert seconds == EVERY_S and len(runtime.gauges) == 1
    assert ask() == []
    said = rows(store, "SELECT ?s WHERE { GRAPH ?g { ?s sensing:silentSince ?t } }", ())
    assert [r["s"] for r in said] == [PROBE], "the probe, silent past its limit, is said so"
