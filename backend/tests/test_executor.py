"""Tests for the executor (grant -> bounded command), no MQTT needed."""

import pytest

from agora.clearing import Grant
from agora.executor import Executor


def grant(jti="j1", sub="fern", amount_l=0.64) -> Grant:
    return Grant(sub=sub, scope=f"actuate:valve/{sub}", amount_l=amount_l, debit=0.3, round_id="R-1", jti=jti)


def collector():
    calls = []
    return calls, (lambda topic, payload: calls.append((topic, payload)))


def test_command_shapes_ml_and_seconds():
    _, pub = collector()
    exe = Executor(pub, ml_per_second=10.0)
    cmd = exe.command_for(grant(amount_l=0.64))  # 640 ml
    assert cmd.ml == 640.0
    assert cmd.seconds == 64.0  # 640 / 10
    assert cmd.scope == "actuate:valve/fern"


def test_hard_dose_cap():
    _, pub = collector()
    exe = Executor(pub, ml_per_second=10.0, max_dose_ml=500.0)
    cmd = exe.command_for(grant(amount_l=5.0))  # 5000 ml requested
    assert cmd.ml == 500.0  # capped at the edge, regardless of the grant


def test_settle_publishes_to_valve_topic():
    calls, pub = collector()
    exe = Executor(pub)
    exe.settle(grant(sub="tomato", jti="jx"))
    topic, payload = calls[0]
    assert topic == "actuators/tomato/valve"
    assert payload["jti"] == "jx"
    assert payload["plant"] == "tomato"


def test_single_use_rejects_replay():
    calls, pub = collector()
    exe = Executor(pub)
    exe.settle(grant(jti="dup"))
    with pytest.raises(ValueError, match="replay"):
        exe.settle(grant(jti="dup"))
    assert len(calls) == 1  # the second one never published


def test_settle_all_one_command_per_grant():
    calls, pub = collector()
    exe = Executor(pub)
    cmds = exe.settle_all([grant(jti="a", sub="fern"), grant(jti="b", sub="tomato")])
    assert {c.plant for c in cmds} == {"fern", "tomato"}
    assert len(calls) == 2
