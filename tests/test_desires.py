"""What an agent holds, as its packages contribute it — the split pair and its one join (#234, #298).

`desires.rq` asks the desire modality, `readings.rq` asks the belief modality, and `desires_of`
is the join. It carried MAGNITUDES too — a region want's from the capability answering the choir, an
obligation's fraction of its redeem window in Python — and carries none: a want is judged by
its met-test and nothing scores one by degree. What is pinned here is the STATES, and the
engine limits the arithmetic was written around, which outlive it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox


from orexis_capability_sensing.regions import ObservedWant
from conftest import sensing_of, MOISTURE, TEMPERATURE, build_agent, desires_build, genesis_store
from orexis_agent_progression.ontology import PUBLIC

FERN = "http://example.org/orexis/world/simulation#fern_agent"


def _fern(readings, monkeypatch):
    """A real fern, because a region want's urgency is a capability's answer now: sensing asks
    the choir and sensing answered from its own declaration, so a
    hand-built join would fake away the contribution these tests exercise."""
    st = genesis_store(readings)
    return st, build_agent("fern", st, monkeypatch)


def test_the_query_and_the_module_agree_with_the_diff(query_with_readings, monkeypatch):
    """One definition, three readers. The ranking and the diff both ask the same declared
    measure through the same choir path, so the urgency a desire carries must equal the |gap|
    the diff reports, to the store's own precision.

    Both properties, and both signs: fern below its moisture region and above its temperature
    one. A copy that dropped the sign handling would agree on one of them and not the other.
    """
    _, fern = _fern({("fern", MOISTURE): 0.30, ("fern", TEMPERATURE): 33.0}, monkeypatch)
    desires, diffs = sensing_of(fern).desires(), sensing_of(fern).gaps()

    #  STAKES, which now needs saying: a property carries an epistemic want beside its region,
    #  and a dict keyed on the property alone quietly kept whichever came last. The diff is
    #  about numbers, so the wants it must agree with are the ones about numbers.
    region_wants = {g.observed_property: g for g in desires
              if getattr(g, "observed_property", None) is not None and not g.is_epistemic}
    assert set(region_wants) == set(diffs), "the same wants, whichever text is run"
    #  THE MAGNITUDES NO LONGER MEET, because only one side has one: the want carried a
    #  number the diff had to agree with, and the want carries none. What the two texts must
    #  still agree about is WHICH wants there are, which is the assertion above.


def test_a_want_nobody_has_read_is_the_hottest_goal_and_not_a_missing_one(monkeypatch):
    """Where the two texts deliberately differ, and why it is not a fork.

    `gap.rq` emits NO row for an unmeasured property — a diff needs two sides, and "unmeasured"
    must never read as "satisfied". But it is a GOAL, and the hottest kind: not knowing whether
    the pot is dying is at least as urgent as knowing it is uncomfortable, which is the answer
    `urgency(None)` has always given and the reason the first intention is to look.
    """
    _, fern = _fern({("fern", TEMPERATURE): 21.0}, monkeypatch)  # temperature seen, moisture never
    desires = sensing_of(fern).desires()

    moisture = next(g for g in desires
                    if g.observed_property == MOISTURE and not g.is_epistemic)
    assert moisture.value is None
    assert moisture.state == "unmeasured", \
        "and it says which kind of not-knowing this is — nothing has read it"
    #  NO ORDER TO ASSERT: it sorted to the top and nothing chose by that, since every want
    #  handed up is planned for.
    assert sensing_of(fern).gaps().get(MOISTURE) is None, \
        "while the diff still reports nothing, which is right for a diff"


def test_the_states_a_stake_can_be_in(monkeypatch):
    """met, unmet and unmeasured, asked across the range rather than at one value — a boundary
    that is wrong by one reads correctly at the centre and at the extremes."""
    for value, expected in [(0.55, "met"), (0.45, "met"), (0.65, "met"),
                            (0.30, "unmet"), (0.95, "unmet")]:
        _, fern = _fern({("fern", MOISTURE): value}, monkeypatch)
        #  THE STAKE, named rather than taken first: these came back hottest first, and the
        #  region want about a property sorted ahead of the freshness want about the same one.
        moisture = next(g for g in sensing_of(fern).desires()
                        if g.observed_property == MOISTURE and not g.is_epistemic)
        assert moisture.state == expected, f"{value} should be {expected}"


def test_a_duty_carries_its_timestamps_and_what_the_window_decides(monkeypatch):
    """What is left of the fraction, which is the part anything read.

    A debt carried how much of its redeem window had run — Python, because this store binds
    NOTHING for `duration / duration`, which `test_this_store_still_will_not_divide_one_duration_by_another`
    below still pins. Nothing chose by the number: every want handed up is planned for. What
    the window decides is the STATE and whether the debt may be acted on, asked at the two
    ends, because the ends are what the choice was made about.
    """
    from agent import genesis
    from orexis_agent_progression.ontology import obligations_graph
    stored = "http://example.org/orexis/water#StoredLitres"
    st = genesis_store({("barrel1", stored): 3.0})
    genesis.birth(st, genesis.world_dir("simulation"), "supplier")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("supplier")}> {{
        <http://example.org/orexis#obligation.j1>
            <http://example.org/orexis/market#owedTo>
                <http://example.org/orexis/world/simulation#fern_agent> ;
            <http://example.org/orexis/market#forClaim> "j1" ;
            <http://example.org/orexis/market#presented> true ;
            <http://example.org/orexis/market#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
            <http://example.org/orexis#expiresAt> "{(owed + timedelta(seconds=900)).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")
    supplier = build_agent("supplier", st, monkeypatch)
    ledger = supplier.hosting().ledger
    ledger.endow()
    def duty_at(offset_s):
        #  THE LEDGER'S OWN READ, which hands back its debts and nothing else — no filter,
        #  where the container's merged list needed one to tell a debt from a region want.
        return ledger.desires(now=owed + timedelta(seconds=offset_s))[0]
    assert duty_at(0).state == "demanded" and duty_at(450).state == "demanded"
    assert duty_at(900).state == "lapsed" and duty_at(5000).state == "lapsed"
    assert duty_at(0).pursuable and not duty_at(5000).pursuable, \
        "past the window there is nothing left to spend"


def test_the_gap_is_measured_from_the_aim_and_follows_a_repick_without_a_rebuild(monkeypatch):
    """The finding a-desire-states-its-own-measure records, pinned from the DIFF's side.

    The reflex steered toward the AIM while the magnitude was measured from the region's
    CENTRE, so the two mechanisms pursued different targets whenever the pick sat off-centre.
    The point is read AT ASKING TIME — so moving the aim moves the gap with no desires
    rebuild, which is what a review's re-pick needs, and the scaling stays asymmetric: the
    room below the aim is aim-to-floor, above it aim-to-ceiling, so the same 0.10 out reads
    differently per side. Fern: region 0.45-0.65, survives 0.2-0.85.

    ASKED OF THE DIFF, because that is the one reader left. This was a SPARQL measure the
    choir answered, so a search could ask it of a world nobody was in yet; a search asks a
    want's met-test now, and what still wants a magnitude is what sensing REPORTS.
    """
    from orexis_agent_progression.ontology import picks_graph

    st, fern = _fern({("fern", MOISTURE): 0.55}, monkeypatch)

    def urgency():
        return abs(sensing_of(fern).gaps()[MOISTURE].gap)

    assert urgency() == 0.0, "at the pick (0.55, which is also the centre) nothing is urgent"

    #  The re-pick: the aim moves in the BELIEF BASE alone — the desires store is deliberately
    #  not rebuilt, because the claim under test is that the measure asks, not that a rebuild
    #  recompiles.
    st.update(f"""DELETE {{ GRAPH <{picks_graph("fern")}> {{ ?aim <https://schema.org/value> ?v }} }}
                  INSERT {{ GRAPH <{picks_graph("fern")}> {{ ?aim <https://schema.org/value> 0.65 }} }}
                  WHERE  {{ GRAPH <{picks_graph("fern")}> {{
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
    exactly such a row and asserts the ledger still serves it, on both the desire path and the
    ask path; the day a type-match regrows in `_DUTIES_Q` or `owed`, this goes red.

    AND ENDOWED what the derivation needs (one-function-mints-every-want): a debt written before the
    ledger predicted its lapse predicts nothing, and the derivation derives nothing from it — so
    boot writes the lapse the ledger would write today, once, and asks the derivation."""
    from agent import genesis
    from orexis_agent_progression.ontology import obligations_graph
    stored = "http://example.org/orexis/water#StoredLitres"
    st = genesis_store({("barrel1", stored): 3.0})
    genesis.birth(st, genesis.world_dir("simulation"), "supplier")
    owed = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    st.update(f"""INSERT DATA {{ GRAPH <{obligations_graph("supplier")}> {{
        <http://example.org/orexis#obligation.legacy> a <http://example.org/orexis#Obligation> ;
            <http://example.org/orexis/market#owedTo>
                <http://example.org/orexis/world/simulation#fern_agent> ;
            <http://example.org/orexis/market#forClaim> "legacy-1" ;
            <http://example.org/orexis/market#presented> true ;
            <http://example.org/orexis/market#owedAt> "{owed.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
            <http://example.org/orexis#expiresAt> "{(owed + timedelta(days=400)).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}""")
    supplier = build_agent("supplier", st, monkeypatch)
    from orexis_agent_progression.store import bindings
    ledger = supplier.hosting().ledger
    #  AS BOOT DOES — a built agent is never started, so the endowment is asked for here.
    assert ledger.endow() == 1, "a debt predicting nothing is endowed its lapse"
    assert ledger.endow() == 0, "and only once"
    assert bindings(supplier.beliefs.query_union("""SELECT ?w WHERE {
        <http://example.org/orexis#obligation.legacy> market:lapsesAt ?w }""")), \
        "the legacy debt now predicts its lapse, as one written today would"
    assert any(g.claim == "legacy-1" for g in ledger.desires(now=owed)), \
        "a pre-fold row must still be served: readers match premises, never the type"
    assert any(r["jti"] == "legacy-1" for r in ledger.owed()), "and on the ask path too"


def test_an_obligation_is_judged_by_the_met_test_the_ledger_wrote(monkeypatch):
    """#635: the ledger's words are the market's, and the planner names none of them. The
    host's desire carries a shape the ledger authored — its violations are the debts presented
    or lapsing and not discharged, in the record and in the world being judged — and the want
    the derivation mints under it points at that shape, so the search reads a world where Serving
    ran as met by the ledger's own test, compiled exactly as every shaped want is, and the
    branch that named the discharge inside the kernel is gone."""
    import inspect

    from orexis_agent_deliberation import planner as planner_module, trace
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.ontology import obligations_graph
    from orexis_agent_progression.store import bindings

    stored = "http://example.org/orexis/water#StoredLitres"
    supplier = build_agent("supplier", genesis_store({("barrel1", stored): 3.0}), monkeypatch)
    ledger = supplier.hosting().ledger
    debt = ledger.owe("fern", "m1", amount_l=0.5)
    ledger.demanded("m1")
    #  THE MET-TEST IS THE DESIRE'S, and the want the derivation minted POINTS at it
    #  (one-function-mints-every-want): a `sh:sparql` in the ledger's own words, whose
    #  violation is a debt presented or lapsing and not discharged — so a world where a
    #  serve wrote the discharge reads met. AND IT NAMES NO WORLD (#666).
    want = next(d for d in supplier.wants()
            if any(a.rsplit("#", 1)[-1].rsplit(".", 1)[-1] == "m1" for a in d.about))
    assert want.uri != debt, "the want is the derivation's, not the debt"
    rows = bindings(supplier.beliefs.query_union(f"""SELECT ?t WHERE {{
        <{want.uri}> orexis:metWhen ?shape . ?shape sh:sparql ?c . ?c sh:select ?t }}"""))
    assert rows and all("market:dischargedAt" in r["t"] and "$state" not in r["t"] for r in rows), \
        "the desire carries its met-test, in the ledger's own words"
    planner = Planner(supplier, supplier.me)
    plan = planner.plan(want)
    assert plan.steps, "the serve is planned: the served world reads met by the debt's own test"
    assert planner._judged(want)[0] == trace.COMPILED, \
        "judged by the select compiled from the ledger's shape, not by a kernel branch"
    assert "dischargedAt" not in inspect.getsource(planner_module), "the kernel names no ledger word"
    ledger.discharge("m1")
    assert not any(getattr(d, "claim", None) == "m1" for d in supplier.wants()), \
        "paid: no longer pursued"
