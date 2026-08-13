"""The gap between desired and sensed state — the diff, as the packages ship it.

Phase 1 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md: how far an agent
sits from what it wants stops being arithmetic inside a module and becomes a query anyone can
run. These drive it against the real simulation world, with observations written the way an
agent writes them, because the join it performs — public regions against the private sensed
graph — is exactly the thing a unit test with a hand-built store would fake away.
"""

from __future__ import annotations

from packages.capability.desire import gaps_of, regions_of

from conftest import MOISTURE, TEMPERATURE, build_agent, genesis_store

FERN = "http://example.org/agora#fern_agent"
SUPPLIER = "http://example.org/agora#supplier"


def test_the_query_and_the_module_are_one_definition(query_with_readings):
    """|gap| is `urgency`, by construction: gap.rq is the definition and Region reads the same
    numbers, so the two must agree to the store's own precision. If they ever diverge, one of
    them has been edited alone — and every consumer of the query is now judging differently
    from the agent being judged."""
    q = query_with_readings({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0})
    gaps, regions = gaps_of(q, FERN), regions_of(q, FERN)
    assert set(gaps) == {MOISTURE, TEMPERATURE}
    for prop, gap in gaps.items():
        assert abs(gap.gap) == round(regions[prop].urgency(gap.value), 6) or \
            abs(abs(gap.gap) - regions[prop].urgency(gap.value)) < 1e-9


def test_the_gap_is_signed_and_the_sign_says_which_way_out(query_with_readings):
    """0.30 moisture is below fern's region (0.45-0.65) and 33 degrees is above its band
    (18-24): one gap negative, one positive. The sign is what a planner steers by — a band
    says IN TROUBLE, the gap says which direction relief lies in."""
    gaps = gaps_of(query_with_readings(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), FERN)
    assert gaps[MOISTURE].gap < 0 < gaps[TEMPERATURE].gap


def test_at_the_survival_bound_the_gap_is_exactly_one(query_with_readings):
    """The normalisation: fern survives 0.20-0.85 moisture, so 0.20 is the whole of the dry
    room spent — and past it is not more than everything."""
    at_floor = gaps_of(query_with_readings({("fern", MOISTURE): 0.20}), FERN)
    assert at_floor[MOISTURE].gap == -1.0
    past_it = gaps_of(query_with_readings({("fern", MOISTURE): 0.05}), FERN)
    assert past_it[MOISTURE].gap == -1.0


def test_unmeasured_is_not_satisfied(query):
    """At birth there is a desired state and no observations, so the diff is EMPTY — not zero.

    This is the fact the whole roadmap leans on: a gap of 0 would read as "all is well" and an
    absent row reads as "go and look", and the first intention is always to look. A defaulted
    zero here would quietly retire the reason the society polls at all.
    """
    assert gaps_of(query, FERN) == {}


def test_an_agent_with_no_desire_has_no_gap(query_with_readings):
    """The supplier observes nothing and wants nothing — no regions, no rows, and nothing here
    invents a stake for it. Handed readings about somebody else's plant, still nothing."""
    q = query_with_readings({("fern", MOISTURE): 0.05})
    assert gaps_of(q, SUPPLIER) == {}


def test_the_agent_reports_its_worst_gap(monkeypatch, query_with_readings):
    """The first consumer: the health series. `worst_gap` is |gap| over every property, so an
    operator's dashboard can rank agents in different units on one scale — and its absence
    before the first reading says 'wants things it has not seen', not 'fine'."""
    fern = build_agent("fern", genesis_store(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")
    reported = desire.reports()
    assert reported["desires"] == 2
    # temperature is the worse of the two: 33 against 18-24 with survival to 35
    assert reported["worst_gap"] == round(abs(desire.gaps()[TEMPERATURE].gap), 3)

    unmeasured = build_agent("fern", genesis_store(), monkeypatch)
    fresh = next(m for m in unmeasured.modules if m.name == "desire")
    assert "worst_gap" not in fresh.reports()
    assert fresh.reports()["desires"] == 2


def test_a_reading_past_survival_warns_at_boot_and_does_not_refuse(monkeypatch):
    """The second consumer: validation. Past the envelope is an emergency, not an invalid
    belief — the agent MUST start, precisely so it can do something about it, and the report
    says why it had better hurry. A violation here would keep a thirsty agent from ever
    bidding for water, which is the one wrong direction.
    """
    from agent.ontology import SENSED_GRAPH, beliefs_graph
    from agent.validate import conforms, graph_from

    st = genesis_store({("fern", MOISTURE): 0.05})   # fern survives 0.20-0.85
    from agent import genesis
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    data = graph_from(st, *st.public_graphs(), beliefs_graph("fern"), SENSED_GRAPH)
    ok, report = conforms(data, focus=FERN)
    assert ok, "a warning must not fail validation — the agent has to be able to start"
    assert "survival envelope" in report

    calm = genesis_store({("fern", MOISTURE): 0.30})  # outside the region, inside the envelope
    genesis.birth(calm, genesis.world_dir("simulation"), "fern")
    data = graph_from(calm, *calm.public_graphs(), beliefs_graph("fern"), SENSED_GRAPH)
    ok, report = conforms(data, focus=FERN)
    assert ok
    assert "survival envelope" not in report, \
        "merely dry is the society's ordinary working state, not a warning"
