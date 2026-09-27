"""Tower of Hanoi in the 0.2.0 runtime: the world boots from the files beside this test, the
mover plans and takes its own moves, and the runtime stops when every disk is home."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import clock
from agent.ontology import STATE

WANT = "http://example.org/orexis/planning#WantGraph"   # planning's word; the Planner is all planning exports
from agent.runtime import MET, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

_HOME_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"


def _home(store) -> int:
    return int(rows(store, _HOME_Q, ())[0]["n"])


def _acts(runtime) -> int:
    return int(rows(runtime.executor.intentions, _ACTS_Q, ())[0]["n"])


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "hanoi")
    assert len(graphs_of(beliefs, WANT)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _home(beliefs) == 0, "three disks on peg A"
    (scopes,) = rows(beliefs, "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a planning:Scope } }", ())
    assert int(scopes["n"]) >= 1, "scope_actions ran at boot"


def test_the_mover_loads_the_mind_and_nothing_else():
    """No sensor, no drift, no topic, no saying: no premise holds, so neither sensing's ontology nor
    its three rules, nor prediction's ontology, nor the MQTT transport's is in the store (#824);
    that none of their modules is imported either is asked of a whole process, in
    agent/tests/test_premises.py."""
    import pyoxigraph as ox

    from agent.runtime import MIND, packages_of

    beliefs = boot(WORLD, "hanoi")
    assert packages_of(beliefs, "http://example.org/orexis/world/hanoi#hanoi") == MIND
    agent = WORLD.parents[1] / "agent"
    absent = [agent / "sensing" / "ontology.ttl", agent / "sensing" / "rules.ttl",
              agent / "prediction" / "ontology.ttl", agent / "transport" / "mqtt" / "ontology.ttl"]
    present = [agent / "ontology.ttl", agent / "planning" / "ontology.ttl"]
    assert all(p.exists() for p in absent + present), "a document this test names has moved"
    held = {p: bool(list(beliefs.quads_for_pattern(ox.NamedNode(p.as_uri()), None, None))) for p in absent + present}
    assert not any(held[p] for p in absent), [p.name for p in absent if held[p]]
    assert all(held[p] for p in present), "the probe sees a document the mover does read"


def test_the_tower_is_solved_in_seven_moves_and_the_runtime_stops(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=64)
    assert runtime.run() == MET
    assert _acts(runtime) == 7 and _home(runtime.beliefs) == 3
    assert runtime.run() == MET and _acts(runtime) == 7, "met stays met, and nothing moves again"


def test_a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after(monkeypatch):
    """Twenty candidates a pass: two passes hand nothing down, the third hands the plan, and
    the passes together are the one-shot search. The clock TICKS here, as a running agent's
    does — a pass at the same instant as the last re-lays the present under the last one's
    name and the search would start over."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
    assert runtime.run(passes=12) == MET
    assert _acts(runtime) == 7


def test_each_pass_writes_the_minds_metrics_and_the_runtimes_own(monkeypatch):
    """What the metrics store is handed, pass by pass, at twenty candidates a pass (#826). The mind's
    packages count what they wrote — the first pass's search cut short, `exhausted`, with the cone
    it left: twenty worlds, twenty-one weighings, three still on the frontier; the last pass's
    intention done after seven acts — and the runtime adds its own three. Sensing is not loaded, so
    no silence is counted: a package's metrics are where the package is."""
    runtime, passes, events, _ = _metered(monkeypatch)
    first, last = passes[0], passes[-1]
    assert set(first) == {"pass", "phases", "plans", "cone", "intentions", "acts", "revisions"}
    assert first["plans"] == {"satisfied": 0, "exhausted": 1, "noCandidate": 0}
    assert first["cone"] == {"worlds": 20, "weighings": 21, "open": 3, "met": 0}
    assert first["intentions"]["standing"] == 0 and first["acts"] == {"taken": 0, "notTaken": 0}
    assert last["intentions"] == {"standing": 0, "done": 1, "failed": 0, "superseded": 0, "abandoned": 0}
    assert last["acts"] == {"taken": 7, "notTaken": 0}
    assert set(last["pass"]) == {"duration_s", "quads", "uptime_s"} and last["pass"]["quads"] == len(runtime.beliefs)
    assert all(p["pass"]["duration_s"] > 0 for p in passes) and len(passes) >= 3
    assert all(sum(p["phases"].values()) <= p["pass"]["duration_s"] for p in passes), "the parts are of the pass"


def _metered(monkeypatch):
    """Three disks at twenty candidates a pass, with a metrics sink loaded and who speaks said as
    `main` says it: the runtime, each pass's gauges as {measurement: fields}, and every event."""
    from agent import metrics
    from agent.runtime import world_name
    from agent.series import METRICS, Sink, install

    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    writes = []
    install(METRICS, Sink(METRICS, "hanoi-hanoi-metrics", lambda bucket, record: writes.append(list(record))))
    metrics.identify(world=world_name(WORLD), agent="hanoi")
    try:
        runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
        assert runtime.run(passes=12) == MET
    finally:
        install(METRICS, None)
        metrics.identify()
    gauges = [w for w in writes if any(p["measurement"] == "pass" for p in w)]
    return (runtime, [{p["measurement"]: p["fields"] for p in w} for w in gauges],
            [p for w in writes if w not in gauges for p in w], [p for w in writes for p in w])


def test_each_search_and_the_adoption_are_said_as_they_happen_tagged_and_never_by_the_want(monkeypatch):
    """The events of the same run (#826): a search a pass, each weighing its twenty candidates until
    the third finds the seven moves; one adoption, after three passes of searching, whose plan cost
    what the estimate at the ground said or more; a reroot and a planner pass each pass. Every point
    is tagged with the world and the agent, and the want — minted per instance — is a field, never
    a tag. Hanoi's want is authored, so no desire tags it."""
    runtime, passes, events, points = _metered(monkeypatch)
    by = {}
    for e in events:
        by.setdefault(e["measurement"], []).append(e)
    searches, (adopted,) = by["search"], by["adopted"]
    assert [s["tags"]["outcome"] for s in searches] == ["Exhausted", "Exhausted", "Satisfied"]
    assert [s["fields"]["weighed"] for s in searches[:2]] == [20, 20] and all(s["fields"]["budget"] == 20 for s in searches)
    assert {s["fields"]["want"] for s in searches} == {adopted["fields"]["want"]} == {"every_disk_home"}
    assert adopted["fields"]["passes"] == 3 and adopted["fields"]["replan"] == 0
    assert adopted["fields"]["cost"] == 7 and 0 <= adopted["fields"]["estimate"] <= adopted["fields"]["cost"]
    assert adopted["fields"]["wall_s"] >= sum(s["fields"]["duration_s"] for s in searches) > 0
    assert len(by["reroot"]) == len(by["planner"]) == len(passes)
    assert "desire" not in adopted["tags"], "an authored want was derived under no desire"
    for p in points:                                       # the gauges as well as the events
        assert p["tags"]["world"] == "hanoi" and p["tags"]["agent"] == "hanoi", p
        assert "every_disk_home" not in p["tags"].values() and "want" not in p["tags"], p
    #  COST: an event per search and per pass, never one per weighing — sixty-odd weighings, a
    #  handful of points.
    assert len(events) < sum(s["fields"]["weighed"] for s in searches)


def test_a_lived_in_volume_keeps_the_agents_state_and_reloads_the_worlds(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    beliefs = boot(WORLD, "hanoi")
    Runtime(beliefs, "hanoi", budget=64).run()
    boot(WORLD, "hanoi", beliefs)                     # a restart on the same volume
    assert _home(beliefs) == 3, "the solved tower is the agent's belief, not the file's"
    assert len(graphs_of(beliefs, STATE)) == 1
    assert graphs_of(beliefs, WANT) == [], "the want was reached and withdrawn, and a restart does not bring it back"
