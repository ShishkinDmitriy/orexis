"""The stand-in valve refuses what a real one would refuse.

The old simulated-actuation capability said plainly that it did not sign, "because there is
nothing to convince". That was honest and it meant the simulation exercised everything about
actuation except the part the market exists to make safe. A stand-in that opens for an unsigned
command is not standing in for a valve; it is standing in for a valve with its safety removed.

So these hold it to the two limits the real path enforces — a token signed by BOTH parties, and
the device's own dose ceiling regardless of what cleared — and to one thing peculiar to being a
copy: `firmware/simulated-valve/valve.py` reimplements `agent.signing.verify_command`, because
its image holds cryptography and paho and not the agent package. Duplication that nothing checks
drifts, so the last test here checks it.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent import signing

VALVE_PY = Path(__file__).resolve().parents[1] / "firmware" / "simulated-valve" / "valve.py"


def _load_valve_module():
    """Import the firmware by path: it is not a package and must never become one."""
    spec = importlib.util.spec_from_file_location("_sim_valve", VALVE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


valve_mod = _load_valve_module()


@pytest.fixture
def keys():
    host, clearing = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    return host, clearing, host.public_key(), clearing.public_key()


def _command(host_key=None, clearing_key=None, **over):
    payload = {"jti": "j1", "plant": "fern", "scope": "water",
               "ml": 500.0, "seconds": 50.0, "auction_id": "r1"}
    payload.update(over)
    data = signing.canonical(payload)
    if host_key is not None:
        payload["match_sig"] = signing.sign(host_key, data)
    if clearing_key is not None:
        payload["val_sig"] = signing.sign(clearing_key, data)
    return payload


def test_a_fully_signed_command_is_accepted(keys):
    host, clearing, host_pub, clearing_pub = keys
    assert valve_mod.verify_command(_command(host, clearing), host_pub, clearing_pub)


def test_an_unsigned_command_moves_no_water(keys):
    _, _, host_pub, clearing_pub = keys
    assert not valve_mod.verify_command(_command(), host_pub, clearing_pub)


@pytest.mark.parametrize("signer", ["host", "clearing"])
def test_one_signature_is_not_enough(keys, signer):
    """Either party alone is a decision only half the society made."""
    host, clearing, host_pub, clearing_pub = keys
    payload = _command(host, None) if signer == "host" else _command(None, clearing)
    assert not valve_mod.verify_command(payload, host_pub, clearing_pub)


def test_a_tampered_dose_is_refused(keys):
    """The interesting attack: sign a small dose, deliver a large one."""
    host, clearing, host_pub, clearing_pub = keys
    payload = _command(host, clearing)
    payload["ml"] = 999999.0
    assert not valve_mod.verify_command(payload, host_pub, clearing_pub)


def test_a_command_signed_by_another_society_is_refused(keys):
    """Two worlds are two societies, and neither may open the other's valves."""
    _, _, host_pub, clearing_pub = keys
    other_host, other_clearing = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    assert not valve_mod.verify_command(
        _command(other_host, other_clearing), host_pub, clearing_pub)


def test_missing_public_keys_refuse_everything(keys):
    """A valve that could not load its keys must fail closed, not open."""
    host, clearing, host_pub, _ = keys
    assert not valve_mod.verify_command(_command(host, clearing), None, None)
    assert not valve_mod.verify_command(_command(host, clearing), host_pub, None)


def test_the_copy_agrees_with_the_kernel(keys):
    """The duplication cannot drift in silence.

    `agent.signing.verify_command` and the firmware's copy must answer identically, including on
    the awkward inputs — that is the whole reason it is safe to have two of them.
    """
    host, clearing, host_pub, clearing_pub = keys
    cases = [
        _command(host, clearing),
        _command(),
        _command(host, None),
        _command(None, clearing),
        {**_command(host, clearing), "ml": 1.0},
        {**_command(host, clearing), "match_sig": "not-base64!!"},
        {**_command(host, clearing), "val_sig": ""},
    ]
    for payload in cases:
        assert (valve_mod.verify_command(payload, host_pub, clearing_pub)
                == signing.verify_command(payload, host_pub, clearing_pub)), payload

    # and the canonical bytes themselves, which is where a drift would actually begin
    assert valve_mod.canonical({"b": 2, "a": 1}) == signing.canonical({"b": 2, "a": 1})


