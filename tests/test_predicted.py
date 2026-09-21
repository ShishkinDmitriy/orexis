"""The keeper tells the predictor the intended branch, and the verdict comes from the
comparison at arrival (#639) — item 3 of the-drift-is-sensings-and-its-result-is-predictions,
held to the code.

A step that predicts a reading holds no shape: the keeper tells `orexis:predicted` the band the
step declared and the instants that frame it, sensing folds that band into the predictions of
the key from the step's landing on, and every reading of the key is compared with it once, at
arrival — in the band, met; outside it at or after the landing, unmet; before the landing,
nothing. The keeper's verdict runs unchanged from there.
"""
from __future__ import annotations

from datetime import timedelta

from orexis_agent_progression import clock
from orexis_agent_progression.act import Step
from orexis_agent_progression.ontology import PLAN_FAILED, PLAN_FINISHED
from orexis_agent_progression.store import bindings
from orexis_capability_actuation.terms import DOSING
from conftest import MOISTURE, build_agent, genesis_store, predicted_reading, reading_of, region_want_of, write_reading
from conftest import ABOUT, VALVE, filled
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import PREDICTION

IN_REGION = "http://example.org/orexis/sensing#InRegion"
BELOW = "http://example.org/orexis/sensing#BelowRegion"


def _gardener(monkeypatch, moisture=0.05):
    """The loner's gardener, its pot under the floor of 0.10, with a pump of its own."""
    return build_agent("gardener", genesis_store({("zz", MOISTURE): moisture}, world="loner"), monkeypatch)


def _two_doses(agent, band: str = BELOW):
    """A two-step plan adopted by hand — a dose, then a dose — standing at the first, each
    step predicting the pot's reading to be `band`."""
    pump = bindings(agent.beliefs.query(
        f"SELECT ?p WHERE {{ <{agent.me.uri}> actuation:hasActuator ?p }}", agent.beliefs.graphs_of(PUBLIC)))[0]["p"]
    want = region_want_of(agent).uri
    #  Each step carries what it predicts, as a search-made one does: a small dose that leaves
    #  the pot below its floor — so the actor taking the second can open a watch on it.
    dose = Step(action=DOSING, binding=filled((VALVE, pump), (ABOUT, MOISTURE)), want=want, quantity=0.2,
                predicts=predicted_reading(agent.me.acts_for, MOISTURE, band=band))
    return agent.keeper.adopt([dose, dose], want, "two doses, the search's plan"), want


def _told(agent, monkeypatch) -> list:
    heard = []
    monkeypatch.setattr(agent, "tell", lambda point, *a, **kw: heard.append(point))
    return heard


def _bands_at(agent, seconds_ahead: float) -> set:
    """The families the prediction holding that far ahead types the pot's reading with."""
    at = clock.now() + timedelta(seconds=seconds_ahead)
    out = set()
    for graph in agent.beliefs.graphs_of(PREDICTION, at=at):
        out |= {r["t"] for r in bindings(agent.beliefs.query(f"""
SELECT ?t WHERE {{ GRAPH <{graph}> {{ ?o sosa:observedProperty <{MOISTURE}> ; a ?t }} }}""", agent.beliefs.graphs_of(PUBLIC)))}
    return out


def test_a_step_predicting_a_reading_holds_no_shape_and_the_predictor_is_told(monkeypatch):
    """No SHACL shape is built per step and nothing is held: the keeper's `predicted()` lists
    the branch it told — the band, and the three instants that frame the comparison."""
    agent = _gardener(monkeypatch)
    uri, _ = _two_doses(agent, IN_REGION)
    assert agent.keeper.expect(uri, "the first dose", baseline=reading_of(agent, MOISTURE),
                               lands_after_s=3600.0)
    assert agent.keeper.held() == [], "no hold: the comparison is the predictor's"
    told = agent.keeper.predicted()
    assert len(told) == 1 and told[0].intention == uri and told[0].bands == {IN_REGION}
    assert told[0].since < told[0].lands_at <= told[0].not_after
    assert abs((told[0].lands_at - clock.now()).total_seconds() - 3600.0) < 5.0


