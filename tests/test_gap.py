"""The gap between desired and sensed state — the diff, as the packages ship it.

Phase 1 of knowledge/decisions/an-intention-is-an-amortised-deliberation.md: how far an agent
sits from what it wants stops being arithmetic inside a module and becomes a query anyone can
run. These drive it against the real simulation world, with observations written the way an
agent writes them, because the join it performs — public regions against the private sensed
graph — is exactly the thing a unit test with a hand-built store would fake away.
"""

from __future__ import annotations

import re

from orexis_capability_sensing.regions import regions_of

from conftest import sensing_of, MOISTURE, TEMPERATURE, build_agent, desires_build, genesis_store
from orexis_agent_progression.ontology import PUBLIC


def _judged(st, *extra):
    """Validation data the way the boot builds it since #312: publics and readings from the
    store, the wants and the pick record through the desire modality — and only through it."""
    from orexis_agent_deliberation import effects
    from agent.validate import graph_from

    data = graph_from(st, *st.graphs_of(PUBLIC), *extra)
    for triple in desires_build(st, "fern").construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"):
        data.add(effects._triple(triple))
    return data


def _gaps(st, uri, agent_id="fern", monkeypatch=None):
    """Through a REAL agent, because the magnitude is a capability's answer now: sensing
    hands `gaps_of` the choir's own (`Agent.desire_urgency`) and sensing answers from its own
    declaration — a hand-built join would fake away exactly the contribution under test."""
    return sensing_of(build_agent(agent_id, st, monkeypatch)).gaps()

FERN = "http://example.org/orexis/world/simulation#fern_agent"
SUPPLIER = "http://example.org/orexis/world/simulation#supplier"


def test_the_query_and_the_module_are_one_definition(query_with_readings, monkeypatch):
    """|gap| is `urgency`, by construction — the magnitude is the measure sensing declares,
    asked through the choir, and where no aim sits off the centre (fern's picks are the
    centres in this world) it must agree with `Region.urgency`, the reference arithmetic the
    declared query is held to at exactly that fallback."""
    st = genesis_store({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0})
    gaps = _gaps(st, FERN, monkeypatch=monkeypatch)
    regions = regions_of(st.reader(PUBLIC), FERN)
    assert set(gaps) == {MOISTURE, TEMPERATURE}
    for prop, gap in gaps.items():
        assert abs(gap.gap) == round(regions[prop].urgency(gap.value), 6) or \
            abs(abs(gap.gap) - regions[prop].urgency(gap.value)) < 1e-9


def test_the_gap_is_signed_and_the_sign_says_which_way_out(query_with_readings, monkeypatch):
    """0.30 moisture is below fern's region (0.45-0.65) and 33 degrees is above its band
    (18-24): one gap negative, one positive. The sign is what a planner steers by — a band
    says IN TROUBLE, the gap says which direction relief lies in."""
    gaps = _gaps(genesis_store(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), FERN,
        monkeypatch=monkeypatch)
    assert gaps[MOISTURE].gap < 0 < gaps[TEMPERATURE].gap


def test_at_the_survival_bound_the_gap_is_exactly_one(query_with_readings, monkeypatch):
    """The normalisation: fern survives 0.20-0.85 moisture, so 0.20 is the whole of the dry
    room spent — and past it is not more than everything."""
    at_floor = _gaps(genesis_store({("fern", MOISTURE): 0.20}), FERN, monkeypatch=monkeypatch)
    assert at_floor[MOISTURE].gap == -1.0
    past_it = _gaps(genesis_store({("fern", MOISTURE): 0.05}), FERN, monkeypatch=monkeypatch)
    assert past_it[MOISTURE].gap == -1.0


def test_unmeasured_is_not_satisfied(monkeypatch):
    """At birth there is a desired state and no observations, so the diff is EMPTY — not zero.

    This is the fact the whole roadmap leans on: a gap of 0 would read as "all is well" and an
    absent row reads as "go and look", and the first intention is always to look. A defaulted
    zero here would quietly retire the reason the society polls at all.
    """
    assert _gaps(genesis_store(), FERN, monkeypatch=monkeypatch) == {}


def test_an_agent_with_no_desire_has_no_gap(query_with_readings, monkeypatch):
    """The supplier observes nothing and wants nothing — no regions, no rows, and nothing here
    invents a stake for it. Handed readings about somebody else's plant, still nothing."""
    assert _gaps(genesis_store({("fern", MOISTURE): 0.05}), SUPPLIER, "supplier",
                 monkeypatch=monkeypatch) == {}


