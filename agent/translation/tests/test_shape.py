"""What a person may fill, read off a node shape: each field's schema by its datatype or the choices of its class, the
term a filled value is taken as, and the tool the model calls where nothing fits."""

from __future__ import annotations

from agent.translation.shape import NOTHING, Field, nothing_tool, schema_of, term_of, tool

XSD = "http://www.w3.org/2001/XMLSchema#"
LISTING = Field("http://example.org/v#listing", None, "http://example.org/v#Listing", True, "which listing",
                (("the flat", "http://example.org/v#flat"),))
AT = Field("http://example.org/v#at", XSD + "dateTime", None, True, "when")
LITRES = Field("http://example.org/v#litres", XSD + "integer", None, False, "")


def test_a_fields_schema_is_its_datatypes_or_the_labels_of_its_class():
    assert schema_of(LISTING) == {"type": "string", "enum": ["the flat"], "description": "which listing"}
    assert schema_of(AT) == {"type": "string", "description": "when; an instant, ISO 8601 with its offset"}
    assert schema_of(LITRES) == {"type": "integer"}
    assert tool("asked", "a question", (LISTING, LITRES))["input_schema"]["required"] == ["listing"]


def test_a_filled_value_is_the_term_its_field_takes_or_none():
    assert term_of(LISTING, "the flat").value == "http://example.org/v#flat"
    assert term_of(LISTING, "a flat nobody states") is None, "a label the world does not state is no value"
    assert term_of(AT, "2026-11-02T18:00:00+00:00").datatype.value == XSD + "dateTime"
    assert term_of(LITRES, "many") is None and term_of(LITRES, "3").value == "3"


def test_the_tool_where_nothing_fits_says_why():
    assert nothing_tool()["name"] == NOTHING == "nothing_fits"
    assert nothing_tool()["input_schema"]["required"] == ["why"]
