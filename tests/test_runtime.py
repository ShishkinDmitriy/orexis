"""An agent builds itself from its id, and runs exactly what its capabilities name.

These use the real `Agent`, the real world and the real modules — only MQTT and Influx are
stubbed, because they are the two things that would leave the machine.
"""

import logging

import pytest

from conftest import build_agent, wired_actuators, wired_hosted_markets, wired_markets, wired_sensors


@pytest.fixture
def agent(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


# --- it loads the modules its hardware implies, and no others --------------

def test_plant_agent_runs_sensing_and_bidding(agent):
    """`reporting` is in every one of these sets, because every agent is granted it.

    `desire` is in this one because fern acts for a plant that states what it needs — a stake,
    not a wire and not a market position. The supplier gained the same the day it started
    acting for its barrel — the distinction is the stake, not which side of the market.
    """
    #  `intention`, `deliberation` and `owing` are the MIND, which every agent has: they are
    #  the kernel's, granted by nothing. (`desire` was among them until the region and the aim
    #  went to sensing — the-stake-is-sensings-want.) What is fern's own is `subscribing` (a
    #  scheduled board), `bidding` (a market position), `review` (latitude) and `reporting`.
    assert {m.name for m in agent("fern").modules} == {
        "subscribing", "bidding", "review", "reporting",
        "intention", "deliberation", "owing"}


def test_supplier_runs_the_dealers_full_stack(agent):
    """Its original three (protocol, valves, matching), plus what the barrel arcs earned it:
    listening (arc 1 — it watches its stock), since the stake (arc 2) desire, intention and
    deliberation — because acting for a barrel that states its needs is a stake, and the
    valves it always held are means, and stake plus means is the premise Keeping and Reflex
    share — and since the city exists (arc 4), BIDDING: the dealer buys upstream at one venue
    and sells downstream at another, hosting and bidding in one process, and its reflex
    proposes now because the refill venue carries a direction for StoredLitres.

    And `reporting`, which it did not earn — every agent is granted that one.
    """
    assert {m.name for m in agent("supplier").modules} == {
        "hosting", "actuation", "pay-as-bid", "reporting", "listening",
        # `owing` beside `desire` and not inside it (#233): the ledger is granted by a lever
        # others may demand, the region by a stake, and the supplier is the agent that has both.
        # `deliberation` is the KERNEL's and every agent has it, so it appears here for the
        # same reason it appears in every other agent's list. Arc 5's `planning` does not:
        # the planner was a member that subclassed the reflex and added one clause inert for
        # everyone else, so it is a clause and not a module. What it protects is pinned in
        # test_deliberation, against the fact rather than against who was handed which module.
        "owing", "intention", "deliberation", "bidding"}


def test_the_supplier_listens_to_its_stock_and_schedules_nothing(agent):
    """Since the barrel learned to run dry, the supplier polls its level sensor — a push
    device, so it derives Listening and only Listening: it commands no cadence, because a
    float announces and is not asked. The stake (arc 2) and the lever (arc 4) both arrived
    since; what this still guards is the clock — a dealer with a full stack still may not
    order a float around."""
    supplier = agent("supplier")
    assert any(m.name == "listening" for m in supplier.modules)
    assert not any(m.name == "subscribing" for m in supplier.modules)
    assert [s.local_id for s in wired_sensors(supplier)] == ["barrel1_level"]


def test_a_plant_agent_holds_no_actuator(agent):
    """Winning water is not being able to open a valve."""
    assert wired_actuators(agent("fern")) == ()


# --- every topic it touches came from the graph ----------------------------

def test_subscribes_its_own_sensor_and_market_channels(agent):
    from agent import sovereign

    fern = agent("fern")
    market = wired_markets(fern)[0]
    assert set(fern.subscribed) == {
        wired_sensors(fern)[0].reading_topic,
        market.offer_topic,
        f"{market.claim_topic}/fern",
        # its own question channel and nobody else's — the one topic the world does not
        # state, single-sourced in agent/sovereign.py and granted by the ACL to one asker
        sovereign.query_topic("fern"),
    }


def test_never_subscribes_a_wildcard_sensor(agent):
    """The access grant is visible in the subscription: its own sensor, nobody else's."""
    for agent_id in ("fern", "tomato", "succulent"):
        a = agent(agent_id)
        assert not any(t.startswith("sensors/+") or t.startswith("sensors/#")
                       for t in a.subscribed)


def test_host_subscribes_its_participants_and_bid_channel(agent):
    supplier = agent("supplier")
    market = wired_hosted_markets(supplier)[0]
    assert f"{market.bid_topic}/+" in supplier.subscribed
    # it listens to what participants announce, which is how scarcity reaches it
    assert "readings/fern" in supplier.subscribed
    assert "readings/tomato" in supplier.subscribed


# --- routing ---------------------------------------------------------------

def test_a_message_is_offered_to_every_module(agent, monkeypatch):
    """One message, every module that wants it — not the first one that speaks up.

    This test used to assert `len(seen) == 1`, which was the defect written down as the
    contract. `_on_message` returned as soon as a module's `handle` came back true, so a
    second module subscribed to the same topic never saw the message at all.

    Exactly the defect #51 fixed one level down, where `SensingModule.handle` returned
    after the first SENSOR owning a topic and a board's second channel went unread. The
    module-level version stayed because nothing yet wanted one topic twice. #36 wants it:
    actuation subscribes to its valves' status, and a supplier runs actuation beside hosting.

    `reading_recorded` immediately above already offers to every module. This is that.
    """
    fern = agent("fern")
    seen = []
    for m in fern.modules:
        monkeypatch.setattr(m, "handle", lambda t, p, n=m.name: (seen.append(n), True)[1])
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.2})
    assert len(seen) == len(fern.modules), f"only {seen} were offered it"


