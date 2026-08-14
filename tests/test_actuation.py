"""actuation:Actuation — claim to bounded, co-signed command. The actuate boundary.

Dosing is not configured here: it comes from the valve's own calibration in the world, so
these tests build a device and check the module obeys it.
"""

import json
import logging
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent import loader, signing  # noqa: F401  (loader puts the package trees on sys.path)
from agent.clearing import Claim
from agent.signing import verify_command
from packages.capability.actuation import ActuationModule
from agent.world import Actuator, Self


class FakeAgent:
    """The smallest thing an actuation module needs: an identity and somewhere to publish."""

    def __init__(self, ml_per_second=10.0, max_dose_ml=1000.0,
                 status_topic="actuators/fern/valve/status", dose_grace_s=10):
        valve = Actuator(
            uri="ag:valve_fern", local_id="valve_fern", subject="ag:fern", subject_id="fern",
            command_topic="actuators/fern/valve",
            ml_per_second=ml_per_second, max_dose_ml=max_dose_ml,
            status_topic=status_topic,
        )
        self.id = "supplier"
        self.me = Self(uri="ag:supplier", agent_id="supplier", capabilities=frozenset(),
                       actuators=(valve,))
        self.sent = []
        self.beliefs = _Beliefs(dose_grace_s)

    def publish(self, topic, payload, retain=False):
        self.sent.append((topic, payload))


class _Beliefs:
    """Just enough belief base to hand back this capability's one figure."""

    def __init__(self, dose_grace_s):
        self._grace = dose_grace_s

    def read(self, block):
        return block.cls(dose_grace_s=self._grace)


def module(agent=None):
    agent = agent or FakeAgent()
    m = ActuationModule(agent)
    m.host_key = Ed25519PrivateKey.generate()
    m.clearing_key = Ed25519PrivateKey.generate()
    return m, agent


def claim(jti="j1", sub="fern", amount_l=0.64):
    return Claim(sub=sub, scope=f"actuate:valve/{sub}", amount_l=amount_l,
                   debit=0.3, auction_id="R-1", jti=jti)


# --- dosing follows the device ---------------------------------------------

def test_litres_become_open_seconds():
    m, _ = module()
    cmd, _ = m.command_for(claim(amount_l=0.64))  # 640 ml
    assert cmd.ml == 640.0 and cmd.seconds == 64.0


def test_a_faster_valve_opens_for_less_time():
    m, _ = module(FakeAgent(ml_per_second=40.0))
    cmd, _ = m.command_for(claim(amount_l=0.64))
    assert cmd.seconds == 16.0  # same litres, different hardware


def test_the_device_caps_its_own_dose():
    m, _ = module(FakeAgent(max_dose_ml=500.0))
    cmd, _ = m.command_for(claim(amount_l=5.0))  # 5000 ml cleared
    assert cmd.ml == 500.0  # defence in depth, whatever the claim said


def test_a_claim_for_hardware_i_do_not_own_is_refused():
    m, _ = module()
    with pytest.raises(ValueError, match="no actuator"):
        m.redeem(claim(sub="orchid"))


# --- the actuate boundary --------------------------------------------------

def test_command_goes_to_the_devices_own_topic():
    m, agent = module()
    m.redeem(claim())
    topic, _ = agent.sent[0]
    assert topic == "actuators/fern/valve"  # stated by the world, not built from the id


def test_settled_command_is_co_signed_and_verifies():
    m, agent = module()
    m.redeem(claim())
    _, payload = agent.sent[0]
    assert verify_command(payload, m.host_key.public_key(), m.clearing_key.public_key())


def test_unsigned_command_is_rejected():
    m, agent = module()
    m.host_key = m.clearing_key = None  # no keys -> no signatures
    m.redeem(claim())
    _, payload = agent.sent[0]
    other = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(payload, other, other)


def test_tampered_dose_is_rejected():
    m, agent = module()
    m.redeem(claim())
    _, payload = agent.sent[0]
    payload["ml"] = 9999.0  # someone tries to enlarge the dose in flight
    assert not verify_command(payload, m.host_key.public_key(), m.clearing_key.public_key())


