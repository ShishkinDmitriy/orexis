"""The sovereign may ask, and the agent answers about itself — disclosure, not access.

The channel packages/orexis-capability-reporting/sovereign.py declares, exercised end to end short of a broker: the
responder in reporting, the grants in orexis-mqtt, and the one property that makes the whole
thing safe to exist — read-only by construction, because pyoxigraph's query API structurally
cannot execute an update.
"""

from __future__ import annotations

import json

import pytest

from orexis_capability_reporting import sovereign
from onboarding import mqtt as mqtt_admin

from conftest import build_agent, genesis_store


@pytest.fixture
def fern(monkeypatch):
    return build_agent("fern", genesis_store(), monkeypatch)


def reporter_of(agent):
    return next(m for m in agent.modules if m.name == "reporting")


def _ask(agent, sparql, modality="beliefs"):
    return reporter_of(agent).handle(
        sovereign.query_topic(agent.id),
        json.dumps({"modality": modality, "sparql": sparql}).encode())


def _answer(agent):
    replies = agent.sent.to(sovereign.result_topic(agent.id))
    assert replies, "the agent must answer on its own result topic"
    raw = replies[-1]
    assert isinstance(raw, dict), (
        "the answer must be handed to Agent.publish as a DICT — publish serialises, and a "
        "pre-dumped string double-encodes (found by the first live orexis-ask)")
    return raw


def test_a_select_is_answered_from_the_live_store(fern):
    took = _ask(fern, "SELECT ?v WHERE { ?a <http://example.org/orexis/sensing#slowSleepS> ?v }")
    assert took
    answer = _answer(fern)
    assert answer["rows"] and answer["rows"][0]["v"] == "600", \
        "fern's own belief, disclosed on the authorised channel"


def test_an_update_is_refused_by_the_engine_not_a_filter(fern):
    before = fern.beliefs.query(
        "SELECT ?v WHERE { ?a <http://example.org/orexis/sensing#slowSleepS> ?v }")
    _ask(fern, 'INSERT DATA { <http://example.org/x> <http://example.org/y> "stolen" }')
    answer = _answer(fern)
    assert "error" in answer, "an update must come back as the engine's own refusal"
    assert fern.beliefs.query(
        "SELECT ?v WHERE { ?a <http://example.org/orexis/sensing#slowSleepS> ?v }") == before


def test_a_question_for_another_agent_is_not_taken(fern):
    took = reporter_of(fern).handle(
        sovereign.query_topic("tomato"),
        json.dumps({"modality": "beliefs", "sparql": "SELECT * WHERE {?s ?p ?o}"}).encode())
    assert not took
    assert not fern.sent.to(sovereign.result_topic("tomato")), \
        "an agent must never speak on another's channel"


def test_a_flood_of_rows_is_capped_not_streamed(fern):
    _ask(fern, "SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
    answer = _answer(fern)
    assert len(answer["rows"]) <= reporter_of(fern).ANSWER_ROWS
    assert answer.get("truncated"), "a whole belief base exceeds the cap and must say so"


def test_the_sovereign_asks_a_modality_and_the_desires_answer(fern):
    """The third ruling of a-store-is-a-modality, on the wire: the ask names a modality, and
    the desire modality answers about wants — here, the region deduced from fern's plant —
    through the same read-only channel."""
    _ask(fern, """SELECT ?low WHERE {
        <http://example.org/orexis/world/simulation#fern_agent>
            <http://example.org/orexis#holds> ?desire .
        ?desire <http://www.w3.org/ns/ssn/forProperty>
                <http://example.org/orexis/water#SoilMoisture> ;
                <http://example.org/orexis#metWhen> ?region .
        ?region <http://www.w3.org/ns/shacl#property> ?below .
        ?below <http://www.w3.org/ns/shacl#severity>
               <http://example.org/orexis#ShouldBecome> ;
               <http://example.org/orexis#violationIs> <http://example.org/orexis#Below> ;
               <http://www.w3.org/ns/shacl#qualifiedValueShape>/<http://www.w3.org/ns/shacl#property>/<http://www.w3.org/ns/shacl#maxExclusive> ?low
    }""", modality="desires")
    answer = _answer(fern)
    assert answer["rows"] and float(answer["rows"][0]["low"]) == 0.45, \
        "the want fern's plant implies, asked of the store that owns wants"


def test_a_question_naming_no_modality_is_refused_with_the_road_spelled_out(fern):
    """No default, deliberately — the same rule as no default world: a fallback answers a
    question the asker did not ask. The refusal says how to ask, not merely no."""
    reporter_of(fern).handle(sovereign.query_topic(fern.id), b"SELECT * WHERE { ?s ?p ?o }")
    answer = _answer(fern)
    assert "error" in answer and "no default modality" in answer["error"]


def test_a_modality_the_mind_lacks_is_refused_naming_what_exists(fern):
    _ask(fern, "SELECT * WHERE { ?s ?p ?o }", modality="dreams")
    answer = _answer(fern)
    assert "error" in answer
    assert "beliefs" in answer["error"] and "desires" in answer["error"], \
        "the refusal must name the modalities this mind has"


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
