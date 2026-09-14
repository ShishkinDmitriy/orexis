"""The reviser wakes the mind on a surprise, not on a reading (#632) — item 2 of
a-prediction-is-a-set-of-bands-that-widens-with-the-horizon, held to the code.

A reading that lands inside the bands the expected next observation said it may be in is the
world going on as believed: absorbed, no mark. One outside them is an exogenous surprise,
caught at arrival: marked, and the pass it wakes names it. With no prediction standing for
the key, a reading marks as any change did before there were expectations.
"""
from __future__ import annotations

from orexis_agent_progression.ontology import DELIBERATION_GRAPH
from orexis_agent_progression.store import bindings
from orexis_capability_sensing import predictions
from conftest import MOISTURE, build_agent, genesis_store, sensing_of, stake_of, write_reading

PROBE = "http://example.org/orexis/world/loner#moisture_probe"
WORLD = "http://example.org/orexis/graph/world"


def _gardener(monkeypatch, moisture: float = 0.12, noise: float | None = None):
    """The loner's gardener, its pot at `moisture` inside [0.10, ...]; `noise` on its probe
    widens what the next observation may be (#642)."""
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    if noise is not None:
        st.update(f"""INSERT DATA {{ GRAPH <{WORLD}> {{ <{PROBE}> sensing:noise {noise} }} }}""")
    return build_agent("gardener", st, monkeypatch)


def _marks(agent) -> dict:
    return dict(agent.reviser._pending)


def test_ten_readings_inside_the_expectation_leave_no_mark_and_one_outside_leaves_one(monkeypatch):
    """Absorbed, ten times; then a surprise, once — and the pass it wakes says what
    contradicted what, as `deliberation:surprise` on the trace."""
    agent = _gardener(monkeypatch, moisture=0.12)
    assert _marks(agent) == {}
    for i in range(10):
        write_reading(agent, 0.12 + i * 0.001, MOISTURE)
    assert _marks(agent) == {}, "the world going on as believed wakes nothing"
    write_reading(agent, 0.05, MOISTURE)
    marks = _marks(agent)
    assert list(marks) == [stake_of(agent).uri]
    _, surprise = marks[stake_of(agent).uri]
    assert surprise is not None and surprise[0] == "exogenous" and "BelowRegion" in surprise[1]
    agent.reviser.settle()
    rows = bindings(agent.beliefs.query(f"""
SELECT ?s WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?d deliberation:surprise ?s }} }}"""))
    assert rows and any("exogenous" in r["s"] and "BelowRegion" in r["s"] for r in rows), rows


def test_a_reading_that_crosses_a_boundary_inside_the_expected_set_does_not_wake_the_mind(monkeypatch):
    """The hysteresis #615 asked for, without a margin: a pot near its floor, whose probe is
    noisy, is expected inside OR below — so a reading that crosses to below is no surprise,
    and one the set does not reach is."""
    agent = _gardener(monkeypatch, moisture=0.115, noise=0.03)
    write_reading(agent, 0.095, MOISTURE)                 # crossed the floor, inside the set
    assert _marks(agent) == {}, "a boundary crossed inside the expected set wakes nothing"
    high = sensing_of(agent).regions[MOISTURE].high
    write_reading(agent, high + 0.05, MOISTURE)           # above: no prediction reached it
    assert list(_marks(agent)) == [stake_of(agent).uri]


def test_a_reading_nobody_expected_anything_of_marks_as_any_change_did(monkeypatch):
    """A world with no expectation standing behaves exactly as before there were any: the
    reading is marked, and the mark names no surprise."""
    agent = _gardener(monkeypatch, moisture=0.12)
    predictions.drop(agent.beliefs, predictions.graphs_of(agent.beliefs, agent.id, "zz", MOISTURE))
    write_reading(agent, 0.121, MOISTURE)
    marks = _marks(agent)
    assert list(marks) == [stake_of(agent).uri] and marks[stake_of(agent).uri][1] is None
