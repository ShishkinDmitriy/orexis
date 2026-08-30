"""The Actuate rung (#190): direct, no market — honest exactly where both chains are mine.

The ladder's second rung, last to be built, first new KIND of move to arrive as a package's
own menu branch (#207's recorded first customer). The world that exercises it is
`world/loner`: one gardener, one Zamioculcas planted by one triple, one pump on one rain
butt, and no market anywhere — the demonstration that every rung of wanting, watching,
deciding, committing and acting runs with no economy at all.
"""

import pytest

from orexis_deliberation.afforder import affordances_of
from orexis_capability_market.terms import ACQUIRING
from orexis_capability_actuation.terms import DOSING
from orexis_capability_sensing.terms import OBSERVING

from orexis_progression.ontology import beliefs_graph
from orexis_capability_sensing.regions import ObservedDesire
from conftest import sensing_of, stake_of, build_agent, genesis_store, desires_build, open_round_for, write_reading

MOIST = "http://example.org/orexis/water#SoilMoisture"
GARDENER = "http://example.org/orexis/world/loner#gardener"


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


@pytest.fixture
def gardener(make, tmp_path, monkeypatch):
    from onboarding.keygen import create_keypair

    monkeypatch.setenv("OREXIS_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    return make("gardener", genesis_store(world="loner"))


# --- the menu's second rung -------------------------------------------------

def test_the_menu_offers_actuate_where_both_chains_are_mine():
    """Lever chain: my pump, plumbed to my pot. Resource chain: drawing from a source that is
    mine and that no market offers as its lot. Both end at the gardener, so the rung appears —
    beside Observe, with the domain's one stated physics atom as its direction."""
    st = genesis_store(world="loner")
    rows = affordances_of(st.query, GARDENER, desires_build(st, "gardener").query_union, beliefs_graph("gardener"))
    assert [(r.action.rsplit("#", 1)[-1], r.direction and r.direction.rsplit("#", 1)[-1])
            for r in rows if r.about == MOIST] == [
        ("Dosing", "Raises"), ("Observing", None)]


def test_opening_a_shop_on_your_own_bottle_costs_you_the_free_rung():
    """The cut-source pin, from the loner's side: state market:matchesBy on the gardener —
    consent, a shop on the butt — re-derive, and the venue exists, so the butt is a source a
    market offers and the Actuate row vanishes. The market is about the resource: once it is
    a lot, even its owner's own pump answers to the venue."""
    from agent import genesis
    from assembly import loader
    from orexis_progression.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH

    st = genesis_store(world="loner")
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{GARDENER}> <http://example.org/orexis/market#matchesBy>
            <http://example.org/orexis/market#PayAsBid> }} }}""")
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        st.update(genesis.substitute(rule.read_text(), st))
    rows = affordances_of(st.query, GARDENER, desires_build(st, "gardener").query_union, beliefs_graph("gardener"))
    assert not any(r.action == DOSING for r in rows), \
        "a source a market offers is not yours to open free, whoever holds the pump"


def test_a_pot_local_pump_on_the_shared_barrel_still_yields_acquire_only():
    """The other side of the same rule, in the market world: give fern its own pump drawing
    from the SHARED barrel, and the menu must offer Acquire and only Acquire — a lever you
    own on a resource you do not is exactly what the market referees."""
    from orexis_progression.ontology import WORLD_GRAPH

    ns = "http://example.org/orexis/world/simulation#"
    st = genesis_store()
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{ns}fern_agent> <http://example.org/orexis/actuation#hasActuator> <{ns}fern_pump> .
        <{ns}fern_pump> <http://example.org/orexis/actuation#actuates> <{ns}fern> ;
            <http://example.org/orexis/actuation#drawsFrom> <{ns}barrel1> .
    }} }}""")
    open_round_for(st, "fern")
    rows = [r for r in affordances_of(st.query, ns + "fern_agent", desires_build(st, "fern").query_union, beliefs_graph("fern"))
            if r.about == MOIST]
    assert any(r.action == ACQUIRING for r in rows)
    assert not any(r.action == DOSING for r in rows), \
        "owning the pump does not exempt anyone from the auction when the water is common"


# --- the cheaper rung is the one the search finds ---------------------------

def test_a_dose_is_proposed_below_the_aim_and_nothing_above_it(gardener):
    """The gardener owns its pump, so the move it reaches for is its own valve rather than a
    venue — the ladder's preference, arrived at by simulation instead of by a rung table.

    It used to be asked of the bare-value door, which sorted the menu cheapest-rung-first and
    took the first row whose stated direction matched the gap's sign. That door is gone: the
    rung a plan takes is the one whose predicted world scores best, and above the aim every
    world a dose reaches is worse than standing still.
    """
    from orexis_deliberation.desire import Desire

    deliberator = gardener.deliberator
    #  The world holds the value; the want does not. Written OLD, so the freshness want the
    #  tail of this test asks about is still unmet — a stake judges the number it has.
    write_reading(gardener, 0.10, MOIST, age_s=10_000)
    assert deliberator.propose_for(
        ObservedDesire(uri=stake_of(gardener, MOIST).uri, urgency=0.6, observed_property=MOIST,
                     value=0.10)) == DOSING
    write_reading(gardener, 0.30, MOIST, age_s=10_000)
    assert deliberator.propose_for(
        ObservedDesire(uri=stake_of(gardener, MOIST).uri, urgency=0.1, observed_property=MOIST,
                     value=0.25)) is None, \
        "above the aim, nothing — as ever"
    #  NOT SEEING is answered by the search like everything else, and it is a different WANT
    #  rather than a state this one is in. It used to be asserted of a made-up desire carrying
    #  `state="unmeasured"`, which the deliberator read before any search ran; there is no such
    #  branch now, so the question has to be asked of the want that actually means it — the
    #  agent's own freshness want for the probe, which no reading has yet answered. A made-up
    #  region want with no reading correctly gets NOTHING: looking does not put a number
    #  inside a region, and nothing else the gardener holds moves a number it cannot see.
    epistemic = next(d for d in gardener.pursuing()
                     if d.is_epistemic and d.observed_property == MOIST)
    assert deliberator.propose_for(epistemic) == OBSERVING
    assert deliberator.propose_for(sensing_of(gardener).want_about(MOIST)) == OBSERVING, \
        "and the actors' door says the same while the reading is missing — look, then dose"


# --- the self-dose: signed, confirmed, ledgered, watched --------------------

def test_a_self_dose_is_commanded_co_signed_and_ledgered(gardener):
    """The executor path for a dose that fulfils no claim: the reading arrives low, the
    deliberator says Actuate, the dose is sized from the deficit and the agent's own
    conversion belief, and it goes out through the SAME redeem the market path uses —
    co-signed, replay-protected, awaiting the device's confirmation. The keeper holds the
    whole story: Actuate adopted with the reason, satisfied at the command, and an
    expectation open for the effect — an unconfirmed self-dose is not a delivered one."""
    from agent.signing import verify_command

    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    sent = gardener.sent.to("actuators/pump/command")
    assert len(sent) == 1
    cmd = sent[0]
    assert cmd["ml"] == 120.0, "deficit 0.08 x 1.5 L per fraction = 120 ml"
    actuation = next(m for m in gardener.modules if m.name == "actuation")
    assert verify_command(cmd, actuation.host_key.public_key(),
                          actuation.clearing_key.public_key())

    keeper = next(m for m in gardener.modules if m.name == "intention")
    watches = keeper.open_expectations(stake_of(gardener, MOIST).uri)
    assert len(watches) == 1 and watches[0].expected_delta == pytest.approx(0.08)


def test_an_unanswered_self_dose_blocks_the_next(gardener):
    """The #167 guard on rung 2: while my own dose has not answered, no reading I hold can
    prove the pot was not already watered — so a second low look inside the watch commands
    nothing. One impulse, one dose, however often the probe reports the same thirst."""
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.11})
    assert len(gardener.sent.to("actuators/pump/command")) == 1


def test_the_gardener_derives_no_market_pair():
    """The world's whole claim, as a capability set: stake, sight, lever, memory — and no
    Bidding, no Hosting, because nothing here is anyone else's.

    `Reflex`, `Keeping` and `Deducing` were in this set and are not capabilities any more:
    deciding, committing and wanting are the kernel's, granted by nothing, because a mind is
    not plug-in-able. What the gardener DELIBERATES is
    unchanged and is tested elsewhere; what this asserts is only what its world grants it."""
    from agent.world import load_self

    caps = {c.rsplit("#", 1)[-1] for c in
            load_self(genesis_store(world="loner").query, "gardener").capabilities}
    assert caps == {"Subscribing", "Listening", "Storing",
                    "Actuation", "Linking"}, "both clocks in one agent since the butt got its witness"


# --- the 584-dose morning (patience reads the ledger; the butt is metered) --

def test_a_dose_in_flight_absorbs_the_next_impulse(gardener, monkeypatch):
    """The flood, pinned: Actuate is adopted and satisfied within milliseconds, so the
    standing-only patience check absorbed nothing and the gardener pulsed its pump every
    second reading, all night — 584 doses. The intention is to the END now (#353): it stands
    from the command until the watch is judged, and while it stands `adopt` absorbs the next
    impulse by the ordinary rule — no hook, no second read of the ledger."""
    keeper = next(m for m in gardener.modules if m.name == "intention")
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert len(gardener.sent.to("actuators/pump/command")) == 1
    monkeypatch.setattr(keeper, "open_expectations", lambda p: [])  # the watch out of the way
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert len(gardener.sent.to("actuators/pump/command")) == 1, \
        "the dose in flight is a commitment, and a commitment absorbs the same impulse"
    assert keeper.standing(action="http://example.org/orexis/actuation#Dosing",
                           want=stake_of(gardener, MOIST).uri), "it STANDS until the world answers"


def test_the_dose_is_capped_by_what_the_vessel_holds(gardener):
    """The witness meters rung 2 as it meters the host's rounds: the sized dose wants
    120 ml, the butt holds 50 ml, the pump gets 50."""
    gardener.deliver("sensors/butt_level/reading", {"value": 0.05})
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    sent = gardener.sent.to("actuators/pump/command")
    assert len(sent) == 1 and sent[0]["ml"] == 50.0


def test_a_spent_vessel_refuses_the_dose_and_says_so(gardener, caplog):
    """The other 584-dose finding: self-claims never meet clearing's allocation ledger, so
    without a witness the capacity bounded nothing. With one, a spent butt refuses — the
    wanting continues, the means is gone, and the log says exactly that."""
    import logging

    gardener.deliver("sensors/butt_level/reading", {"value": 0.0})
    with caplog.at_level(logging.WARNING):
        gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert gardener.sent.to("actuators/pump/command") == []
    assert "the vessel is spent" in caplog.text
