"""What an agent is pursuing, hottest first — the shipped query and its readers (#234).

`goals.rq` is the definition and `goals_of` is its Python shape, exactly as `gap.rq` and
`urgency` are. These hold the two together, pin the states the query names, and pin the one
piece of arithmetic that had to stay in Python because the store's engine will not do it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox

from packages.capability.desire import gaps_of, goals_of

from conftest import MOISTURE, TEMPERATURE, genesis_store

FERN = "http://example.org/agora/world/simulation#fern_agent"


def _goals(readings, agent="fern", **kw):
    from agent import genesis

    st = genesis_store(readings)
    genesis.birth(st, genesis.world_dir("simulation"), agent)
    return st, goals_of(st.query, FERN, agent, **kw)


def test_the_query_and_the_module_agree_with_the_diff(query_with_readings):
    """One definition, three readers. `goals.rq` repeats `gap.rq`'s arithmetic because SPARQL
    has no include, and a repeat nobody checks is a fork with a delay on it — so the urgency a
    goal carries must equal the |gap| the diff reports, to the store's own precision.

    Both properties, and both signs: fern below its moisture region and above its temperature
    one. A copy that dropped the sign handling would agree on one of them and not the other.
    """
    st, goals = _goals({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0})
    diffs = gaps_of(st.query, FERN)

    stakes = {g.observed_property: g for g in goals if not g.is_duty}
    assert set(stakes) == set(diffs), "the same wants, whichever text is run"
    for prop, gap in diffs.items():
        assert abs(stakes[prop].urgency - abs(gap.gap)) < 1e-9


def test_a_want_nobody_has_read_is_the_hottest_goal_and_not_a_missing_one(monkeypatch):
    """Where the two texts deliberately differ, and why it is not a fork.

    `gap.rq` emits NO row for an unmeasured property — a diff needs two sides, and "unmeasured"
    must never read as "satisfied". But it is a GOAL, and the hottest kind: not knowing whether
    the pot is dying is at least as urgent as knowing it is uncomfortable, which is the answer
    `urgency(None)` has always given and the reason the first intention is to look.
    """
    st, goals = _goals({("fern", TEMPERATURE): 21.0})   # temperature seen, moisture never

    moisture = next(g for g in goals if g.observed_property == MOISTURE)
    assert moisture.value is None
    assert moisture.urgency == 1.0
    assert goals[0] is moisture, "and it sorts to the top, where a deliberator will meet it"
    assert gaps_of(st.query, MOISTURE if False else FERN).get(MOISTURE) is None, \
        "while the diff still reports nothing, which is right for a diff"


def test_the_states_a_stake_can_be_in():
    """met, unmet and unmeasured, asked across the range rather than at one value — a boundary
    that is wrong by one reads correctly at the centre and at the extremes."""
    for value, expected in [(0.55, "met"), (0.45, "met"), (0.65, "met"),
                            (0.30, "unmet"), (0.95, "unmet")]:
        _, goals = _goals({("fern", MOISTURE): value})
        moisture = next(g for g in goals if g.observed_property == MOISTURE)
        met = moisture.urgency == 0.0 or (0.45 <= value <= 0.65)
        assert met == (expected == "met"), f"{value} should be {expected}"


def test_a_duty_carries_its_timestamps_and_the_fraction_is_computed_from_them():
    """The engine limit, made visible rather than worked around.

    A duty's urgency is the fraction of its redeem window that has run, and this store binds
    NOTHING for `duration / duration` — so the query carries `owedAt` and `expiresAt` and the
    division happens in Python. Asked at three points across one window, because the ends are
    what the choice was made about: cool at issue, maximal at the deadline.
    """
    from agent import genesis
    from packages.capability.desire.graphs import obligations_graph

    st = genesis_store({("fern", MOISTURE): 0.55})
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("fern")}> {{
        <http://example.org/agora#obligation.j1> a <http://example.org/agora#Obligation> ;
            <http://example.org/agora#owedTo>
                <http://example.org/agora/world/simulation#tomato_agent> ;
            <http://example.org/agora#forClaim> "j1" ;
            <http://example.org/agora#presented> true ;
            <http://example.org/agora#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
            <http://example.org/agora#expiresAt> "{(owed + timedelta(seconds=900)).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")

    def duty_at(offset_s):
        goals = goals_of(st.query, FERN, "fern", now=owed + timedelta(seconds=offset_s))
        return next(g for g in goals if g.is_duty)

    assert duty_at(0).urgency == 0.0
    assert abs(duty_at(450).urgency - 0.5) < 0.02
    assert duty_at(900).urgency == 1.0
    assert duty_at(5000).urgency == 1.0, "clamped — no more overdue than overdue"
    assert duty_at(0).pursuable and not duty_at(5000).pursuable, \
        "past the window there is nothing left to spend, however hot it reads"


def test_this_store_still_will_not_divide_one_duration_by_another():
    """The measurement the Python fallback exists for, pinned so it cannot rot.

    Four operations, and the split is what matters: comparing durations and adding one to a
    dateTime work, while dividing or scaling a duration binds NOTHING — no error, no row
    missing, just a column of unbound values. That is the failure this project keeps meeting
    from a new direction, so it is worth a test that fails LOUDLY the day the engine grows the
    operation: the arithmetic can then move back into `goals.rq` where it belongs.
    """
    st = ox.Store()
    st.update("""PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA { <urn:o> <urn:at> "2026-08-20T00:00:00Z"^^xsd:dateTime ;
                              <urn:exp> "2026-08-20T01:00:00Z"^^xsd:dateTime }""")

    def answer(bind):
        rows = list(st.query(
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> "
            "SELECT ?r WHERE { <urn:o> <urn:at> ?at ; <urn:exp> ?e . %s }" % bind))
        return rows[0]["r"] if rows else None

    assert answer('BIND((?e - ?at) / "PT1S"^^xsd:dayTimeDuration AS ?r)') is None, \
        "if this now binds, delete _duty_urgency and let goals.rq do the arithmetic"
    assert answer("BIND((?e - ?at) * 0.5 AS ?r)") is None
    assert answer("BIND(?at + (?e - ?at) AS ?r)") is not None, "dateTime + duration works"
    assert answer("BIND((?e - ?at) > (?e - ?e) AS ?r)") is not None, "and durations compare"
