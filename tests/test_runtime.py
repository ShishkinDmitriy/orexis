"""An agent builds itself from its id, and runs exactly what its capabilities name.

These use the real `Agent`, the real world and the real modules — only MQTT and Influx are
stubbed, because they are the two things that would leave the machine.
"""

import logging

import pytest

from conftest import build_agent


@pytest.fixture
def agent(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


# --- it loads the modules its hardware implies, and no others --------------

def test_plant_agent_runs_perception_and_bidding(agent):
    """`reporting` is in every one of these sets, because every agent is granted it.

    `desire` is in this one because fern acts for a plant that states what it needs — a stake,
    not a wire and not a market position. The supplier below has none and runs no desire module,
    which is the same distinction from the other side.
    """
    assert {m.name for m in agent("fern").modules} == {
        "subscribing", "bidding", "desire", "intention", "review", "reporting"}


def test_supplier_runs_hosting_actuation_and_matching(agent):
    """Three abilities of its own: it runs the protocol, it opens valves, and it knows one way of
    turning bids into an allocation. Hosting reaches the third through `agent.provider`, so the
    market package never learns that pay-as-bid is implemented in Python.

    And `reporting`, which it did not earn — every agent is granted that one.
    """
    assert {m.name for m in agent("supplier").modules} == {
        "hosting", "actuation", "pay-as-bid", "reporting"}


def test_the_supplier_has_no_perception(agent):
    """It is wired to no sensor, so it neither polls nor listens — and is never asked to."""
    supplier = agent("supplier")
    assert not any(m.name in ("subscribing", "listening") for m in supplier.modules)
    assert supplier.me.sensors == ()


def test_a_plant_agent_holds_no_actuator(agent):
    """Winning water is not being able to open a valve."""
    assert agent("fern").me.actuators == ()


# --- every topic it touches came from the graph ----------------------------

def test_subscribes_its_own_sensor_and_market_channels(agent):
    fern = agent("fern")
    market = fern.me.markets[0]
    assert set(fern.subscribed) == {
        fern.me.sensors[0].reading_topic,
        market.offer_topic,
        f"{market.voucher_topic}/fern",
    }


def test_never_subscribes_a_wildcard_sensor(agent):
    """The access grant is visible in the subscription: its own sensor, nobody else's."""
    for agent_id in ("fern", "tomato", "succulent"):
        a = agent(agent_id)
        assert not any(t.startswith("sensors/+") or t.startswith("sensors/#")
                       for t in a.subscribed)


def test_host_subscribes_its_participants_and_bid_channel(agent):
    supplier = agent("supplier")
    market = supplier.me.hosted_markets[0]
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

    Exactly the defect #51 fixed one level down, where `PerceptionModule.handle` returned
    after the first SENSOR owning a topic and a board's second channel went unread. The
    module-level version stayed because nothing yet wanted one topic twice. #36 wants it:
    actuation subscribes to its valves' status, and a supplier runs actuation beside hosting.

    `reading_recorded` immediately above already offers to every module. This is that.
    """
    fern = agent("fern")
    seen = []
    for m in fern.modules:
        monkeypatch.setattr(m, "handle", lambda t, p, n=m.name: (seen.append(n), True)[1])
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.2})
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
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.2})  # must not raise
