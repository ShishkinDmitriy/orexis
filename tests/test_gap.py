"""The gap between desired and sensed state — the diff, as the packages ship it.

Phase 1 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md: how far an agent
sits from what it wants stops being arithmetic inside a module and becomes a query anyone can
run. These drive it against the real simulation world, with observations written the way an
agent writes them, because the join it performs — public regions against the private sensed
graph — is exactly the thing a unit test with a hand-built store would fake away.
"""

from __future__ import annotations

import re

from packages.capability.desire import gaps_of, regions_of

from conftest import MOISTURE, TEMPERATURE, build_agent, desires_build, genesis_store


def _judged(st, *extra):
    """Validation data the way the boot builds it since #312: publics and readings from the
    store, the wants and the pick record through the desire modality — and only through it."""
    from agent import effects
    from agent.validate import graph_from

    data = graph_from(st, *st.public_graphs(), *extra)
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))
    return data


def _gaps(st, uri, agent_id="fern"):
    """Both handles the way an agent holds them: wants from the desire modality's build,
    readings from the store (#312)."""
    return gaps_of(desires_build(st, agent_id).query_union, st.query, uri)

FERN = "http://example.org/orexis/world/simulation#fern_agent"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"


def test_the_query_and_the_module_are_one_definition(query_with_readings):
    """|gap| is `urgency`, by construction — and since the split, by construction in the
    literal sense: `gaps_of` computes the gap FROM `Region.urgency`, so this holds the sign
    convention and the join to the same numbers every other consumer reads."""
    st = genesis_store({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0})
    gaps, regions = _gaps(st, FERN), regions_of(desires_build(st, "fern").query_union, FERN)
    assert set(gaps) == {MOISTURE, TEMPERATURE}
    for prop, gap in gaps.items():
        assert abs(gap.gap) == round(regions[prop].urgency(gap.value), 6) or \
            abs(abs(gap.gap) - regions[prop].urgency(gap.value)) < 1e-9


def test_the_gap_is_signed_and_the_sign_says_which_way_out(query_with_readings):
    """0.30 moisture is below fern's region (0.45-0.65) and 33 degrees is above its band
    (18-24): one gap negative, one positive. The sign is what a planner steers by — a band
    says IN TROUBLE, the gap says which direction relief lies in."""
    gaps = _gaps(genesis_store(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), FERN)
    assert gaps[MOISTURE].gap < 0 < gaps[TEMPERATURE].gap


def test_at_the_survival_bound_the_gap_is_exactly_one(query_with_readings):
    """The normalisation: fern survives 0.20-0.85 moisture, so 0.20 is the whole of the dry
    room spent — and past it is not more than everything."""
    at_floor = _gaps(genesis_store({("fern", MOISTURE): 0.20}), FERN)
    assert at_floor[MOISTURE].gap == -1.0
    past_it = _gaps(genesis_store({("fern", MOISTURE): 0.05}), FERN)
    assert past_it[MOISTURE].gap == -1.0


def test_unmeasured_is_not_satisfied():
    """At birth there is a desired state and no observations, so the diff is EMPTY — not zero.

    This is the fact the whole roadmap leans on: a gap of 0 would read as "all is well" and an
    absent row reads as "go and look", and the first intention is always to look. A defaulted
    zero here would quietly retire the reason the society polls at all.
    """
    assert _gaps(genesis_store(), FERN) == {}


def test_an_agent_with_no_desire_has_no_gap(query_with_readings):
    """The supplier observes nothing and wants nothing — no regions, no rows, and nothing here
    invents a stake for it. Handed readings about somebody else's plant, still nothing."""
    assert _gaps(genesis_store({("fern", MOISTURE): 0.05}), SUPPLIER, "supplier") == {}