def test_a_wrong_signer_is_rejected():
    m, agent = module()
    m.redeem(claim())
    _, payload = agent.sent[0]
    impostor = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(payload, impostor, m.clearing_key.public_key())


# --- single use ------------------------------------------------------------

def test_replay_is_refused():
    m, agent = module()
    m.redeem(claim(jti="dup"))
    with pytest.raises(ValueError, match="replay"):
        m.redeem(claim(jti="dup"))
    assert len(agent.sent) == 1  # the second never reached the wire


def test_redeem_all_is_one_command_per_claim():
    m, agent = module()
    m.redeem_all([claim(jti="a", sub="fern"), claim(jti="b", sub="fern")])
    assert len(agent.sent) == 2


# --- single use ------------------------------------------------------------

def test_a_redeemed_claim_cannot_fire_twice():
    """A jti is spent on redemption, so a replayed claim opens nothing."""
    m, _ = module()
    m.redeem(claim(jti="dup"))
    with pytest.raises(ValueError, match="replay"):
        m.redeem(claim(jti="dup"))


# --- commanded is not delivered (#36) --------------------------------------

def test_it_listens_on_its_own_valves_status_and_no_wildcard():
    """The grant has existed since PR #34 and nothing consumed it. Now something does."""
    m, _ = module()
    assert m.subscriptions() == ["actuators/fern/valve/status"]
    assert not any("+" in t or "#" in t for t in m.subscriptions())


def test_a_valve_that_reports_confirms_the_dose():
    m, _ = module()
    m.redeem(claim(jti="j-ok"))
    assert "j-ok" in m.pending, "a commanded dose is outstanding until the device reports"
    m.handle("actuators/fern/valve/status",
             json.dumps({"valve": "valve_fern", "jti": "j-ok", "ml": 640.0, "ok": True}).encode())
    assert m.pending == {} and m.confirmed == 1 and m.unconfirmed == 0


def test_silence_past_the_deadline_is_noticed_and_counted(caplog):
    """The failure this whole change exists for: a valve that never heard, or refused.

    `firmware/simulated-valve` publishes on the status topic after dispensing and stays SILENT
    when it refuses — signature, replay, nothing to dispense. So silence IS the refusal, and
    before this it was indistinguishable from a dose that went perfectly.
    """
    m, _ = module(FakeAgent(ml_per_second=100000.0, dose_grace_s=0))
    m.redeem(claim(jti="j-lost"))
    time.sleep(0.05)
    with caplog.at_level(logging.WARNING):
        m._expire()
    assert m.unconfirmed == 1 and m.confirmed == 0
    assert "no confirmation" in caplog.text and "j-lost" in caplog.text


def test_an_unconfirmed_dose_stays_spent():
    """Deliberate, and the opposite of what #36 proposed.

    The device keeps its own spent set, so a re-sent command is refused rather than poured —
    un-spending buys nothing. And the failures are not symmetric: a lost report plus a re-send
    risks watering twice, while an unopened valve costs one round the plant bids again for.
    """
    m, _ = module(FakeAgent(ml_per_second=100000.0, dose_grace_s=0))
    m.redeem(claim(jti="j-lost"))
    time.sleep(0.05)
    m._expire()
    assert m.unconfirmed == 1
    with pytest.raises(ValueError, match="replay"):
        m.redeem(claim(jti="j-lost"))


def test_a_valve_with_no_status_channel_is_never_waited_on():
    """A world may wire a valve it cannot hear back from — a deployment, not an error. Nothing
    goes pending, and the zeroes in `reports()` are themselves the reading."""
    m, _ = module(FakeAgent(status_topic=None))
    m.redeem(claim(jti="j-deaf"))
    assert m.subscriptions() == [] and m.pending == {}
    m._expire()
    assert m.unconfirmed == 0


def test_a_report_for_a_dose_it_forgot_is_not_an_error():
    """A restarted agent has forgotten what it commanded; the device is right to report."""
    m, _ = module()
    assert m.handle("actuators/fern/valve/status",
                    json.dumps({"jti": "from-before-the-restart"}).encode()) is True
    assert m.unconfirmed == 0 and m.confirmed == 0


def test_the_counts_reach_the_agents_own_series():
    m, _ = module()
    assert m.reports() == {"doses_confirmed": 0, "doses_unconfirmed": 0}