def test_the_agent_reports_its_worst_gap(monkeypatch, query_with_readings):
    """The first consumer: the health series. `worst_gap` is |gap| over every property, so an
    operator's dashboard can rank agents in different units on one scale — and its absence
    before the first reading says 'wants things it has not seen', not 'fine'."""
    fern = build_agent("fern", genesis_store(
        {("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}), monkeypatch)
    desire = sensing_of(fern)
    reported = desire.reports()
    assert reported["desires"] == 2
    assert reported["desires_measured"] == 2
    # temperature is the worse of the two: 33 against 18-24 with survival to 35
    assert reported["worst_gap"] == round(abs(desire.gaps()[TEMPERATURE].gap), 3)

    unmeasured = build_agent("fern", genesis_store(), monkeypatch)
    fresh = sensing_of(unmeasured)
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
    desire = sensing_of(fern)
    #  STARTED, as a booting agent starts it, because a reading is stale when sensing says so
    #  ON the reading and no longer because its timestamp is old (#598): `start()` re-arms the
    #  horizon on every standing reading and marks one already past it, which is exactly the
    #  case a probe that died while the process was down leaves behind.
    desire.start()

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
    desire = sensing_of(fern)
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
    from agent import genesis
    from assembly import loader
    from orexis_agent_progression.ontology import WORLD_GRAPH, picks_graph
    from agent.validate import conforms, graph_from

    st = genesis_store()
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    data = _judged(st)
    ok, report = conforms(data, focus=FERN)
    assert ok and "polls no sensor" not in report, "the shipped world must warn nothing"

    unwired = genesis_store()
    unwired.update(f"""
        PREFIX orexis: <http://example.org/orexis#>
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
    from orexis_agent_progression.ontology import STATE_GRAPH, picks_graph
    from agent.validate import conforms, graph_from

    st = genesis_store({("fern", MOISTURE): 0.05})   # fern survives 0.20-0.85
    from agent import genesis
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    data = _judged(st, STATE_GRAPH)
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
    data = _judged(calm, STATE_GRAPH)
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
    desire = sensing_of(fern)
    rows = {tags["property"]: (measurement, fields)
            for measurement, tags, fields in desire.series()
            if measurement == "agent_desire"}   # the ranking's own row has no property tag
    m, moisture = rows["SoilMoisture"]
    assert m == "agent_desire"
    #  The region and the pick inside it, and no urgency: how badly a want is unmet is
    #  reported per WANT by the deliberator (`agent_want`), because a property cannot name a
    #  freshness want or an obligation, and two places computing the same figure is the drift this
    #  project keeps removing.
    assert moisture == {"desired_low": 0.45, "desired_high": 0.65, "aim": 0.55}
    _, temperature = rows["AirTemperature"]
    assert temperature == {"desired_low": 18.0, "desired_high": 24.0}, \
        "a want with no aim reports its region and no invented pick"


def test_an_unmet_want_is_not_printed_as_a_finding(monkeypatch):
    """A report is what a person reads when something is wrong, and a want is not that.

    Once a desire compiled to SHACL, every property nobody has read yet produced a result —
    which at genesis is every property — and `orexis-validate` printed a wall of them about a
    world it was accepting. The verdict was never affected; the noise was, and noise in a gate
    teaches people to skip the gate.

    Since #472 there is nothing to filter: a met-test enters no validation pass — the
    metWhen linkage keeps it out — so the want produces no result to hide. Written to fail
    from either end even so: the want must be REAL — the same store, asked through the
    package's own reader, reports it — or this would pass on a world with nothing to say;
    and the header must agree with the body, which now means pySHACL's own untouched report
    agreeing with itself.
    """
    from agent import genesis
    from orexis_agent_progression.ontology import STATE_GRAPH, picks_graph
    from agent.validate import conforms, graph_from

    dry = genesis_store({("fern", MOISTURE): 0.30})   # outside the region, inside the envelope
    genesis.birth(dry, genesis.world_dir("simulation"), "fern")
    data = _judged(dry, STATE_GRAPH)
    ok, report = conforms(data, focus=FERN)

    assert ok
    assert "a gap, which is what an agent is for" not in report, \
        "no want result may reach a person: since #472 a met-test enters no validation pass " \
        "at all — the metWhen linkage keeps it out — where a filter used to drop its results"

    shown = report.count("Validation Result in")
    if claimed := re.search(r"Results \((\d+)\):", report):
        assert int(claimed.group(1)) == shown, "the header must count what the body shows"

    assert _gaps(dry, FERN, monkeypatch=monkeypatch)[MOISTURE].gap < 0, \
        "the store must still report the gap the report no longer prints"





def test_the_ranking_reaches_the_dashboards_with_the_split_that_matters(monkeypatch):
    """A drowning society must not graph like a thirsty one.

    Both are unmet, and only one of them is anybody's to fix: no lever in this society lowers
    moisture, so a fern above its region is a row an operator should read last and a model
    should never propose against. The count that says so is `unactionable`,
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
    #  NO `hottest`: it was the largest urgency across the wants, and the number it took the
    #  maximum of is gone — four packages each computed one its own way, ahead of the search
    #  that was the only thing able to compare them.
    assert "hottest" not in fields
    assert fields["unactionable"] >= 1, \
        "wet is unmet and unactionable — the whole point of the column"
    #  A plant holds no lever anyone may demand, so it has NO LEDGER — which is a stronger
    #  statement than the empty one this used to make. The ledger is hosting's, because a
    #  debt arises from a claim this agent ISSUED, and a bidder issues none.
    assert not [m for m in fern.modules if m.name == "hosting"], \
        "a plant hosts nothing, so there is no ledger for it to owe from"



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
    assert all(g.state == "met" for g in desires), \
        "and the STATE is the region's verdict, which is what the old definition confused"

    reflex = next(m for m in fern.modules if m.name == "deliberation")
    _, _, fields = next(row for row in reflex.series() if row[0] == "agent_goals")
    assert fields["unmet"] == 0.0
    assert fields["unactionable"] == 0.0, "content is not stuck"
    #  FOUR, and the extra two are what this change added to every sensing agent: a region
    #  want and a freshness want per property, because knowing the number and the number
    #  being right are two things a pot can be short of. Both are met here — the readings are
    #  inside their regions and both arrived a moment ago — so the counts that matter are
    #  still zero, which is the property this test is really about.
    assert fields["desires"] == 4.0, "the wants are still counted — they are simply satisfied"
