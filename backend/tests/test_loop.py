"""Tests for the round-runner's cooldown gate (pure, no MQTT)."""

from agora.loop import due


def test_first_round_is_due():
    assert due(last_run_ts=0.0, now=100.0, cooldown_s=30.0)


def test_within_cooldown_is_not_due():
    assert not due(last_run_ts=100.0, now=120.0, cooldown_s=30.0)


def test_after_cooldown_is_due():
    assert due(last_run_ts=100.0, now=131.0, cooldown_s=30.0)


def test_exactly_at_cooldown_is_due():
    assert due(last_run_ts=100.0, now=130.0, cooldown_s=30.0)
