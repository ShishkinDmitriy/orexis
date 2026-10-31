"""The account an agent gives of itself: each loaded package's `account.rq` asked over the graphs it says it reads,
a line per row under its title, values as a person reads them — and nothing of a package the agent does not load."""

from __future__ import annotations

from pathlib import Path

from agent.translation.account import account

WORLD = Path(__file__).parent / "worlds" / "two_readings_and_an_intention.trig"
ME = "http://example.org/test#keeper"


def test_an_account_is_each_loaded_packages_rows_under_its_title(snapshots):
    store = snapshots.stand_in(WORLD)
    told = account([store], ["belief", "sensing", "execution"], ME, snapshots.NOW)
    assert told.split("\n") == [
        "keeper at 2026-01-01 12:00 UTC",
        "observes:",
        " - observed: SoilMoisture, of: bed, reading: 0.2, sensor: probe, at: 2026-01-01 12:00 UTC",
        " - reading: 14.5, sensor: thermo, at: 2026-01-01 11:59 UTC",
        "does:",
        " - pursues: water_the_bed, since: 2026-01-01 11:00 UTC, at: dose",
    ], "the latest percept of each sensor, the intention standing, and no package that ships no select"


def test_a_package_the_agent_does_not_load_says_nothing_and_nothing_said_is_said_so(snapshots):
    store = snapshots.stand_in(WORLD)
    assert account([store, None], ["execution"], ME, snapshots.NOW).split("\n")[1:] == [
        "does:", " - pursues: water_the_bed, since: 2026-01-01 11:00 UTC, at: dose"]
    assert account([store], ["belief"], ME, snapshots.NOW) == "keeper at 2026-01-01 12:00 UTC\nnothing to say yet"
