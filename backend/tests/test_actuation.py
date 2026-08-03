"""ag:Actuation — voucher to bounded, co-signed command. The actuate boundary.

Dosing is not configured here: it comes from the valve's own calibration in the world, so
these tests build a device and check the module obeys it.
"""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agora import signing
from agora.clearing import Voucher
from agora.modules.actuation import ActuationModule, verify_command
from agora.world import Actuator, Self


class FakeAgent:
    """The smallest thing an actuation module needs: an identity and somewhere to publish."""

    def __init__(self, ml_per_second=10.0, max_dose_ml=1000.0):
        valve = Actuator(
            uri="ag:valve_fern", local_id="valve_fern", subject="ag:fern", subject_id="fern",
            command_topic="actuators/fern/valve",
            ml_per_second=ml_per_second, max_dose_ml=max_dose_ml,
        )
        self.id = "supplier"
        self.me = Self(uri="ag:supplier", agent_id="supplier", capabilities=frozenset(),
                       actuators=(valve,))
        self.sent = []

    def publish(self, topic, payload, retain=False):
        self.sent.append((topic, payload))


def module(agent=None, armed=True, monkeypatch=None):
    agent = agent or FakeAgent()
    if monkeypatch is not None:
        monkeypatch.setenv("AGORA_ACTUATE", "true" if armed else "false")
    m = ActuationModule(agent)
    m.armed = armed
    m.host_key = Ed25519PrivateKey.generate()
    m.clearing_key = Ed25519PrivateKey.generate()
    return m, agent


def voucher(jti="j1", sub="fern", amount_l=0.64):
    return Voucher(sub=sub, scope=f"actuate:valve/{sub}", amount_l=amount_l,
                   debit=0.3, round_id="R-1", jti=jti)


# --- dosing follows the device ---------------------------------------------

def test_litres_become_open_seconds():
    m, _ = module()
    cmd, _ = m.command_for(voucher(amount_l=0.64))  # 640 ml
    assert cmd.ml == 640.0 and cmd.seconds == 64.0


def test_a_faster_valve_opens_for_less_time():
    m, _ = module(FakeAgent(ml_per_second=40.0))
    cmd, _ = m.command_for(voucher(amount_l=0.64))
    assert cmd.seconds == 16.0  # same litres, different hardware


def test_the_device_caps_its_own_dose():
    m, _ = module(FakeAgent(max_dose_ml=500.0))
    cmd, _ = m.command_for(voucher(amount_l=5.0))  # 5000 ml cleared
    assert cmd.ml == 500.0  # defence in depth, whatever the voucher said


def test_a_voucher_for_hardware_i_do_not_own_is_refused():
    m, _ = module()
    with pytest.raises(ValueError, match="no actuator"):
        m.redeem(voucher(sub="orchid"))


# --- the actuate boundary --------------------------------------------------

def test_command_goes_to_the_devices_own_topic():
    m, agent = module()
    m.redeem(voucher())
    topic, _ = agent.sent[0]
    assert topic == "actuators/fern/valve"  # stated by the world, not built from the id


def test_settled_command_is_co_signed_and_verifies():
    m, agent = module()
    m.redeem(voucher())
    _, payload = agent.sent[0]
    assert verify_command(payload, m.host_key.public_key(), m.clearing_key.public_key())


def test_unsigned_command_is_rejected():
    m, agent = module()
    m.host_key = m.clearing_key = None  # no keys -> no signatures
    m.redeem(voucher())
    _, payload = agent.sent[0]
    other = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(payload, other, other)


def test_tampered_dose_is_rejected():
    m, agent = module()
    m.redeem(voucher())
    _, payload = agent.sent[0]
    payload["ml"] = 9999.0  # someone tries to enlarge the dose in flight
    assert not verify_command(payload, m.host_key.public_key(), m.clearing_key.public_key())


def test_a_wrong_signer_is_rejected():
    m, agent = module()
    m.redeem(voucher())
    _, payload = agent.sent[0]
    impostor = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(payload, impostor, m.clearing_key.public_key())


# --- single use ------------------------------------------------------------

def test_replay_is_refused():
    m, agent = module()
    m.redeem(voucher(jti="dup"))
    with pytest.raises(ValueError, match="replay"):
        m.redeem(voucher(jti="dup"))
    assert len(agent.sent) == 1  # the second never reached the wire


def test_redeem_all_is_one_command_per_voucher():
    m, agent = module()
    m.redeem_all([voucher(jti="a", sub="fern"), voucher(jti="b", sub="fern")])
    assert len(agent.sent) == 2


# --- the deployment safety toggle ------------------------------------------

def test_a_disarmed_module_opens_nothing():
    m, agent = module(armed=False)
    cmd = m.redeem(voucher())
    assert cmd.ml > 0  # it still decides, and logs what it would have done
    assert agent.sent == []  # but no valve command reaches the wire


def test_a_dry_run_still_spends_the_jti():
    """Otherwise arming the system later would let every past voucher fire."""
    m, _ = module(armed=False)
    m.redeem(voucher(jti="dup"))
    with pytest.raises(ValueError, match="replay"):
        m.redeem(voucher(jti="dup"))
