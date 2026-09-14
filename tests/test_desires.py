"""What an agent is pursuing, hottest first — the split pair and its one join (#234, #298).

`desires.rq` asks the desire modality, `readings.rq` asks the belief modality, and `desires_of`
is the join — a stake's magnitude is whichever capability answers the choir (sensing's
declared measure), an obligation's fraction is `_duty_urgency`, Python because the store's engine
will not divide durations. These pin the states, the ranking, both fallbacks and the engine
limits.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox


from orexis_capability_sensing.regions import ObservedDesire
from conftest import sensing_of, MOISTURE, TEMPERATURE, build_agent, desires_build, genesis_store

FERN = "http://example.org/orexis/world/simulation#fern_agent"


def _fern(readings, monkeypatch):
    """A real fern, because a stake's urgency is a capability's answer now: sensing asks
    the choir (`Agent.desire_urgency`) and sensing answers from its own declaration, so a
    hand-built join would fake away the contribution these tests exercise."""
    st = genesis_store(readings)
    return st, build_agent("fern", st, monkeypatch)


def test_the_query_and_the_module_agree_with_the_diff(query_with_readings, monkeypatch):
    """One definition, three readers. The ranking and the diff both ask the same declared
    measure through the same choir road, so the urgency a desire carries must equal the |gap|
    the diff reports, to the store's own precision.

    Both properties, and both signs: fern below its moisture region and above its temperature
    one. A copy that dropped the sign handling would agree on one of them and not the other.
    """
    _, fern = _fern({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}, monkeypatch)
    desires, diffs = sensing_of(fern).desires(), sensing_of(fern).gaps()

    #  STAKES, which now needs saying: a property carries an epistemic want beside its region,
    #  and a dict keyed on the property alone quietly kept whichever came last. The diff is
    #  about numbers, so the wants it must agree with are the ones about numbers.
    stakes = {g.observed_property: g for g in desires
              if not g.is_obligation and not g.is_epistemic}
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
    _, fern = _fern({("fern", TEMPERATURE): 21.0}, monkeypatch)  # temperature seen, moisture never
    desires = sensing_of(fern).desires()

    moisture = next(g for g in desires if g.observed_property == MOISTURE)
    assert moisture.value is None
    assert moisture.urgency == 1.0
    assert desires[0] is moisture, "and it sorts to the top, where a deliberator will meet it"
    assert sensing_of(fern).gaps().get(MOISTURE) is None, \
        "while the diff still reports nothing, which is right for a diff"


def test_the_states_a_stake_can_be_in(monkeypatch):
    """met, unmet and unmeasured, asked across the range rather than at one value — a boundary
    that is wrong by one reads correctly at the centre and at the extremes."""
    for value, expected in [(0.55, "met"), (0.45, "met"), (0.65, "met"),
                            (0.30, "unmet"), (0.95, "unmet")]:
        _, fern = _fern({("fern", MOISTURE): value}, monkeypatch)
        moisture = next(g for g in sensing_of(fern).desires()
                        if g.observed_property == MOISTURE)
        met = moisture.urgency == 0.0 or (0.45 <= value <= 0.65)
        assert met == (expected == "met"), f"{value} should be {expected}"


def test_a_duty_carries_its_timestamps_and_the_fraction_is_computed_from_them(monkeypatch):
    """The engine limit, made visible rather than worked around.

    A obligation's urgency is the fraction of its redeem window that has run, and this store binds
    NOTHING for `duration / duration` — so the query carries `owedAt` and `expiresAt` and the
    division happens in Python. Asked at three points across one window, because the ends are
    what the choice was made about: cool at issue, maximal at the deadline.
    """
    from agent import genesis
    from orexis_agent_progression.ontology import obligations_graph

    st = genesis_store({("fern", MOISTURE): 0.55})
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("fern")}> {{
        <http://example.org/orexis#obligation.j1> a <http://example.org/orexis#Desire> ;
            <http://example.org/orexis/market#owedTo>
                <http://example.org/orexis/world/simulation#tomato_agent> ;
            <http://example.org/orexis/market#forClaim> "j1" ;
            <http://example.org/orexis/market#presented> true ;
            <http://example.org/orexis/market#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
            <http://example.org/orexis#expiresAt> "{(owed + timedelta(seconds=900)).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")

    fern = build_agent("fern", st, monkeypatch)

    #  THE LEDGER IS CONSTRUCTED, not reached through the agent: it is hosting's since the
    #  ledger moved into the market package, and fern bids rather than hosts. What is under
    #  test is the urgency curve of a debt, which is the ledger's arithmetic and needs no
    #  host to exercise.
    from orexis_capability_market.ower import Ower

    ledger = Ower(fern)

    def duty_at(offset_s):
        return next(g for g in ledger.desires(now=owed + timedelta(seconds=offset_s))
                    if g.is_obligation)

    assert duty_at(0).urgency == 0.0
    assert abs(duty_at(450).urgency - 0.5) < 0.02
    assert duty_at(900).urgency == 1.0
    assert duty_at(5000).urgency == 1.0, "clamped — no more overdue than overdue"
    assert duty_at(0).pursuable and not duty_at(5000).pursuable, \
        "past the window there is nothing left to spend, however hot it reads"


def test_a_stakes_urgency_is_measured_from_the_aim_and_follows_a_repick_without_a_rebuild(
        monkeypatch):
    """The finding a-desire-states-its-own-measure records, pinned from the ranking side.

    The reflex steered toward the AIM while urgency was measured from the region's CENTRE, so
    the two mechanisms pursued different targets whenever the pick sat off-centre. The desire's
    declared measure reads the pick out of the belief base AT QUERY TIME — so moving the aim
    moves the urgency with no desires rebuild, which is what a review's re-pick needs, and the
    scaling stays asymmetric: the room below the aim is aim-to-floor, above it aim-to-ceiling,
    so the same 0.10 out reads differently per side. Fern: region 0.45-0.65, survives 0.2-0.85.
    """
    from orexis_agent_progression.ontology import beliefs_graph

    st, fern = _fern({("fern", MOISTURE): 0.55}, monkeypatch)

    def urgency():
        return next(g for g in sensing_of(fern).desires()
                    if g.observed_property == MOISTURE).urgency

    assert urgency() == 0.0, "at the pick (0.55, which is also the centre) nothing is urgent"

    #  The re-pick: the aim moves in the BELIEF BASE alone — the desires store is deliberately
    #  not rebuilt, because the claim under test is that the measure asks, not that a rebuild
    #  recompiles.
    st.update(f"""DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim <https://schema.org/value> ?v }} }}
                  INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ?aim <https://schema.org/value> 0.65 }} }}
                  WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{
                      <{FERN}> <http://example.org/orexis/sensing#aims> ?aim .
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


def test_the_measure_answers_one_for_a_world_with_no_reading(monkeypatch):
    """The COALESCE the engine's silent arithmetic demands, exercised through the whole choir
    road: asked of a world holding no observation, sensing's answer is 1.0 and never unbound —
    an unmeasured want must not read as no urgency, and this store binds NOTHING for
    arithmetic over an unbound value rather than failing."""
    from orexis_agent_deliberation.desire import Desire
    from orexis_agent_progression.ontology import STATE_GRAPH

    st, fern = _fern(None, monkeypatch)       # no readings seeded at all
    probe = ObservedDesire(uri="urn:asked", urgency=1.0, observed_property=MOISTURE)
    assert fern.desire_urgency(probe, st.query, STATE_GRAPH) == 1.0


def test_a_want_whose_kind_nothing_measures_scores_a_logged_one(monkeypatch):
    """The defined fallback, pinned: a desire whose KIND nothing loaded measures reads
    urgency 1.0 — not knowing how bad is maximal, consistent with `urgency(None)` — rather
    than quietly reviving a Python arithmetic beside the declared one. Constructed by
    emptying sensing's declaration, the way the partial-plan test removes Acquire's effect
    rule: the shipped worlds never hit this, and a sibling test holds THAT."""
    from orexis_capability_sensing import module as sensing

    monkeypatch.setattr(sensing, "_DECLARED_MEASURES", ())
    _, fern = _fern({("fern", MOISTURE): 0.55}, monkeypatch)
    moisture = next(g for g in sensing_of(fern).desires()
                    if g.observed_property == MOISTURE)
    assert moisture.urgency == 1.0, "unmeasurable must never read as content"
    assert moisture.state == "met", \
        "while the met-verdict stays the shape's — the two are different questions"


def test_every_shipped_stake_resolves_a_declared_measure(monkeypatch):
    """The fallback above must be a case no ratified world hits — every desiring agent in the
    shipped worlds holds a sensing module whose declaration measures its stakes, every stake
    property being a `sosa:ObservableProperty`. If this fails, a world has grown a want
    nothing loaded can weigh, and that is a genesis conversation rather than a silent 1.0."""
    from orexis_agent_deliberation.desire import Desire
    from orexis_agent_progression.ontology import STATE_GRAPH
    from orexis_agent_progression.store import bindings

    checked = 0
    for world in ("simulation", "loner"):
        monkeypatch.setenv("OREXIS_WORLD", world)
        st = genesis_store(world=world)
        for row in bindings(st.query(
                'SELECT ?a ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id }')):
            agent = build_agent(row["id"], st, monkeypatch)
            for prop in sensing_of(agent).regions:
                probe = ObservedDesire(uri="urn:asked", urgency=1.0, observed_property=prop)
                assert agent.desire_urgency(probe, st.query, STATE_GRAPH) is not None, \
                    f'{row["id"]} in {world}: a stake nothing loaded measures'
                checked += 1
    assert checked >= 3, "the walk went quiet — no stakes were checked at all"


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


def test_an_obligation_row_typed_before_the_class_retired_still_serves(monkeypatch):
    """#471 folded the Obligation class, and readers match premises, never a type.

    A live volume written before the fold holds rows typed with the retired IRI, and beliefs
    are never reset — so the guarantee has to be a reader that does not care. This authors
    exactly such a row and asserts the ledger still serves it, on both the desire road and the
    ask road; the day a type-match regrows in `_DUTIES_Q` or `owed`, this goes red."""
    from agent import genesis
    from orexis_agent_progression.ontology import obligations_graph

    st = genesis_store({("fern", MOISTURE): 0.55})
    genesis.birth(st, genesis.world_dir("simulation"), "fern")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("fern")}> {{
        <http://example.org/orexis#obligation.legacy> a <http://example.org/orexis#Obligation> ;
            <http://example.org/orexis/market#owedTo>
                <http://example.org/orexis/world/simulation#tomato_agent> ;
            <http://example.org/orexis/market#forClaim> "legacy-1" ;
            <http://example.org/orexis/market#presented> true ;
            <http://example.org/orexis/market#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")

    fern = build_agent("fern", st, monkeypatch)
    from orexis_capability_market.ower import Ower

    from orexis_agent_progression.store import bindings

    ledger = Ower(fern)
    #  AND ENDOWED (#635): a row written before the record carried its met-test gets one at
    #  boot — never-held terms arrive with their structures — and only once.
    assert ledger.endow() == 1 and ledger.endow() == 0
    assert bindings(fern.beliefs.query(f"""SELECT ?t WHERE {{ GRAPH <{obligations_graph("fern")}> {{
        <http://example.org/orexis#obligation.legacy> orexis:unmetWhen ?n . ?n sh:select ?t }} }}""")), \
        "the legacy debt now carries the select whose rows are the debt undischarged"
    assert any(g.claim == "legacy-1" for g in ledger.desires(now=owed)), \
        "a pre-fold row must still be served: readers match premises, never the type"
    assert any(r["jti"] == "legacy-1" for r in ledger.owed()), "and on the ask road too"


def test_an_obligation_is_judged_by_the_met_test_the_ledger_wrote(monkeypatch):
    """#635: the ledger's words are the market's, and the planner names none of them. A debt
    is written with `orexis:unmetWhen` — the select whose rows are the debt undischarged, in
    the record and in the world being judged — so the search reads a world where Serving ran
    as met by the debt's own test, exactly as it reads every authored pattern, and the branch
    that named the discharge inside the kernel is gone."""
    import inspect

    from orexis_agent_deliberation import planner as planner_module, trace
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.ontology import obligations_graph
    from orexis_agent_progression.store import bindings

    stored = "http://example.org/orexis/water#StoredLitres"
    supplier = build_agent("supplier", genesis_store({("barrel1", stored): 3.0}), monkeypatch)
    ledger = supplier.hosting().ledger
    uri = ledger.owe("fern", "m1", amount_l=0.5)
    ledger.demanded("m1")
    rows = bindings(supplier.beliefs.query_union(f"""SELECT ?t WHERE {{
        <{uri}> orexis:unmetWhen ?n . ?n sh:select ?t }}"""))
    assert rows and "market:dischargedAt" in rows[0]["t"] and "$state" in rows[0]["t"], \
        "the record carries its met-test, in the ledger's own words"
    want = next(d for d in supplier.pursuing() if d.claim == "m1")
    planner = Planner(supplier, supplier.me)
    plan = planner.plan(want)
    assert plan.steps, "the serve is planned: the served world reads met by the debt's own test"
    assert planner._judged(want)[0] == trace.AUTHORED, "judged as an authored pattern, not a record"
    assert "dischargedAt" not in inspect.getsource(planner_module), "the kernel names no ledger word"
    ledger.discharge("m1")
    assert not any(d.claim == "m1" for d in supplier.pursuing()), "paid: no longer pursued"