def test_a_module_that_claims_a_topic_does_not_silence_the_next(agent, monkeypatch):
    """The narrow case, stated on its own because it is the one that bit.

    The FIRST module claims and the SECOND is the one with work to do. Under the old loop the
    second is never called, and nothing anywhere says so — the message is simply gone.
    """
    fern = agent("fern")
    first, second = fern.modules[0], fern.modules[1]
    monkeypatch.setattr(first, "handle", lambda t, p: True)
    reached = []
    monkeypatch.setattr(second, "handle", lambda t, p: (reached.append(t), True)[1])
    fern.deliver("shared/channel", {})
    assert reached, "the first module claiming the topic hid it from the second"


def test_the_unhandled_warning_still_fires_only_when_nobody_took_it(agent, monkeypatch, caplog):
    """A regression guard rather than a failing test: unchanged by the fix, and worth holding.

    The warning is what makes a topic disagreement visible — the world names one channel, the
    device publishes on another, both ends look healthy. Offering the message to everyone must
    not turn `handled` into "somebody was asked", which would silence it forever.
    """
    fern = agent("fern")
    for m in fern.modules:
        monkeypatch.setattr(m, "handle", lambda t, p: False)
    with caplog.at_level(logging.WARNING):
        fern.deliver("nobody/wants/this", {})
    assert "nothing handled a message" in caplog.text

    caplog.clear()
    monkeypatch.setattr(fern.modules[0], "handle", lambda t, p: True)
    with caplog.at_level(logging.WARNING):
        fern.deliver("somebody/wants/this", {})
    assert "nothing handled a message" not in caplog.text


def test_an_unrelated_topic_is_ignored(agent):
    fern = agent("fern")
    fern.deliver("something/else", {"value": 0.2})
    assert fern.sent == []


def test_a_module_raising_does_not_kill_the_agent(agent, monkeypatch):
    fern = agent("fern")
    monkeypatch.setattr(fern.modules[0], "handle",
                        lambda t, p: (_ for _ in ()).throw(RuntimeError("boom")))
    fern.deliver(wired_sensors(fern)[0].reading_topic, {"moisture": 0.2})  # must not raise


def test_the_agent_holds_a_clean_session():
    """Arrival-stamped freshness is sound only while delivery is immediate.

    The boards have no clocks, so a reading's instant is stamped when it ARRIVES — and a
    persistent MQTT session breaks that silently: the broker queues everything missed during
    downtime and replays it on reconnect, each stale reading stamped fresh at arrival, the
    ignorance burst suppressed because the agent "already knows", and the trend computed from
    replay intervals rather than real ones. "Don't lose readings while the agent is down"
    sounds like reliability and converts an honest blindness into a confident lie — so the
    clean session is an invariant, not a default someone forgot to change.

    Guarded at the source in two halves, because `build_agent` stubs the client and the flag
    is unobservable through it: the runtime must not ask for a persistent session, and paho's
    default — which the runtime therefore inherits — must still be clean. If paho ever flips
    its default, the second half fails and forces the look this comment exists for.
    """
    import inspect

    import paho.mqtt.client as paho

    from agent import runtime

    source = inspect.getsource(runtime)
    assert "clean_session" not in source, \
        "runtime.py mentions clean_session — if it sets False, every freshness judgment lies"
    real = paho.Client(paho.CallbackAPIVersion.VERSION2)
    assert getattr(real, "_clean_session", None) is True, \
        "paho's default session is no longer clean — the runtime must now say so explicitly"