def test_the_agent_reports_its_worst_gap(monkeypatch, query_with_readings):
    """The first consumer: the health series. `worst_gap` is |gap| over every property, so an
    operator's dashboard can rank agents in different units on one scale — and its absence
    before the first reading says 'wants things it has not seen', not 'fine'."""
    fern = build_agent("fern", genesis_store(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")
    reported = desire.reports()
    assert reported["desires"] == 2
    assert reported["desires_measured"] == 2
    # temperature is the worse of the two: 33 against 18-24 with survival to 35
    assert reported["worst_gap"] == round(abs(desire.gaps()[TEMPERATURE].gap), 3)

    unmeasured = build_agent("fern", genesis_store(), monkeypatch)
    fresh = next(m for m in unmeasured.modules if m.name == "desire")
    assert "worst_gap" not in fresh.reports()
    assert fresh.reports()["desires"] == 2
    assert fresh.reports()["desires_measured"] == 0


# --- issue #124: current, stale, unmeasurable — three states, told apart ----

def test_a_dead_sensors_last_reading_does_not_present_as_a_current_gap(monkeypatch):
    """The defect: observations are upserted and never expire, so a dead probe's last value
    kept producing a comfortable-looking worst_gap for however long the probe stayed dead.
    A reading past the agent's OWN freshness rule — the cadence it commanded plus its grace —
    now drops out of `current()` and out of the report: worst_gap disappears rather than
    reassures, desires_measured says how many eyes are actually open, and reading_age_s on the
    same dashboard says why."""
    from datetime import datetime, timedelta, timezone

    long_dead = datetime.now(timezone.utc) - timedelta(seconds=6_000)  # slow 600 + grace 45
    fern = build_agent("fern", genesis_store(
        {("fern", MOISTURE): 0.05}, result_time=long_dead), monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")

    # the diff still SAYS it: last I looked I was parched, and I cannot see any more
    assert desire.gaps()[MOISTURE].gap == -1.0
    assert desire.gaps()[MOISTURE].age_s() > 5_000

    # but nothing presents it as live
    assert MOISTURE not in desire.current()
    reported = desire.reports()
    assert "worst_gap" not in reported
    assert reported["desires_measured"] == 0


def test_a_fresh_reading_is_current_by_the_same_rule(monkeypatch):
    fern = build_agent("fern", genesis_store({("fern", MOISTURE): 0.30}), monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")
    assert MOISTURE in desire.current()
    assert desire.reports()["desires_measured"] == 1   # temperature stays unmeasured
    assert desire.reports()["desires"] == 2


def test_a_desire_nothing_watches_warns_at_the_gate(monkeypatch):
    """The blind case, said where the sovereign who could add the instrument is reading.

    Unwire fern's thermometer and its temperature desire still derives — a range is a fact
    about the plant that does not wait for an instrument — but the agent will never see a
    reading to hold it to, and nothing else would ever mention that. A WARNING, not a refusal:
    the wiring is legitimate, the sentence in the boot log was the missing part. The shipped
    world stays clean, which is the negative half that keeps the channel worth reading.
    """
    from agent import genesis, loader
    from agent.ontology import WORLD_GRAPH, beliefs_graph
    from agent.validate import conforms, graph_from

    st = genesis_store()
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    data = _judged(st)
    ok, report = conforms(data, focus=FERN)
    assert ok and "polls no sensor" not in report, "the shipped world must warn nothing"

    unwired = genesis_store()
    unwired.update(f"""
        PREFIX ag: <http://example.org/orexis#>
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ <http://example.org/orexis/world/simulation#fern_agent>
            <http://example.org/orexis/sensing#polls> <http://example.org/orexis/world/simulation#air_temp_fern> }} }}
        WHERE {{}}""")
    for rule in loader.rule_files():
        unwired.update(genesis.substitute(rule.read_text(), unwired))
    genesis.birth(unwired, genesis.world_dir("simulation"), "fern")
    data = _judged(unwired)
    ok, report = conforms(data, focus=FERN)
    assert ok, "blind is legal — the region is real and the agent must start"
    assert "polls no sensor" in report


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
    data = _judged(st, SENSED_GRAPH)
    ok, report = conforms(data, focus=FERN)
    assert ok, "a warning must not fail validation — the agent has to be able to start"
    #  The message names the side and the edge, because the shape that produced it was minted
    #  for this agent and this property (#242). Before the split both sides fired one shape
    #  with one sentence, and a plant drowning read exactly like a plant dying of thirst.
    assert "SoilMoisture is below 0.2" in report
    assert "past what fern survives" in report
    assert "is above" not in report, "one side is wrong, and only that side should be reported"

    calm = genesis_store({("fern", MOISTURE): 0.30})  # outside the region, inside the envelope
    genesis.birth(calm, genesis.world_dir("simulation"), "fern")
    data = _judged(calm, SENSED_GRAPH)
    ok, report = conforms(data, focus=FERN)
    assert ok
    assert "past what fern survives" not in report, \
        "merely dry is the society's ordinary working state, not a warning"


def test_the_region_and_the_aim_reach_the_agents_own_bucket(monkeypatch):
    """#61's argument extended from the revisable picks to the wants: WHERE the want sits, not
    merely that it exists — and the property is a TAG, on the sovereign's own suggestion, so
    one generic panel groups any number of wants where a suffixed field name could only be
    string-matched. Into this agent's own series: the operator sees them, rivals do not."""
    fern = build_agent("fern", genesis_store({"fern": 0.55}), monkeypatch)
    desire = next(m for m in fern.modules if m.name == "desire")
    rows = {tags["property"]: (measurement, fields)
            for measurement, tags, fields in desire.series()
            if measurement == "agent_desire"}   # the ranking's own row has no property tag
    m, moisture = rows["SoilMoisture"]
    assert m == "agent_desire"
    #  The region and the pick inside it, and no urgency: how badly a want is unmet is
    #  reported per WANT by the deliberator (`agent_want`), because a property cannot name a
    #  freshness want or a duty, and two places computing the same figure is the drift this
    #  project keeps removing.
    assert moisture == {"desired_low": 0.45, "desired_high": 0.65, "aim": 0.55}
    _, temperature = rows["AirTemperature"]
    assert temperature == {"desired_low": 18.0, "desired_high": 24.0}, \
        "a want with no aim reports its region and no invented pick"


def test_an_unmet_want_is_not_printed_as_a_finding():
    """A report is what a person reads when something is wrong, and a want is not that.

    Once a desire compiled to SHACL, every property nobody has read yet produced a result —
    which at genesis is every property — and `orexis-validate` printed a wall of them about a
    world it was accepting. The verdict was never affected; the noise was, and noise in a gate
    teaches people to skip the gate.

    Written so it fails from either end. The want must be REAL — the same store, asked through
    the package's own reader, reports it — or this would pass on a world with nothing to say.
    And the header has to agree with the body, because the filter rewrites a count pySHACL
    wrote: a report claiming three results and showing one is how a filter goes wrong quietly.
    """
    from agent import genesis
    from agent.ontology import SENSED_GRAPH, beliefs_graph
    from agent.validate import conforms, graph_from

    dry = genesis_store({("fern", MOISTURE): 0.30})   # outside the region, inside the envelope
    genesis.birth(dry, genesis.world_dir("simulation"), "fern")
    data = _judged(dry, SENSED_GRAPH)
    ok, report = conforms(data, focus=FERN)

    assert ok
    assert "a gap, which is what an agent is for" not in report, \
        "the want's own message is the signal: the filter matches pySHACL's spelling of the " \
        "severity, so its spelling is a dependency, and this is how a change in it surfaces"
    #  Not a search for `ShouldBecome` anywhere — a surviving WARNING quotes the term inside
    #  its own SPARQL text, and refusing that would be refusing a shape for talking about the
    #  thing it is there to talk about.

    shown = report.count("Validation Result in")
    if claimed := re.search(r"Results \((\d+)\):", report):
        assert int(claimed.group(1)) == shown, "the header must count what the body shows"

    assert _gaps(dry, FERN)[MOISTURE].gap < 0, \
        "the store must still report the gap the report no longer prints"


def test_the_filter_keeps_a_violation_however_pyshacl_heads_it():
    """The filter reads pySHACL's prose, and prose has two headings.

    A violation is written "Constraint Violation in ...", everything else "Validation Result
    in ...". Knowing only the second put every violation into the report's HEADER, where the
    filter discarded it along with the rest — so a world was refused with a report that said
    it conformed. Four shape tests caught it; this one names it, because those four would all
    have to be read before anyone suspected the filter.
    """
    from agent.validate import _without_wants

    report = (
        "Validation Report\nConforms: False\nResults (2):\n"
        "Constraint Violation in SPARQLConstraintComponent (http://example/x):\n"
        "\tSeverity: sh:Violation\n\tMessage: the aim sits outside the region\n"
        "Validation Result in QualifiedValueShapeConstraintComponent (http://example/y):\n"
        "\tSeverity: ag:ShouldBecome\n\tMessage: a gap, which is what an agent is for\n")

    kept = _without_wants(report)
    assert "the aim sits outside the region" in kept
    assert "a gap, which is what an agent is for" not in kept
    assert "Results (1):" in kept, "the count must follow what survived"
    assert _without_wants("Validation Report\nConforms: True") == "Validation Report\nConforms: True"


def test_the_ranking_reaches_the_dashboards_with_the_split_that_matters(monkeypatch):
    """A drowning society must not graph like a thirsty one.

    Both are "unmet at urgency 1.00", and only one of them is anybody's to fix: no lever in
    this society lowers moisture, so a fern above its region is a row an operator should read
    last and a model should never propose against. The count that says so is `unactionable`,
    and it is computed by ASKING the deliberator rather than by a second copy of the menu.

    Asked at a value ABOVE the region on purpose. Below it, every count agrees whatever the
    join does, and the test would pass on a version that never consulted anything.
    """
    fern = build_agent("fern", genesis_store({("fern", MOISTURE): 0.95}), monkeypatch)
    #  Reported by the DELIBERATOR since #233: counting what nothing can be done about needs
    #  both the wants (the modules') and the moves (its own), and it is the one module that
    #  sees both.
    reflex = next(m for m in fern.modules if m.name == "deliberation")
    _, _, fields = next(row for row in reflex.series() if row[0] == "agent_goals")

    assert fields["unmet"] >= 1
    assert fields["hottest"] == 1.0, "past the survival ceiling is as bad as it gets"
    assert fields["unactionable"] >= 1, \
        "wet is unmet and unactionable — the whole point of the column"
    assert not [m for m in fern.modules if m.name == "owing"], \
        "a plant holds no lever anyone may demand, so it keeps no ledger at all"


def test_a_content_agent_reports_nothing_wanted_and_nothing_stuck(monkeypatch):
    """The counts are about WANTING, not about distance from the centre.

    Shipped wrong and caught on the bench inside ten minutes: `unmet` was "urgency > 0", which
    is false only at the exact centre of a region, and `unactionable` was "no move proposed",
    which is equally true of an agent that needs no move. The supplier — barrel at 1.97, well
    inside 1-5, urgency 0.003 — reported one unmet and one unactionable desire, so a calm society
    graphed as a stuck one. That is the failure the panel exists to prevent, arriving through
    the panel itself.

    A reading INSIDE the region but off its point is the only case that separates the two
    definitions, so that is what this asks about.
    """
    fern = build_agent("fern", genesis_store({("fern", MOISTURE): 0.52,
                                              ("fern", TEMPERATURE): 21.0}), monkeypatch)
    desires = fern.pursuing()
    assert all(g.is_met for g in desires), "0.52 in 0.45-0.65 and 21 in 18-24 are both met"
    assert any(g.urgency > 0 for g in desires), \
        "and still off-centre — which is what made the old definition look right"

    reflex = next(m for m in fern.modules if m.name == "deliberation")
    _, _, fields = next(row for row in reflex.series() if row[0] == "agent_goals")
    assert fields["unmet"] == 0.0
    assert fields["unactionable"] == 0.0, "content is not stuck"
    assert fields["desires"] == 2.0, "the wants are still counted — they are simply satisfied"