class _Recorder:
    """Stands in for the paho client: remembers what was published, connects to nothing."""

    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, json.loads(payload)))

    def username_pw_set(self, *a, **k):
        pass


def _valve_under_test(monkeypatch, keys, max_dose_ml="1000"):
    _, _, host_pub, clearing_pub = keys
    for name, value in {
        "VALVE_ID": "valve_fern",
        "VALVE_COMMAND_TOPIC": "sim/actuators/fern/valve",
        "VALVE_STATUS_TOPIC": "sim/actuators/fern/valve/status",
        "VALVE_ML_PER_SECOND": "10000",   # keep the abbreviated pour near-instant
        "VALVE_MAX_DOSE_ML": max_dose_ml,
        "MQTT_USERNAME": "valve_fern", "MQTT_PASSWORD": "x",
        "MQTT_HOST": "localhost", "MQTT_PORT": "1885",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(valve_mod.mqtt, "Client", lambda *a, **k: _Recorder())
    valve = valve_mod.SimulatedValve()
    valve.host_pub, valve.clearing_pub = host_pub, clearing_pub
    return valve


class _Msg:
    def __init__(self, topic, payload):
        self.topic, self.payload = topic, json.dumps(payload).encode()


def test_the_dose_is_capped_by_the_device_not_by_the_market(monkeypatch, keys):
    """The valve's own ceiling, applied after the signature and whatever cleared.

    Two independent limits — the module's and the device's — because the interesting failures
    are the ones where one of them is wrong. Here the market cleared five litres and the device
    passes one, so one is what flows.
    """
    host, clearing, _, _ = keys
    valve = _valve_under_test(monkeypatch, keys)
    valve._on_message(None, None, _Msg(valve.command_topic, _command(host, clearing, ml=5000.0)))

    assert len(valve.client.published) == 1
    topic, report = valve.client.published[0]
    assert topic == valve.status_topic
    assert report["ml"] == 1000.0        # the device's limit, not the 5000 that cleared


def test_an_unsigned_command_leaves_the_soil_dry(monkeypatch, keys):
    """The behaviour the whole change exists for.

    The simulated sensor waters on the STATUS topic, so a refusal that publishes nothing is a
    plant that stays dry. Under the old arrangement the sensor read the COMMAND topic and would
    have been watered by this.
    """
    valve = _valve_under_test(monkeypatch, keys)
    valve._on_message(None, None, _Msg(valve.command_topic, _command()))
    assert valve.client.published == []


def test_a_replayed_voucher_dispenses_once(monkeypatch, keys):
    """Single-use by jti, as the real path enforces it."""
    host, clearing, _, _ = keys
    valve = _valve_under_test(monkeypatch, keys)
    command = _command(host, clearing, ml=100.0)
    valve._on_message(None, None, _Msg(valve.command_topic, command))
    valve._on_message(None, None, _Msg(valve.command_topic, command))
    assert len(valve.client.published) == 1


def test_the_firmware_never_imports_agora():
    """Its image holds cryptography and paho. Importing agora would put the belief base, the
    SHACL machinery and a 230 MB dependency set on a device."""
    source = VALVE_PY.read_text()
    assert "import agent" not in source
    assert "from agent" not in source


def test_a_refusal_is_silent_on_the_status_topic():
    """Silence is the report: no water flowed.

    A refusal that announced itself on the status topic would still be a message a simulated
    sensor might learn to water on, and the one thing a refusing valve must not do is move water
    it declined to move.
    """
    source = VALVE_PY.read_text()
    refuse = source[source.index("def _refuse"):source.index("def _on_message")]
    # the CALL, not the word: the docstring explains why it does not publish, and matching prose
    # would have made this test pass for the wrong reason
    body = "\n".join(line for line in refuse.splitlines()
                     if not line.strip().startswith("#") and '"""' not in line)
    assert "self.client.publish" not in body
    assert ".publish(" not in body
