"""A channel is a node, derived from the topics devices already state.

These run the real derivation over the real worlds, because the thing worth checking is not that
a rule fires but that it GROUPS: two sensors naming one topic must land on one node, or the whole
reason for having the node is gone.
"""

import pytest

from onboarding.namespaces import MQTT
from orexis_agent_progression.store import bindings

from conftest import genesis_store

OREXIS = "http://example.org/orexis#"

_CHANNELS = f"""
SELECT DISTINCT ?topic ?channel WHERE {{
  ?channel a <{MQTT}Channel> ; <{MQTT}channelTopic> ?topic
}}"""

_USERS = f"""
SELECT ?id ?topic ?dir WHERE {{
  ?d <{OREXIS}localId> ?id .
  {{ ?d <{MQTT}publishesOn> ?c . BIND("publishes" AS ?dir) }}
  UNION
  {{ ?d <{MQTT}listensOn> ?c . BIND("listens" AS ?dir) }}
  ?c <{MQTT}channelTopic> ?topic
}}"""


@pytest.fixture(scope="module")
def sensing():
    return genesis_store(world="sensing")


def _rows(store, query):
    return bindings(store.query(query))


def test_one_node_per_distinct_topic(sensing):
    """The identity check: a topic names exactly one channel, however many devices state it."""
    rows = _rows(sensing, _CHANNELS)
    by_topic = {}
    for r in rows:
        by_topic.setdefault(r["topic"], set()).add(r["channel"])
    assert by_topic, "no channels were derived at all"
    for topic, nodes in by_topic.items():
        assert len(nodes) == 1, f"{topic} minted {len(nodes)} nodes — the grouping is broken"


def test_three_sensors_on_one_board_share_one_reading_channel(sensing):
    """The case the node exists for.

    `world/sensing` puts soil moisture, air temperature and air humidity on one topic, because
    one board is one client and publishes once. Before this they shared a STRING, which nothing
    could hold a fact against. Now they share a node.
    """
    rows = [r for r in _rows(sensing, _USERS) if r["dir"] == "publishes"]
    readers = {r["id"] for r in rows if r["topic"].endswith("/reading")}
    assert readers == {"moisture_sensor_fern", "air_temp_fern", "air_humidity_fern"}


def test_direction_is_on_the_relation_not_the_channel(sensing):
    """One topic, two directions, one node.

    A board publishes its readings and listens for its cadence, and those are two channels
    because they are two topics. What must NOT happen is a topic splitting into a read node and
    a write node — the direction belongs to who is using the stream, not to the stream.
    """
    rows = _rows(sensing, _USERS)
    dirs = {}
    for r in rows:
        dirs.setdefault(r["topic"], set()).add(r["dir"])
    for topic, seen in dirs.items():
        assert len(seen) == 1, f"{topic} is used both ways — expected one per topic here"
    assert any(s == {"publishes"} for s in dirs.values())
    assert any(s == {"listens"} for s in dirs.values())


@pytest.mark.parametrize("world", ["simulation"])
def test_a_world_with_no_hardware_still_has_channels(world):
    """The reason the codec could move at all.

    `simulation` states no wiring, so it has no platforms — correctly, since nothing is
    mounted on anything there. It has topics, so it has channels, which is what made the stream
    the right bearer for an encoding and the board the wrong one.
    """
    rows = _rows(genesis_store(world=world), _CHANNELS)
    assert len(rows) >= 6, f"{world} derived only {len(rows)} channels"
