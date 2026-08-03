"""ag:Polling — attention as the agent's own decision, bounded by the constitution.

The cadence policy, the two levers (retained cadence vs best-effort nudge), and the verdict
an agent reaches about itself. Driven through a real agent, so the numbers come from the
agent's own beliefs and the bounds from the ontology — neither is written down here.
"""

from dataclasses import replace

import pytest

from conftest import build_agent, genesis_dataset


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_dataset(), monkeypatch)


def sensor_of(agent):
    return agent.me.sensors[0]


def cadences(agent):
    """Every cadence the agent has commanded, in order."""
    return [p["sleep_s"] for p in agent.sent.to(sensor_of(agent).command_topic)
            if "sleep_s" in p]


# --- the policy ------------------------------------------------------------

def test_it_watches_closely_when_thirsty(fern):
    p = fern.polling()
    assert p.cadence_for(0.35) == 30  # at its own low band -> its fastest
    assert p.cadence_for(0.65) == 600  # at its high band -> its slowest


def test_attention_scales_with_trouble(fern):
    p = fern.polling()
    assert p.cadence_for(0.40) < p.cadence_for(0.60)


def test_the_bounds_come_from_the_ontology_not_the_code(fern):
    """MIN/MAX are stated in ontology/polling.ttl and read at startup."""
    p = fern.polling()
    assert (p.min_sleep_s, p.max_sleep_s) == (10, 900)


def test_no_agent_can_exceed_the_constitutional_ceiling(fern):
    """Even an agent that wants to nap forever is clamped — the shapes reject such beliefs
    too, so this is the second of three independent guards (the third is the firmware)."""
    p = fern.polling()
    p.beliefs = replace(p.beliefs, slow_sleep_s=99_999)
    assert p.cadence_for(0.99) == p.max_sleep_s


def test_no_agent_can_hammer_its_sensor_flat(fern):
    p = fern.polling()
    p.beliefs = replace(p.beliefs, fast_sleep_s=1)
    assert p.cadence_for(0.0) == p.min_sleep_s


# --- the two levers --------------------------------------------------------

def test_cadence_is_retained_so_a_sleeping_board_gets_it(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})
    retained = [r for t, p, r in fern.sent
                if t == sensor_of(fern).command_topic and "sleep_s" in p]
    assert retained and all(retained)


def test_an_unchanged_cadence_is_not_republished(fern):
    for _ in range(3):
        fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})
    assert len(cadences(fern)) == 1


def test_a_changed_cadence_is_republished(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.2})   # thirsty
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.9})   # comfortable
    assert len(cadences(fern)) == 2
    assert cadences(fern)[0] < cadences(fern)[1]


def test_a_sense_request_is_never_retained(fern):
    """A retained 'sense' would re-fire on every wake, forever."""
    fern.polling().sense_now()
    assert all(not retain for t, p, retain in fern.sent if p.get("sense"))


# --- judgment and disclosure ----------------------------------------------

def test_it_judges_itself_against_its_own_limits(fern):
    p = fern.polling()
    assert p.judge(0.20) == "LOW"
    assert p.judge(0.50) == "OK"
    assert p.judge(0.80) == "HIGH"


def test_it_announces_its_verdict_not_just_a_number(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.10})
    event = fern.sent.to(fern.me.event_topic)[-1]
    assert event["band"] == "LOW" and event["agent"] == "fern"


def test_the_reading_is_recorded_as_its_own_assertion(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"value": 0.123})
    reading = fern.beliefs.current_reading(fern.me.acts_for)
    assert reading.value == pytest.approx(0.123)
    assert reading.is_fresh(120)


def test_a_malformed_reading_changes_nothing(fern):
    fern.deliver(sensor_of(fern).reading_topic, {"sensor": "x"})  # no value
    assert cadences(fern) == []
    assert fern.beliefs.current_reading(fern.me.acts_for) is None
