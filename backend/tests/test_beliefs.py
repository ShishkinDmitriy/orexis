"""Tests for the attested-measurement SPARQL-result parser (no Fuseki needed)."""

from agora.beliefs import _parse_moisture


def _binding(value: str) -> dict:
    return {"results": {"bindings": [{"value": {"type": "literal", "value": value}}]}}


def test_parses_value():
    assert _parse_moisture(_binding("0.18")) == 0.18


def test_no_bindings_is_none():
    assert _parse_moisture({"results": {"bindings": []}}) is None
    assert _parse_moisture({}) is None
