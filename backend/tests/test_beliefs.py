"""Tests for the attested-belief SPARQL-result parser (no Fuseki needed)."""

from agora.beliefs import _parse_current_state


def _binding(value: str, band_uri: str) -> dict:
    return {
        "results": {
            "bindings": [
                {
                    "value": {"type": "literal", "value": value},
                    "band": {"type": "uri", "value": band_uri},
                }
            ]
        }
    }


def test_parses_value_and_band_local_name():
    result = _parse_current_state(_binding("0.18", "http://example.org/agora#LOW"))
    assert result == (0.18, "LOW")


def test_band_from_slash_uri():
    result = _parse_current_state(_binding("0.42", "http://example.org/agora/OK"))
    assert result == (0.42, "OK")


def test_no_bindings_is_none():
    assert _parse_current_state({"results": {"bindings": []}}) is None
    assert _parse_current_state({}) is None
