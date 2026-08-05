"""What a running broker does when the ACL underneath it changes.

Everything else in this suite is about what `agora-mqtt` *derives*. This file is about what the
broker then *enforces*, at runtime, against a client that is already connected — which is a
different question and cannot be answered by reading the generated files. It is the question an
operator actually has: I added an agent and reloaded; did anything change for the ones already
running, and did I just interrupt them?

It lives under `infra/` rather than with the unit tests because it tests *this infrastructure*,
not the code: it is a contract with a particular broker, and it is meaningless without one
running. So `pytest backend -q` does not collect it and stays the fast, infra-free gate it has
always been. Run these deliberately:

    cd infra && podman compose up -d && agora-mqtt <world>
    pytest infra -q

They still **skip** rather than fail when the broker or the credentials are absent, so pointing
pytest at the repo root on a machine with nothing running is harmless.

Nothing here touches a real agent's grants. The tests mint a **probe principal** of their own,
append it to the broker's two files, and take it away again — so running this while a society is
up cannot revoke anything from an agent doing real work. The fixture restores both files byte for
byte and reloads, whatever the outcome.

See knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import socket
import time
import uuid

import pytest

from agora import ratified
from onboarding import mqtt as mqtt_admin
from agora.ontology import AG, WORLD_GRAPH

paho = pytest.importorskip("paho.mqtt.client")

WORLD = "sensing"    # the smallest world that states a bus
DELIVER_S = 3.0      # how long a message gets to arrive before it counts as blocked
READY_S = 20.0       # how long the broker gets to finish a reload

# Nothing here waits a fixed time for something it can observe instead. A reload takes longer on
# a loaded machine than an idle one, and the first version of this file slept 1.5s and passed
# alone while failing inside the full suite — a flaky test about security is worse than none.


def _bus() -> tuple[str, int]:
    """Discovered, not hardcoded — the world states where the broker is, as it does for agents."""
    rows = ratified.rows(ratified.dataset(WORLD), f"""SELECT ?host ?port WHERE {{
        GRAPH <{WORLD_GRAPH}> {{
          ?b a <{AG}MessageBus> ; <{AG}brokerHost> ?host ; <{AG}brokerPort> ?port . }} }}""")
    if not rows:
        pytest.skip(f"world {WORLD} states no message bus")
    return rows[0]["host"], int(rows[0]["port"])


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def bus():
    host, port = _bus()
    if not mqtt_admin.PASSWD_FILE.exists() or not mqtt_admin.ACL_FILE.exists():
        pytest.skip("no broker credentials yet — run `agora-mqtt <world>` first")
    if not _reachable(host, port):
        pytest.skip(f"no broker at {host}:{port} — bring infra up to run these")
    return host, port


class Probe:
    """A principal that exists only for this test, and its own private topic."""

    def __init__(self):
        self.username = f"acl-probe-{uuid.uuid4().hex[:8]}"
        self.password = uuid.uuid4().hex
        self.topic = f"probe/acl/{uuid.uuid4().hex[:8]}"


def _grants_block(probe: Probe, read: bool) -> str:
    lines = [f"\n# ---- test probe (removed again by the fixture) {'-' * 20}",
             f"user {probe.username}", f"topic write {probe.topic}",
             # so the tests can ask the broker what it is. No real principal is granted $SYS.
             "topic read $SYS/broker/version"]
    if read:
        lines.append(f"topic read {probe.topic}")
    return "\n".join(lines) + "\n"




@pytest.fixture
def probe(bus):
    """Add a principal to the live broker, and guarantee it is gone again."""
    p = Probe()
    passwd_before = mqtt_admin.PASSWD_FILE.read_text()
    acl_before = mqtt_admin.ACL_FILE.read_text()

    def apply(read: bool, password: str | None = None):
        """Rewrite the broker's two files, reload, and WAIT until the change is really live."""
        p.password = password or p.password
        mqtt_admin.PASSWD_FILE.write_text(
            passwd_before + f"{p.username}:{mqtt_admin._hash(p.password)}\n")
        mqtt_admin.ACL_FILE.write_text(acl_before + _grants_block(p, read=read))
        assert mqtt_admin.reload_broker(), "the broker did not accept a reload"
        _await_credential(bus, p.username, p.password)

    p.apply = apply
    try:
        apply(read=True)
        yield p
    finally:
        mqtt_admin.PASSWD_FILE.write_text(passwd_before)
        mqtt_admin.ACL_FILE.write_text(acl_before)
        mqtt_admin.reload_broker()


def _open(host, port, username, password):
    """One connection attempt. Returns the client and the CONNACK reason, whatever it was."""
    c = paho.Client(paho.CallbackAPIVersion.VERSION2, protocol=paho.MQTTv5)
    c.username_pw_set(username, password)
    seen, life, rc = [], {}, {}
    c.on_message = lambda cl, u, m: seen.append(m.payload.decode())
    c.on_disconnect = lambda cl, u, d, reason, props=None: life.setdefault("gone", str(reason))
    c.on_connect = lambda cl, u, f, reason, props=None: rc.setdefault("r", str(reason))
    c.connect(host, port)
    c.loop_start()
    deadline = time.time() + 5
    while "r" not in rc and time.time() < deadline:
        time.sleep(0.05)
    return c, seen, life, rc.get("r", "no CONNACK")


