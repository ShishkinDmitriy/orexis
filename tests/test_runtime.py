"""An agent builds itself from its id, and runs exactly what its capabilities name.

These use the real `Agent`, the real world and the real modules — only MQTT and Influx are
stubbed, because they are the two things that would leave the machine.
"""

import pytest

from conftest import build_agent


@pytest.fixture
def agent(monkeypatch):
    return lambda agent_id, ds=None: build_agent(agent_id, ds, monkeypatch)


# --- it loads the modules its hardware implies, and no others --------------

def test_plant_agent_runs_perception_and_bidding(agent):
    assert {m.name for m in agent("fern").modules} == {"subscribing", "bidding", "review"}


def test_supplier_runs_hosting_and_actuation(agent):
    assert {m.name for m in agent("supplier").modules} == {"hosting", "actuation"}


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

def test_a_message_is_handled_by_exactly_one_module(agent, monkeypatch):
    fern = agent("fern")
    seen = []
    for m in fern.modules:
        monkeypatch.setattr(m, "handle", lambda t, p, n=m.name: (seen.append(n), True)[1])
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.2})
    assert len(seen) == 1


def test_an_unrelated_topic_is_ignored(agent):
    fern = agent("fern")
    fern.deliver("something/else", {"value": 0.2})
    assert fern.sent == []


def test_a_module_raising_does_not_kill_the_agent(agent, monkeypatch):
    fern = agent("fern")
    monkeypatch.setattr(fern.modules[0], "handle",
                        lambda t, p: (_ for _ in ()).throw(RuntimeError("boom")))
    fern.deliver(fern.me.sensors[0].reading_topic, {"value": 0.2})  # must not raise