def test_a_reading_in_the_band_after_the_landing_advances_the_plan(monkeypatch):
    """Met: the first dose predicted the pot still below its floor — a small one — and once it
    has landed the pot reads so. The watch closes met and, the want still unmet, the
    intention advances to the second dose, no search asked (a reading that met the want
    would finish the plan instead, #521)."""
    agent = _gardener(monkeypatch)
    uri, want = _two_doses(agent)
    assert agent.keeper.expect(uri, "the first dose", baseline=reading_of(agent, MOISTURE),
                               lands_after_s=0.0, seeing_s=600.0)
    first = agent.keeper.predicted()[0].step
    write_reading(agent, 0.08, MOISTURE)
    assert all(w.step != first for w in agent.keeper.open_expectations()), "the first watch closed"
    assert agent.keeper.reports()["expectations_met"] == 1
    standing = [s for s in agent.keeper.standing(want=want) if s.uri == uri]
    assert standing and len(agent.keeper.walked(uri)) == 2, "advanced to the second dose, and it was taken"


def test_a_reading_outside_the_band_after_the_landing_drops_the_tail(monkeypatch):
    """Unmet, at the reading and not at the deadline: the dose has landed and the pot still
    reads below — the tail is dropped and deliberation hears the plan fail."""
    agent = _gardener(monkeypatch)
    uri, _ = _two_doses(agent, IN_REGION)
    assert agent.keeper.expect(uri, "the first dose", baseline=reading_of(agent, MOISTURE),
                               lands_after_s=0.0, seeing_s=600.0)
    heard = _told(agent, monkeypatch)
    write_reading(agent, 0.06, MOISTURE)
    assert agent.keeper.open_expectations() == []
    assert agent.keeper.reports()["expectations_unmet"] == 1
    assert agent.keeper.standing() == [], "the tail is dropped"
    assert PLAN_FAILED in heard and PLAN_FINISHED not in heard


def test_a_reading_before_the_landing_says_nothing_of_the_step(monkeypatch):
    """The dose is still pouring: a reading outside the band is the world's own branch, not
    the step failing, and the watch stays open."""
    agent = _gardener(monkeypatch)
    uri, _ = _two_doses(agent, IN_REGION)
    assert agent.keeper.expect(uri, "the first dose", baseline=reading_of(agent, MOISTURE),
                               lands_after_s=3600.0)
    write_reading(agent, 0.06, MOISTURE)
    assert len(agent.keeper.open_expectations()) == 1
    assert agent.keeper.reports()["expectations_unmet"] == 0


def test_the_predictions_show_the_intended_branch_while_the_step_stands_and_the_drift_after(monkeypatch):
    """What the sovereign reads: from the landing on, the prediction of the pot is the step's
    band; before it, the drift's own. The watch lapsing gives the drift's back everywhere."""
    agent = _gardener(monkeypatch)
    assert BELOW in _bands_at(agent, 2 * 3600.0), "the drift's own branch: below, and staying so"
    uri, _ = _two_doses(agent, IN_REGION)
    assert agent.keeper.expect(uri, "the first dose", baseline=reading_of(agent, MOISTURE),
                               lands_after_s=3600.0)
    assert IN_REGION in _bands_at(agent, 2 * 3600.0) and BELOW not in _bands_at(agent, 2 * 3600.0), \
        "past the landing the prediction is the step's band"
    #  Inside the first window past the next reading's due — no prediction holds between a
    #  reading and the instant the next is due, which is the window's own start.
    assert BELOW in _bands_at(agent, 700.0) and IN_REGION not in _bands_at(agent, 700.0), \
        "before it, the drift's"
    agent.keeper.lapse(uri)
    assert agent.keeper.open_expectations() == []
    assert BELOW in _bands_at(agent, 2 * 3600.0) and IN_REGION not in _bands_at(agent, 2 * 3600.0), \
        "the watch closed: the world's own branch again"
