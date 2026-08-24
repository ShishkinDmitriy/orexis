"""What an agent is pursuing, hottest first — the split pair and its one join (#234, #298).

`desires.rq` asks the desire modality, `readings.rq` asks the belief modality, and `desires_of`
is the join — the arithmetic lives once, in `Region` and `_duty_urgency`. These pin the
states, the ranking, and the duty fraction that was always Python's because the store's
engine will not divide durations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox

from agent.regions import gaps_of, desires_of

from conftest import MOISTURE, TEMPERATURE, desires_build, genesis_store

FERN = "http://example.org/orexis/world/simulation#fern_agent"


def _desires(readings, agent="fern", **kw):
    from agent import genesis

    st = genesis_store(readings)
    genesis.birth(st, genesis.world_dir("simulation"), agent)
    return st, desires_of(desires_build(st, agent).query_union, st.query, FERN, agent, **kw)


def test_the_query_and_the_module_agree_with_the_diff(query_with_readings):
    """One definition, three readers. `desires.rq` repeats `gap.rq`'s arithmetic because SPARQL
    has no include, and a repeat nobody checks is a fork with a delay on it — so the urgency a
    desire carries must equal the |gap| the diff reports, to the store's own precision.

    Both properties, and both signs: fern below its moisture region and above its temperature
    one. A copy that dropped the sign handling would agree on one of them and not the other.
    """
    st, desires = _desires({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0})
    diffs = gaps_of(desires_build(st, "fern").query_union, st.query, FERN, "fern")

    stakes = {g.observed_property: g for g in desires if not g.is_duty}
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
    st, desires = _desires({("fern", TEMPERATURE): 21.0})   # temperature seen, moisture never

    moisture = next(g for g in desires if g.observed_property == MOISTURE)
    assert moisture.value is None
    assert moisture.urgency == 1.0
    assert desires[0] is moisture, "and it sorts to the top, where a deliberator will meet it"
    assert gaps_of(desires_build(st, "fern").query_union, st.query,
                   FERN, "fern").get(MOISTURE) is None, \
        "while the diff still reports nothing, which is right for a diff"


def test_the_states_a_stake_can_be_in():
    """met, unmet and unmeasured, asked across the range rather than at one value — a boundary
    that is wrong by one reads correctly at the centre and at the extremes."""
    for value, expected in [(0.55, "met"), (0.45, "met"), (0.65, "met"),
                            (0.30, "unmet"), (0.95, "unmet")]:
        _, desires = _desires({("fern", MOISTURE): value})
        moisture = next(g for g in desires if g.observed_property == MOISTURE)
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
    from agent.ontology import obligations_graph

    st = genesis_store({("fern", MOISTURE): 0.55})
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("fern")}> {{
        <http://example.org/orexis#obligation.j1> a <http://example.org/orexis#Obligation> ;
            <http://example.org/orexis#owedTo>
                <http://example.org/orexis/world/simulation#tomato_agent> ;
            <http://example.org/orexis#forClaim> "j1" ;
            <http://example.org/orexis#presented> true ;
            <http://example.org/orexis#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
            <http://example.org/orexis#expiresAt> "{(owed + timedelta(seconds=900)).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")

    def duty_at(offset_s):
        desires = desires_of(desires_build(st, "fern").query_union, st.query, FERN, "fern",
                             now=owed + timedelta(seconds=offset_s))
        return next(g for g in desires if g.is_duty)

    assert duty_at(0).urgency == 0.0
    assert abs(duty_at(450).urgency - 0.5) < 0.02
    assert duty_at(900).urgency == 1.0
    assert duty_at(5000).urgency == 1.0, "clamped — no more overdue than overdue"
    assert duty_at(0).pursuable and not duty_at(5000).pursuable, \
        "past the window there is nothing left to spend, however hot it reads"


def test_a_stakes_urgency_is_measured_from_the_aim_and_follows_a_repick_without_a_rebuild():
    """The finding a-desire-states-its-own-measure records, pinned from the ranking side.

    The reflex steered toward the AIM while urgency was measured from the region's CENTRE, so
    the two mechanisms pursued different targets whenever the pick sat off-centre. The desire's
    declared measure reads the pick out of the belief base AT QUERY TIME — so moving the aim
    moves the urgency with no desires rebuild, which is what a review's re-pick needs, and the
    scaling stays asymmetric: the room below the aim is aim-to-floor, above it aim-to-ceiling,
    so the same 0.10 out reads differently per side. Fern: region 0.45-0.65, survives 0.2-0.85.
    """
    from agent.ontology import beliefs_graph

    st = genesis_store({("fern", MOISTURE): 0.55})
    wants = desires_build(st, "fern")

    def urgency():
        desires = desires_of(wants.query_union, st.query, FERN, "fern")
        return next(g for g in desires if g.observed_property == MOISTURE).urgency

    assert urgency() == 0.0, "at the pick (0.55, which is also the centre) nothing is urgent"

    #  The re-pick: the aim moves in the BELIEF BASE alone — the desires store is deliberately
    #  not rebuilt, because the claim under test is that the measure asks, not that a rebuild
    #  recompiles.
    st.update(f"""DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim <https://schema.org/value> ?v }} }}
                  INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim <https://schema.org/value> 0.65 }} }}
                  WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{
                      <{FERN}> <http://example.org/orexis#aims> ?aim .
                      ?aim <http://www.w3.org/ns/ssn/forProperty> <{MOISTURE}> ;
                           <https://schema.org/value> ?v }} }}""")
    #  0.55 against an aim of 0.65: distance 0.10, and the room on the LOW side is
    #  aim - floor = 0.65 - 0.20 = 0.45. Met (inside the region) and still urgent — the
    #  situation the old centre-anchored number could not express.
    assert abs(urgency() - 0.10 / 0.45) < 1e-9, \
        "the urgency must follow the pick the moment the pick moves"

    #  And the other side scales by the other room: reading 0.75 sits ABOVE the 0.65 aim,
    #  distance 0.10 again, but the room is ceiling - aim = 0.85 - 0.65 = 0.20 — the wet side
    #  reads sharper than the dry one, which is the asymmetry the envelope exists to buy.
    st.update(f"""DELETE {{ GRAPH <http://example.org/orexis/graph/sensed> {{ ?o <http://www.w3.org/ns/sosa/hasSimpleResult> ?v }} }}
                  INSERT {{ GRAPH <http://example.org/orexis/graph/sensed> {{ ?o <http://www.w3.org/ns/sosa/hasSimpleResult> 0.75 }} }}
                  WHERE  {{ GRAPH <http://example.org/orexis/graph/sensed> {{
                      ?o <http://www.w3.org/ns/sosa/observedProperty> <{MOISTURE}> ;
                         <http://www.w3.org/ns/sosa/hasSimpleResult> ?v }} }}""")
    assert abs(urgency() - 0.10 / 0.20) < 1e-9, \
        "the same distance out must read differently per side — asymmetric scaling survives"


def test_the_measure_answers_one_for_a_world_with_no_reading():
    """The COALESCE the engine's silent arithmetic demands, exercised through the measure
    itself: asked of a world holding no observation, the answer is 1.0 and never unbound —
    an unmeasured want must not read as no urgency, and this store binds NOTHING for
    arithmetic over an unbound value rather than failing."""
    from agent.measure import urgency_of
    from agent.ontology import SENSED_GRAPH, beliefs_graph
    from agent.regions import measures_of

    st = genesis_store()                      # no readings seeded at all
    wants = desires_build(st, "fern")
    measure = measures_of(wants.query_union, FERN)[MOISTURE]
    assert urgency_of(st.query, measure,
                      subject="http://example.org/orexis/world/simulation#fern",
                      observed_property=MOISTURE, sensed=SENSED_GRAPH,
                      beliefs=beliefs_graph("fern")) == 1.0


def test_this_store_still_will_not_divide_one_duration_by_another():
    """The measurement the Python fallback exists for, pinned so it cannot rot.

    Four operations, and the split is what matters: comparing durations and adding one to a
    dateTime work, while dividing or scaling a duration binds NOTHING — no error, no row
    missing, just a column of unbound values. That is the failure this project keeps meeting
    from a new direction, so it is worth a test that fails LOUDLY the day the engine grows the
    operation: the arithmetic can then move back into `desires.rq` where it belongs.
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
        "if this now binds, delete _duty_urgency and let desires.rq do the arithmetic"
    assert answer("BIND((?e - ?at) * 0.5 AS ?r)") is None
    assert answer("BIND(?at + (?e - ?at) AS ?r)") is not None, "dateTime + duration works"
    assert answer("BIND((?e - ?at) > (?e - ?e) AS ?r)") is not None, "and durations compare"


def test_this_store_will_not_divide_an_exact_zero_by_a_decimal():
    """The measure's arithmetic, pinned the way the duration limit above is — found while
    building it, not read anywhere.

    pyoxigraph 0.5.9 divides decimals — `0.1 / 0.3` binds — and binds NOTHING for the same
    expression with a ZERO dividend. No error, no missing row, an unbound column: an agent
    sitting exactly at its aim would have read as maximally urgent through the measure's own
    error-COALESCE, which is why the compiled query answers the zero-distance case with an IF
    before any division. If the first assertion ever fails, the engine has been fixed and the
    guard in `desires.ru` becomes belt-and-braces rather than load-bearing.
    """
    st = ox.Store()

    def answer(bind):
        rows = list(st.query("SELECT ?r WHERE { %s }" % bind))
        return rows[0]["r"] if rows else None

    assert answer("BIND(0.0 / 0.3 AS ?r)") is None, \
        "a zero dividend now divides — the IF guard in the measure is no longer load-bearing"
    assert answer("BIND(0.1 / 0.3 AS ?r)") is not None, "while a nonzero one always did"
    assert answer("BIND(IF(0.0 <= 0, 0.0, 0.0 / 0.3) AS ?r)") is not None, \
        "and the IF short-circuits, which is what makes the guard a guard"