def _await_credential(bus, username, password, timeout=READY_S):
    """Block until this credential authenticates — i.e. until the reload has actually landed."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        c, _, _, last = _open(*bus, username, password)
        c.loop_stop()
        c.disconnect()
        if last == "Success":
            return
        time.sleep(0.25)
    raise AssertionError(f"broker never accepted {username} after a reload (last: {last!r})")


def _connect(host, port, username, password):
    c, seen, life, reason = _open(host, port, username, password)
    assert reason == "Success", f"probe could not connect: {reason}"
    return c, seen, life


def _subscribe(client, topic) -> None:
    """Subscribe and wait for the SUBACK. Mosquitto grants a subscription it will not honour —
    which is exactly why these tests judge by delivery, never by the SUBACK's return code."""
    acked = {}
    client.on_subscribe = lambda cl, u, mid, codes, props=None: acked.setdefault("ok", True)
    client.subscribe(topic, 1)
    deadline = time.time() + 5
    while "ok" not in acked and time.time() < deadline:
        time.sleep(0.05)
    assert acked.get("ok"), f"no SUBACK for {topic}"


def _delivered(client, seen, topic, marker) -> bool:
    """Publish and watch. Waits for arrival, but must wait out the full window to say 'no' —
    an absence is only meaningful once the message has had time to show up."""
    seen.clear()
    client.publish(topic, marker, qos=1).wait_for_publish(5)
    deadline = time.time() + DELIVER_S
    while time.time() < deadline:
        if marker in seen:
            return True
        time.sleep(0.05)
    return False


def test_reports_which_broker_these_results_are_about(bus, probe):
    """Says what was actually tested, and asserts nothing about which version that is.

    The point of this file is regression across broker upgrades: change the version in
    `infra/mosquitto/Containerfile`, rebuild, re-run, and see whether the behaviours below still
    hold. So the version is *reported*, never pinned here — a test that had to be edited to match
    the compose file would be one more thing to keep in step, and would fail for a version change
    rather than for a behaviour change, which is the only thing worth failing for.
    """
    client, seen, _ = _connect(*bus, probe.username, probe.password)
    try:
        _subscribe(client, "$SYS/broker/version")
        deadline = time.time() + DELIVER_S
        while not seen and time.time() < deadline:
            time.sleep(0.05)
        assert seen, ("the broker published no $SYS/broker/version — if $SYS has been disabled, "
                      "these results cannot say which broker they are about")
        print(f"\nbroker under test: {seen[0]}")
    finally:
        client.loop_stop()
        client.disconnect()


def test_revoking_a_grant_takes_effect_on_a_connected_client(bus, probe):
    """The question this file exists for.

    Mosquitto checks the ACL on every DELIVERY, not only at SUBSCRIBE — which is also why an
    agent may subscribe `#` and still receive only its own topics. So a revoked grant stops the
    traffic at once, without the client reconnecting or re-subscribing.
    """
    client, seen, life = _connect(*bus, probe.username, probe.password)
    try:
        _subscribe(client, probe.topic)
        assert _delivered(client, seen, probe.topic, "before"), (
            "the probe should receive its own topic while the grant is in place")

        probe.apply(read=False)  # revoke the read grant and reload

        assert not _delivered(client, seen, probe.topic, "after"), (
            "a revoked read grant must stop delivery to a client that is already subscribed")
        assert "gone" not in life, (
            "revoking a grant must not disconnect the client — other agents are on this broker")
    finally:
        client.loop_stop()
        client.disconnect()


def test_granting_reaches_a_client_that_never_resubscribed(bus, probe):
    """The other direction, and the reason adding an agent disturbs nobody.

    A subscription mosquitto was not going to honour is still *accepted*, so when the grant
    appears the traffic simply starts. Nothing has to be restarted or told.
    """
    probe.apply(read=False)
    client, seen, life = _connect(*bus, probe.username, probe.password)
    try:
        _subscribe(client, probe.topic)
        assert not _delivered(client, seen, probe.topic, "ungranted")

        probe.apply(read=True)

        assert _delivered(client, seen, probe.topic, "granted"), (
            "a new grant must reach a client that subscribed before it existed")
        assert "gone" not in life
    finally:
        client.loop_stop()
        client.disconnect()


def test_rotating_a_password_evicts_the_connected_client(bus, probe):
    """Eviction, which is stronger than expected and worth pinning down so it cannot regress.

    Credentials are checked at CONNECT, so the reasonable guess is that rotating a password locks
    a principal out of its *next* connection and leaves the session it already holds alone. That
    guess is wrong: on reload, mosquitto re-checks connected clients against the new password file
    and disconnects the ones that no longer match. Written as a test because it was measured, and
    because it decides how much `agora-mqtt --rotate` is actually worth — a rotated agent really
    is off the bus, not merely barred from returning.

    Note what this does NOT weaken: the two tests above reload the same broker without
    disconnecting anyone. It is the credential change that evicts, not the reload.
    """
    client, seen, life = _connect(*bus, probe.username, probe.password)
    try:
        _subscribe(client, probe.topic)
        assert _delivered(client, seen, probe.topic, "before-rotate")

        old_password = probe.password
        probe.apply(read=True, password=uuid.uuid4().hex)  # its credential is now stale

        assert "gone" in life, (
            "a rotated password must drop the session it invalidates, not just bar the next one")

        stale, _, _, reason = _open(*bus, probe.username, old_password)
        stale.loop_stop()
        assert reason == "Not authorized", (
            f"a new connection with the old password must be refused, got {reason!r}")
    finally:
        client.loop_stop()
        client.disconnect()
