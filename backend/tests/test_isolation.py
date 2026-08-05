"""What each agent may reach — the series store and the bus, held to the same rule.

An agent's belief base is isolated structurally: it is a store in its own container, so there
is nothing to enforce. Its *history* and its *channels* are not — they live in shared
infrastructure, and there isolation has to be granted rather than arranged. These tests hold
the two provisioning tools to the property that makes the grant trustworthy: it is derived from
the world's wiring, and it is no wider than that wiring implies.

See knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import base64
import hashlib

import pytest

from agora import ratified
from onboarding import influx as influx_admin, mqtt as mqtt_admin
from agora.ontology import AG, WORLD_GRAPH

from conftest import build_agent, genesis_store

WORLDS = ["society", "sensing", "simulation"]


def covers(pattern: str, topic: str) -> bool:
    """MQTT matching, as the broker does it — so a grant of `x/+` covers `x/y`.

    A subscription that is itself wildcarded is only covered by a grant at least as wide: an
    agent granted `market/b/voucher/fern` has NOT been allowed to subscribe `market/b/voucher/+`.
    """
    p, t = pattern.split("/"), topic.split("/")
    for i, seg in enumerate(p):
        if seg == "#":
            return True
        if i >= len(t) or (seg != t[i] and seg != "+"):
            return False
    return len(p) == len(t)


def read_grants(principal) -> set[str]:
    return {topic for access, topic in principal.grants if access == mqtt_admin.READ}


# --------------------------------------------------------------- the bus


@pytest.mark.parametrize("world", WORLDS)
def test_every_subscription_a_module_makes_is_granted(world, monkeypatch):
    """The invariant the whole approach rests on: what the code subscribes, the ACL allows.

    Derivation is only worth having if it stays in step with the modules. It caught a real gap
    when it was written — a modelled subject listens for its own watering on the VALVE's
    command topic, which no other capability does, so nothing else in the wiring implied it.
    A missed grant does not raise: mosquitto accepts the SUBSCRIBE and silently drops the
    deliveries, so the failure looks like an agent that has simply gone quiet.
    """
    agents, _ = mqtt_admin.grants(world)
    store = genesis_store(world=world)

    for agent_id, principal in agents.items():
        agent = build_agent(agent_id, st=store, monkeypatch=monkeypatch)
        allowed = read_grants(principal)
        for module in agent.modules:
            for topic in module.subscriptions():
                assert any(covers(g, topic) for g in allowed), (
                    f"{world}/{agent_id}: {module.name} subscribes {topic!r}, which the "
                    f"derived ACL does not grant. Allowed: {sorted(allowed)}")


@pytest.mark.parametrize("world", WORLDS)
def test_no_agent_may_hear_a_neighbours_private_channel(world):
    """A voucher is addressed to one agent, and a reading is testimony about one subject.

    Expectations are read from the world here rather than from the tool, so this is a check and
    not an echo of the same query.
    """
    agents, _ = mqtt_admin.grants(world)
    ds = ratified.dataset(world)

    private = {}  # agent id -> the topics that are its alone
    for row in ratified.rows(ds, f"""SELECT ?id ?voucherTopic WHERE {{
        GRAPH <{WORLD_GRAPH}> {{
          ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}bidsIn> ?m .
          ?m <{AG}voucherTopic> ?voucherTopic . }} }}"""):
        private.setdefault(row["id"], set()).add(f"{row['voucherTopic']}/{row['id']}")
    for row in ratified.rows(ds, f"""SELECT ?id ?readingTopic WHERE {{
        GRAPH <{WORLD_GRAPH}> {{
          ?a a <{AG}Agent> ; <{AG}localId> ?id ; <{AG}polls> ?s .
          ?s <{AG}readingTopic> ?readingTopic . }} }}"""):
        private.setdefault(row["id"], set()).add(row["readingTopic"])

    assert private, f"{world} has no private channels to protect — the test proves nothing"
    for owner, topics in private.items():
        for other, principal in agents.items():
            if other == owner:
                continue
            for topic in topics:
                assert not any(covers(g, topic) for g in read_grants(principal)), (
                    f"{world}/{other} may hear {topic!r}, which belongs to {owner}")


@pytest.mark.parametrize("world", WORLDS)
def test_nobody_is_granted_a_wildcard_over_the_whole_bus(world):
    """`#`, or a bare `+` at the root, would hand back everything the rest of this buys."""
    agents, devices = mqtt_admin.grants(world)
    for principal in list(agents.values()) + list(devices.values()):
        for _, topic in principal.grants:
            head = topic.split("/")[0]
            assert head not in ("#", "+"), f"{principal.username} is granted {topic!r}"


def test_two_worlds_that_share_a_device_share_its_credential():
    """`world/sensing` is device-for-device identical to `world/society` on purpose, so one
    flashed board works in either. A world-scoped device credential would break that — the
    board would hold a name only one of them accepts."""
    _, sensing = mqtt_admin.grants("sensing")
    _, society = mqtt_admin.grants("society")
    shared = set(sensing) & set(society)
    assert shared, "the two worlds no longer share a device; this test has lost its subject"
    for device_id in shared:
        assert sensing[device_id].username == society[device_id].username


def test_agent_principals_are_world_scoped():
    """Two worlds each holding a `fern` are two agents, on two belief bases. One name would
    let either answer for the other."""
    society, _ = mqtt_admin.grants("society")
    simulation, _ = mqtt_admin.grants("simulation")
    assert society["fern"].username != simulation["fern"].username


def test_a_generated_password_line_is_one_mosquitto_can_verify():
    """The hash is written here rather than by `mosquitto_passwd`, so the format is ours to
    get right: $7$ is PBKDF2-HMAC-SHA512, with the iteration count carried in the line."""
    line = mqtt_admin._hash("hunter2")
    marker, iterations, salt, digest = line.split("$")[1:]
    assert marker == "7"
    recomputed = hashlib.pbkdf2_hmac(
        "sha512", b"hunter2", base64.b64decode(salt), int(iterations), 64)
    assert base64.b64encode(recomputed).decode() == digest
    assert mqtt_admin._hash("hunter2") != line, "every line must carry a fresh salt"


# --------------------------------------------------------------- the series store


@pytest.mark.parametrize("world", WORLDS)
def test_every_agent_gets_its_own_bucket(world):
    from onboarding import compose

    names = {a: influx_admin.bucket_name(world, a) for a in compose.agent_ids(world)}
    assert len(set(names.values())) == len(names), f"two agents share a bucket in {world}"


def test_bucket_names_cannot_collide_across_worlds():
    """Bucket names are org-global. Two worlds each holding a `fern` must not share a history,
    or a simulation writes into the record of a real plant — and no world can detect that for
    itself, because a world is not allowed to know the others exist."""
    seen = {}
    for world in WORLDS:
        from onboarding import compose

        for agent_id in compose.agent_ids(world):
            name = influx_admin.bucket_name(world, agent_id)
            assert name not in seen, f"{world}/{agent_id} collides with {seen.get(name)}"
            seen[name] = f"{world}/{agent_id}"
