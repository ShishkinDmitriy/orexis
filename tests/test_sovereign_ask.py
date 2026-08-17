"""The sovereign may ask, and the agent answers about itself — disclosure, not access.

The channel agent/sovereign.py declares, exercised end to end short of a broker: the
responder in reporting, the grants in agora-mqtt, and the one property that makes the whole
thing safe to exist — read-only by construction, because pyoxigraph's query API structurally
cannot execute an update.
"""

from __future__ import annotations

import json

import pytest

from agent import sovereign
from onboarding import mqtt as mqtt_admin

from conftest import build_agent, genesis_store


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def reporter_of(agent):
    return next(m for m in agent.modules if m.name == "reporting")


def _answer(agent):
    replies = agent.sent.to(sovereign.result_topic(agent.id))
    assert replies, "the agent must answer on its own result topic"
    raw = replies[-1]
    return json.loads(raw) if isinstance(raw, (str, bytes)) else raw


def test_a_select_is_answered_from_the_live_store(fern):
    took = reporter_of(fern).handle(
        sovereign.query_topic(fern.id),
        b"SELECT ?v WHERE { ?a <http://example.org/agora/sensing#slowSleepS> ?v }")
    assert took
    answer = _answer(fern)
    assert answer["rows"] and answer["rows"][0]["v"] == "600", \
        "fern's own belief, disclosed on the authorised channel"


def test_an_update_is_refused_by_the_engine_not_a_filter(fern):
    before = fern.store.query(
        "SELECT ?v WHERE { ?a <http://example.org/agora/sensing#slowSleepS> ?v }")
    reporter_of(fern).handle(
        sovereign.query_topic(fern.id),
        b'INSERT DATA { <http://example.org/x> <http://example.org/y> "stolen" }')
    answer = _answer(fern)
    assert "error" in answer, "an update must come back as the engine's own refusal"
    assert fern.store.query(
        "SELECT ?v WHERE { ?a <http://example.org/agora/sensing#slowSleepS> ?v }") == before


def test_a_question_for_another_agent_is_not_taken(fern):
    took = reporter_of(fern).handle(sovereign.query_topic("tomato"), b"SELECT * WHERE {?s ?p ?o}")
    assert not took
    assert not fern.sent.to(sovereign.result_topic("tomato")), \
        "an agent must never speak on another's channel"


def test_a_flood_of_rows_is_capped_not_streamed(fern):
    reporter_of(fern).handle(sovereign.query_topic(fern.id),
                             b"SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
    answer = _answer(fern)
    assert len(answer["rows"]) <= reporter_of(fern).ANSWER_ROWS
    assert answer.get("truncated"), "a whole belief base exceeds the cap and must say so"


def test_the_acl_admits_exactly_one_asker_per_channel():
    """Both halves of the grant, from the same generator the broker is configured by: the
    sovereign may ask each agent and hear each answer; each agent may hear only its own
    questions and answer only on its own channel; nobody else appears on these topics."""
    agents, devices = mqtt_admin.grants("simulation")
    asker = devices[sovereign.SOVEREIGN]
    for agent_id, principal in agents.items():
        assert (mqtt_admin.WRITE, sovereign.query_topic(agent_id)) in asker.grants
        assert (mqtt_admin.READ, sovereign.result_topic(agent_id)) in asker.grants
        assert (mqtt_admin.READ, sovereign.query_topic(agent_id)) in principal.grants
        assert (mqtt_admin.WRITE, sovereign.result_topic(agent_id)) in principal.grants
        for other_id in agents:
            if other_id != agent_id:
                assert (mqtt_admin.READ, sovereign.query_topic(other_id)) not in principal.grants
                assert (mqtt_admin.WRITE, sovereign.result_topic(other_id)) not in principal.grants
