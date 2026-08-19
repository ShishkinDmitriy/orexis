"""The Actuate rung (#190): direct, no market — honest exactly where both chains are mine.

The ladder's second rung, last to be built, first new KIND of move to arrive as a package's
own menu branch (#207's recorded first customer). The world that exercises it is
`world/loner`: one gardener, one Zamioculcas planted by one triple, one pump on one rain
butt, and no market anywhere — the demonstration that every rung of wanting, watching,
deciding, committing and acting runs with no economy at all.
"""

import pytest

from packages.capability.deliberation import menu_of
from packages.capability.deliberation.module import ACTUATE, ACQUIRE, OBSERVE

from conftest import build_agent, genesis_store

MOIST = "http://example.org/agora/water#SoilMoisture"
GARDENER = "http://example.org/agora/world/loner#gardener"
_DELIBERATION = "http://example.org/agora/deliberation#DeliberationCapability"


@pytest.fixture
def make(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


@pytest.fixture
def gardener(make, tmp_path, monkeypatch):
    from onboarding.keygen import create_keypair

    monkeypatch.setenv("AGORA_WORLD_DIR", str(tmp_path))
    (tmp_path / "secrets").mkdir()
    for name in ("host", "clearing"):
        create_keypair(name)
    return make("gardener", genesis_store(world="loner"))


# --- the menu's second rung -------------------------------------------------

def test_the_menu_offers_actuate_where_both_chains_are_mine():
    """Lever chain: my pump, plumbed to my pot. Resource chain: drawing from a source that is
    mine and that no market offers as its lot. Both end at the gardener, so the rung appears —
    beside Observe, with the domain's one stated physics atom as its direction."""
    rows = menu_of(genesis_store(world="loner").query, GARDENER)
    assert [(r.means.rsplit("#", 1)[-1], r.direction and r.direction.rsplit("#", 1)[-1])
            for r in rows if r.observed_property == MOIST] == [
        ("Actuate", "Raises"), ("Observe", None)]


def test_opening_a_shop_on_your_own_bottle_costs_you_the_free_rung():
    """The cut-source pin, from the loner's side: state market:matchesBy on the gardener —
    consent, a shop on the butt — re-derive, and the venue exists, so the butt is a source a
    market offers and the Actuate row vanishes. The market is about the resource: once it is
    a lot, even its owner's own pump answers to the venue."""
    from agent import genesis, loader
    from agent.ontology import WORLD_DERIVED_GRAPH, WORLD_GRAPH

    st = genesis_store(world="loner")
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{GARDENER}> <http://example.org/agora/market#matchesBy>
            <http://example.org/agora/market#PayAsBid> }} }}""")
    st.clear_graph(WORLD_DERIVED_GRAPH)
    for rule in loader.rule_files():
        st.update(genesis.substitute(rule.read_text(), st))
    rows = menu_of(st.query, GARDENER)
    assert not any(r.means == ACTUATE for r in rows), \
        "a source a market offers is not yours to open free, whoever holds the pump"


def test_a_pot_local_pump_on_the_shared_barrel_still_yields_acquire_only():
    """The other side of the same rule, in the market world: give fern its own pump drawing
    from the SHARED barrel, and the menu must offer Acquire and only Acquire — a lever you
    own on a resource you do not is exactly what the market referees."""
    from agent.ontology import WORLD_GRAPH

    ns = "http://example.org/agora/world/simulation#"
    st = genesis_store()
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{ns}fern_agent> <http://example.org/agora/actuation#hasActuator> <{ns}fern_pump> .
        <{ns}fern_pump> <http://example.org/agora/actuation#actuates> <{ns}fern> ;
            <http://example.org/agora/actuation#drawsFrom> <{ns}barrel1> .
    }} }}""")
    rows = [r for r in menu_of(st.query, ns + "fern_agent")
            if r.observed_property == MOIST]
    assert any(r.means == ACQUIRE for r in rows)
    assert not any(r.means == ACTUATE for r in rows), \
        "owning the pump does not exempt anyone from the auction when the water is common"


# --- the reflex prefers the cheaper rung ------------------------------------

def test_the_reflex_proposes_actuate_below_the_aim(gardener):
    deliberator = gardener.provider(_DELIBERATION)
    assert deliberator.propose(MOIST, 0.10) == ACTUATE
    assert deliberator.propose(MOIST, 0.25) is None, "above the aim, nothing — as ever"
    assert deliberator.propose(MOIST, None) == OBSERVE


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
    watches = keeper.open_expectations(MOIST)
    assert len(watches) == 1 and watches[0].expected_delta == pytest.approx(0.08)


def test_an_unanswered_self_dose_blocks_the_next(gardener):
    """The #167 guard on rung 2: while my own dose has not answered, no reading I hold can
    prove the pot was not already watered — so a second low look inside the watch commands
    nothing. One impulse, one dose, however often the probe reports the same thirst."""
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.11})
    assert len(gardener.sent.to("actuators/pump/command")) == 1


def test_the_gardener_derives_no_market_pair():
    """The world's whole claim, as a capability set: stake, sight, lever, memory, reflex —
    and no Bidding, no Hosting, because nothing here is anyone else's."""
    from agent.world import load_self

    caps = {c.rsplit("#", 1)[-1] for c in
            load_self(genesis_store(world="loner").query, "gardener").capabilities}
    assert caps == {"Subscribing", "Listening", "Storing", "Keeping", "Deducing", "Reflex",
                    "Actuation"}, "both clocks in one agent since the butt got its witness"


# --- the 584-dose morning (patience reads the ledger; the butt is metered) --

def test_a_satisfied_actuate_still_absorbs_the_next_impulse(gardener, monkeypatch):
    """The flood, pinned: Actuate is adopted and satisfied within milliseconds, so the
    standing-only patience check absorbed nothing and the gardener pulsed its pump every
    second reading, all night — 584 doses. Patience asks the LEDGER now, any outcome: a
    recently satisfied impulse to do the same thing is the same impulse."""
    keeper = next(m for m in gardener.modules if m.name == "intention")
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert len(gardener.sent.to("actuators/pump/command")) == 1
    monkeypatch.setattr(keeper, "open_expectations", lambda p: [])  # the watch out of the way
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert len(gardener.sent.to("actuators/pump/command")) == 1, \
        "the ledger remembers what the standing list forgot"
    assert keeper.within_patience(
        "http://example.org/agora#Actuate", MOIST)


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
