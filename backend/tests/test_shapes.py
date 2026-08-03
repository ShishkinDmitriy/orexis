"""SHACL — the constitution as code, one shapes module per capability.

The interesting property is that the rules are *capability-aware*: a shape applies to an agent
only if the world derived that capability for it. So an agent on a push-mode board is never
asked for a cadence it could not apply, and one on a pull board is required to have it.
"""

import pytest
import rdflib
from pyshacl import validate

from agora.ontology import MODULE_FILES, WORLD_GRAPH, beliefs_graph

from conftest import GENESIS_DIR, ONTOLOGY_DIR, RULES_DIR, SHAPES_DIR, genesis_dataset


def _flatten(ds: rdflib.Dataset) -> rdflib.Graph:
    """The world + every agent's beliefs as one graph, which is what validation sees."""
    data = rdflib.Graph()
    for triple in ds.graph(rdflib.URIRef(WORLD_GRAPH)):
        data.add(triple)
    for agent in ("fern", "tomato", "succulent", "supplier"):
        for triple in ds.graph(rdflib.URIRef(beliefs_graph(agent))):
            data.add(triple)
    return data


def _conforms(data: rdflib.Graph) -> bool:
    ontology, shapes = rdflib.Graph(), rdflib.Graph()
    for name in MODULE_FILES:
        ontology.parse(ONTOLOGY_DIR / f"{name}.ttl", format="turtle")
        if (SHAPES_DIR / f"{name}.ttl").exists():
            shapes.parse(SHAPES_DIR / f"{name}.ttl", format="turtle")
    conforms, _, _ = validate(data, shacl_graph=shapes, ont_graph=ontology,
                              inference="rdfs", advanced=True)
    return conforms


def _mutate(update: str) -> rdflib.Graph:
    """Apply a change to the seeded belief base and re-validate the result."""
    ds = genesis_dataset()
    ds.update("PREFIX ag: <http://example.org/agora#>\n" + update)
    return _flatten(ds)


# --- the world we actually ship --------------------------------------------

def test_genesis_conforms():
    assert _conforms(_flatten(genesis_dataset()))


# --- capability-conditional rules ------------------------------------------

def test_polling_agent_must_state_a_cadence():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS ?v }} }}"""))


def test_polling_agent_must_state_a_freshness_limit():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:maxReadingAgeS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:maxReadingAgeS ?v }} }}"""))


def test_cadence_may_not_be_slower_when_thirsty():
    # watching LESS closely exactly when in trouble inverts the whole policy
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS 30 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:fastSleepS 800 }} }}
        WHERE  {{}}"""))


def test_nobody_may_sleep_past_the_constitutional_ceiling():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:slowSleepS 600 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:slowSleepS 5000 }} }}
        WHERE  {{}}"""))


def test_inverted_band_is_not_a_band():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:bandLow 0.35 }} }}
        INSERT {{ GRAPH <{beliefs_graph("fern")}> {{ ag:fern_agent ag:bandLow 0.90 }} }}
        WHERE  {{}}"""))


def test_bidder_must_have_a_valuation():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("tomato")}> {{ ag:tomato_agent ag:maxValuePerL ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("tomato")}> {{ ag:tomato_agent ag:maxValuePerL ?v }} }}"""))


def test_host_must_say_how_long_it_waits_for_bids():
    # without a window a round never closes
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{beliefs_graph("supplier")}> {{ ag:supplier ag:bidWindowS ?v }} }}
        WHERE  {{ GRAPH <{beliefs_graph("supplier")}> {{ ag:supplier ag:bidWindowS ?v }} }}"""))


def test_the_supplier_is_not_asked_for_a_cadence():
    """It composed no perception capability, so the polling rules simply do not apply to it."""
    assert _conforms(_flatten(genesis_dataset()))  # it has no cadence, and that is fine


# --- the world must be coherently wired ------------------------------------

def test_sensor_must_state_how_it_is_driven():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ?m }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:senseMode ?m }} }}"""))


def test_pull_sensor_must_state_a_command_topic():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:commandTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:commandTopic ?t }} }}"""))


def test_sensor_must_state_where_it_publishes():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:readingTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:moisture_sensor_fern ag:readingTopic ?t }} }}"""))


def test_valve_must_carry_its_calibration():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:valve_fern ag:maxDoseMl ?v }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:valve_fern ag:maxDoseMl ?v }} }}"""))


def test_a_plant_may_not_hold_a_desire():
    """The target belongs to an agent's beliefs; a plant that held one would be a category error."""
    assert not _conforms(_mutate(f"""
        INSERT {{ GRAPH <{WORLD_GRAPH}> {{ ag:fern ag:hasTarget 0.55 }} }} WHERE {{}}"""))


def test_market_must_state_all_three_channels():
    assert not _conforms(_mutate(f"""
        DELETE {{ GRAPH <{WORLD_GRAPH}> {{ ag:barrel1_market ag:voucherTopic ?t }} }}
        WHERE  {{ GRAPH <{WORLD_GRAPH}> {{ ag:barrel1_market ag:voucherTopic ?t }} }}"""))
