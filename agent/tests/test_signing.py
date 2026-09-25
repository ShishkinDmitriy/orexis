"""A device command is signed by the agent that holds the device and opens nothing else: tampered,
expired, replayed or signed by another agent, it is refused."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent import clock
from agent.signing import TTL_S, sign, verify

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def stopped(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def test_a_signed_command_opens_once():
    key = Ed25519PrivateKey.generate()
    command = sign({"dose_ml": 500}, key)
    assert command["dose_ml"] == 500 and {"jti", "exp", "sig"} <= set(command)
    spent: set = set()
    assert verify(command, key.public_key(), spent=spent, now=NOW.timestamp())
    assert not verify(command, key.public_key(), spent=spent, now=NOW.timestamp()), "a replay opens nothing"


def test_a_tampered_expired_or_foreign_command_is_refused():
    key, other = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    command = sign({"dose_ml": 500}, key)
    assert not verify({**command, "dose_ml": 5000}, key.public_key(), spent=set(), now=NOW.timestamp())
    assert not verify(command, key.public_key(), spent=set(), now=NOW.timestamp() + TTL_S + 1)
    assert not verify(command, other.public_key(), spent=set(), now=NOW.timestamp())
    assert not verify({"dose_ml": 500}, key.public_key(), spent=set(), now=NOW.timestamp()), "unsigned"
