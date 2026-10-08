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

#  THE DISKS HOME, read off the state by kind: a published plan's steps state the same rows in the
#  graphs they predict in, and a prediction of a disk on C is not a disk on C.
_HOME_Q = """PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:StateGraph }
  GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"


def _home(store) -> int:
    return int(rows(store, _HOME_Q, ())[0]["n"])


def _acts(runtime) -> int:
    return int(rows(runtime.parts["execution"].executor.intentions, _ACTS_Q, ())[0]["n"])


def test_the_boot_says_what_each_graph_is():
    beliefs = boot(WORLD, "hanoi")
    assert len(graphs_of(beliefs, WANT)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _home(beliefs) == 0, "three disks on peg A"
    (scopes,) = rows(beliefs, "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a planning:Scope } }", ())
    assert int(scopes["n"]) >= 1, "scope_actions ran at boot"


def test_the_mover_loads_what_its_roles_call_for_and_nothing_else():
    """Declared a planner and an executor in its self graph, and nothing else — its world ships no
    rules, so it is no deliberator: neither belief's ontology, nor sensing's and its three rules, nor
    prediction's, nor speech's, nor the MQTT transport's is in the store (#824, #927); that none of
    their parts is imported either is asked of a whole process, in agent/tests/test_roles.py."""
    import pyoxigraph as ox

    from agent.runtime import packages_of

    beliefs = boot(WORLD, "hanoi")
    assert packages_of(beliefs) == ("planning", "execution")
    agent = WORLD.parents[1] / "agent"
    absent = [agent / "belief" / "ontology.ttl", agent / "sensing" / "ontology.ttl", agent / "sensing" / "rules.ttl",
              agent / "prediction" / "ontology.ttl", agent / "speech" / "ontology.ttl",
              agent / "transport" / "mqtt" / "ontology.ttl"]
    present = [agent / "ontology.ttl", agent / "planning" / "ontology.ttl", agent / "execution" / "ontology.ttl"]
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


def test_a_window_a_pass_writes_the_planners_and_executors_levels_and_the_runtimes_own(monkeypatch):
    """The levels, each as it last stood in a window, and here a window a pass (#826, amended). The
    packages its two roles load say what they hold — the first pass's search cut short, `exhausted`, with the cone
    it left in the imaginarium: twenty worlds, twenty-one weighings, three still on the frontier; no
    intention standing yet — and across the run seven acts taken and one intention done; the runtime
    adds its own, the store's size and the uptime on its pass. Neither sensing nor belief is loaded,
    so no silence and no revisions are said: a package's metrics are where the package is."""
    runtime, windows = _metered(monkeypatch, interval_s=0)
    first = {p["measurement"]: p for p in windows[0]}
    assert {"pass", "planner", "imaginarium", "search", "reroot", "intentions"} <= set(first), sorted(first)
    assert "silence" not in first and "revisions" not in first
    assert first["imaginarium"]["fields"] == {"worlds": 20, "weighings": 21, "open": 3, "met": 0,
                                              "satisfied": 0, "exhausted": 1, "no_candidate": 0}
    assert first["imaginarium"]["tags"]["scope"] and first["intentions"]["fields"] == {"standing": 0}
    every = [p for w in windows for p in w]
    acts = [p["fields"] for p in every if p["measurement"] == "act"]
    assert sum(a["count"] for a in acts) == sum(a["taken"] for a in acts) == 7
    ended = [p for p in every if p["measurement"] == "intention"]
    assert [(p["tags"]["outcome"], p["fields"]["count"]) for p in ended] == [("done", 1)]
    passes = [p["fields"] for p in every if p["measurement"] == "pass"]
    assert len(passes) >= 3 and all(p["count"] == 1 and p["duration_s_max"] > 0 for p in passes)
    assert all(0 < p["quads"] and p["uptime_s"] > 0 for p in passes)
    phases = [k for k in passes[0] if k.endswith("_s_sum") and k != "duration_s_sum"]
    assert phases and all(sum(p.get(k, 0) for k in phases) <= p["duration_s_sum"] for p in passes), \
        "the parts are of the pass"


def _metered(monkeypatch, *, interval_s: float):
    """Three disks at twenty candidates a pass, with a metrics sink loaded and who speaks said as
    `main` says it, the window `interval_s` long — nought writes one a pass, and anything longer
    than the run writes one at the end, as a stop does: the runtime, and every window written."""
    from agent.metrics import window as metrics
    from agent.runtime import world_name
    from agent.series import METRICS, Sink, install

    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    writes = []
    install(METRICS, Sink(METRICS, "hanoi-hanoi-metrics", lambda bucket, record: writes.append(list(record))))
    metrics.configure(interval_s=interval_s)
    metrics.identify(world=world_name(WORLD), agent="hanoi")
    try:
        runtime = Runtime(boot(WORLD, "hanoi"), "hanoi", budget=20)
        assert runtime.run(passes=12) == MET
        runtime.stop()                                   # as a stop does: the last window written
    finally:
        install(METRICS, None)
        metrics.reset()
        metrics.identify()
    return runtime, [w for w in writes if w]


def test_every_search_and_the_adoption_are_tallied_into_one_window_and_never_by_the_want(monkeypatch):
    """The events of the same run, in the one window a stop writes (#826, amended): two searches that
    each weighed their twenty candidates and gave up, and a third that found the seven moves, kept
    apart by how they ended; one adoption, after three passes of searching, whose plan cost what the
    estimate at the ground said or more; a reroot and a planner pass each pass. Every point is tagged
    with the world and the agent, and the want — minted per instance — is on none of them. Hanoi's
    want is authored, so no desire tags it."""
    runtime, (window,) = _metered(monkeypatch, interval_s=3600)
    by = {}
    for p in window:
        by.setdefault(p["measurement"], []).append(p)
    searches = {s["tags"]["outcome"]: s["fields"] for s in by["search"]}
    (adopted,) = by["published"]
    assert searches["Exhausted"]["count"] == 2 and searches["Exhausted"]["weighed_sum"] == 40.0
    assert searches["Satisfied"]["count"] == 1 and searches["Exhausted"]["budget_max"] == 20.0
    fields = adopted["fields"]
    assert fields["count"] == 1 and fields["passes_max"] == 3.0 and fields["replan"] == 0
    assert fields["cost_max"] == 7.0 and 0 <= fields["estimate_max"] <= fields["cost_max"]
    assert fields["wall_s_max"] >= sum(s["duration_s_sum"] for s in searches.values()) > 0
    (passed,) = by["pass"]
    assert passed["fields"]["count"] >= 3
    assert sum(p["fields"]["count"] for p in by["reroot"]) == by["planner"][0]["fields"]["count"] == passed["fields"]["count"]
    assert "desire" not in adopted["tags"], "an authored want was derived under no desire"
    for p in window:                                       # the levels as well as the counts
        assert p["tags"]["world"] == "hanoi" and p["tags"]["agent"] == "hanoi", p
        assert "every_disk_home" not in {*p["tags"].values(), *map(str, p["fields"].values())}, p
        assert "want" not in p["tags"] and "want" not in p["fields"], p
    #  COST: a point per measurement and tag set a window, never one per weighing or per pass.
    assert len(window) < 20


def test_a_lived_in_volume_keeps_the_agents_state_and_reloads_the_worlds(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    beliefs = boot(WORLD, "hanoi")
    Runtime(beliefs, "hanoi", budget=64).run()
    boot(WORLD, "hanoi", beliefs)                     # a restart on the same volume
    assert _home(beliefs) == 3, "the solved tower is the agent's belief, not the file's"
    assert len(graphs_of(beliefs, STATE)) == 1
    assert graphs_of(beliefs, WANT) == [], "the want was reached and withdrawn, and a restart does not bring it back"
