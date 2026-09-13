"""Sensing writes the expected next observation (#631) — item 1 of
a-prediction-is-a-set-of-bands-that-widens-with-the-horizon, held to the code.

An observation is an event. Before it occurs, what is known is the window it is expected in —
due when the cadence in force makes it so, closed when the grace runs out — and the bands it may
carry: the drift's centre at the window's far end, widened by the instrument's noise and by what
the drift states beside its rate, mapped onto the subject's own bands. A world stating no width
gets the band the drift reaches alone. Written after every reading into a graph of the agent's
own, replaced by the next reading, gone when the window closes with none.
"""
from __future__ import annotations

from datetime import datetime

from orexis_agent_progression.ontology import WORLD_GRAPH
from orexis_agent_progression.store import bindings
from orexis_capability_sensing.terms import expectations_graph
from conftest import build_agent, genesis_store, sensing_of, wired_sensors, write_reading

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
BELOW = "http://example.org/orexis/sensing#BelowRegion"
IN = "http://example.org/orexis/sensing#InRegion"


def _expected(agent):
    """Every expected next observation the agent holds, as the sovereign would read it."""
    graph = expectations_graph(agent.id)
    rows = bindings(agent.beliefs.query(f"""
SELECT ?e ?subject ?property ?start ?end WHERE {{
  GRAPH <{graph}> {{
    ?e a sensing:ExpectedObservation ; sensing:expectedOf ?subject ;
       sensing:expectedProperty ?property ; dcterms:temporal ?w .
    ?w orexis:start ?start ; orexis:end ?end . }} }}"""))
    for row in rows:
        row["bands"] = " ".join(r["band"] for r in bindings(agent.beliefs.query(
            f"SELECT ?band WHERE {{ GRAPH <{graph}> {{ <{row['e']}> sensing:mayBe ?band }} }}")))
    return rows


def _kinds(agent, bands: str) -> set[str]:
    """Which of the three kinds each band in the set is a member of."""
    out = set()
    for band in bands.split():
        rows = bindings(agent.beliefs.query(f"SELECT ?k WHERE {{ <{band}> rdfs:subClassOf ?k }}"))
        out |= {r["k"] for r in rows if r["k"].startswith("http://example.org/orexis/sensing#")}
    return out


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    return build_agent("gardener", genesis_store({("zz", MOISTURE): moisture}, world="loner"), monkeypatch)


def test_the_loner_holds_one_expected_next_observation_with_a_window_and_a_band(monkeypatch):
    """After a reading mid-region the gardener expects the next one: a window from the reading's
    own instant plus the cadence in force to the grace after it, and — the loner stating no
    noise and no spread — a set with one member, the in-region band."""
    agent = _gardener(monkeypatch, 0.3)
    sensing = sensing_of(agent)
    region = sensing.region(MOISTURE)
    write_reading(agent, region.centre)
    (row,) = _expected(agent)
    assert row["subject"].endswith("#zz") and row["property"] == MOISTURE
    start, end = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
    sensor = wired_sensors(agent)[0]
    #  The module that OWNS the probe wrote it: the gardener senses two ways, and a
    #  listener's horizon is an absolute where the subscriber's follows its cadence.
    owner = next(m for m in agent.modules
                 if hasattr(m, "sensor_for") and m.sensor_for(sensor.subject, sensor.observes) is not None)
    horizon = owner.stale_after_s(sensor.subject, sensor.observes)
    assert 0 < (end - start).total_seconds() <= horizon, "a window: due, then the grace"
    assert abs((end - datetime.fromisoformat(
        bindings(agent.beliefs.query(f"""SELECT ?t WHERE {{ GRAPH <http://example.org/orexis/graph/sensed> {{
            ?o sosa:hasFeatureOfInterest <{sensor.subject}> ; sosa:resultTime ?t }} }}"""))[0]["t"])
        ).total_seconds() - horizon) < 1.0, "the window closes where the freshness horizon runs out"
    assert _kinds(agent, row["bands"]) == {IN}, "no width stated: the band the drift reaches alone"


def test_noise_and_the_rates_spread_widen_the_set(monkeypatch):
    """The simulation fern at 0.60, well inside its region: the window is a day of this world,
    ten minutes, so the rate alone takes the centre to 0.47; the instrument's noise and a spread
    beside the rate take the far end under the floor, and the set holds the in-region band and
    the one below."""
    st = genesis_store({("fern", MOISTURE): 0.60})
    fern = "http://example.org/orexis/world/simulation#fern"
    sensor = bindings(st.query(f"SELECT ?s WHERE {{ ?s sosa:observes <{MOISTURE}> ; a sosa:Sensor }} LIMIT 1"))
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{fern}> water:driesPerDaySpread 0.05 .
        <{sensor[0]["s"]}> sensing:noise 0.05 }} }}""")
    agent = build_agent("fern", st, monkeypatch)
    write_reading(agent, 0.60)
    (row,) = _expected(agent)
    assert _kinds(agent, row["bands"]) == {IN, BELOW}, row["bands"]


def test_the_expectation_is_replaced_by_the_next_reading_and_gone_when_its_window_closes(monkeypatch):
    agent = _gardener(monkeypatch, 0.3)
    region = sensing_of(agent).region(MOISTURE)
    write_reading(agent, region.centre)
    (first,) = _expected(agent)
    write_reading(agent, region.centre)
    (second,) = _expected(agent)
    assert second["e"] == first["e"], "one node per subject and property, keyed as the reading is"
    assert second["end"] >= first["end"], "the window moved with the reading"
    sensor = wired_sensors(agent)[0]
    sensing_of(agent).went_stale(sensor.subject, sensor.observes)
    assert _expected(agent) == [], "the window closed with no reading: the expectation is gone"


def test_an_expectation_never_answers_a_watch(monkeypatch):
    """The expectation is not an observation, and no shape walking a subject's observations
    reaches it: a watch on a predicted number stays open while only the expectation and an
    older reading stand. Found the other way round — the expectation named its subject in the
    observation's word, and a node stating no value passed the value constraint vacuously, so
    every such watch read as answered the moment it opened."""
    from conftest import predicted_reading, reading_of, stake_of

    agent = _gardener(monkeypatch, 0.3)
    region = sensing_of(agent).region(MOISTURE)
    write_reading(agent, region.centre)
    assert _expected(agent), "the expectation stands beside the reading"
    keeper = agent.keeper
    uri = keeper.adopt("urn:toy#Act", stake_of(agent).uri, "an act predicting a number")
    assert keeper.expect(uri, "exactly the centre plus a tenth", baseline=reading_of(agent, MOISTURE),
                         predicts=predicted_reading(agent.me.acts_for, MOISTURE, region.centre + 0.1))
    assert len(keeper.open_expectations()) == 1, "nothing has answered: the expectation is not a reading"
