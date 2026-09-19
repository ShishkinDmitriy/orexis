"""The drift's result is predictions (#642, the-drift-is-sensings-and-its-result-is-predictions).

After every reading sensing runs each drift at the horizons its package lists, the next
reading's window first, and writes one prediction per horizon: a graph holding during its
window, typed `orexis:PredictionGraph`, carrying the predicted reading keyed as the present's
and typed with every band it may be in. The door hands the prediction holding at an instant and
never one outside its period; the records never list them. The first is the expected next
observation, dropped when its window closes with no reading.
"""
from __future__ import annotations

from datetime import timedelta

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import WORLD_GRAPH
from orexis_agent_progression.store import bindings
from orexis_capability_sensing import predictions
from conftest import build_agent, genesis_store, sensing_of, wired_sensors, write_reading
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import PREDICTION
from orexis_agent_progression.ontology import FORESEEN, RECORD

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
BELOW = "http://example.org/orexis/sensing#BelowRegion"
IN = "http://example.org/orexis/sensing#InRegion"
FERN = "http://example.org/orexis/world/simulation#fern"


def _predicted(agent, subject=FERN, observed_property=MOISTURE):
    """Every prediction the agent holds for one key: graph, window, bands."""
    graphs = predictions.graphs_of(agent.beliefs, agent.id, subject.rsplit("#", 1)[-1], observed_property)
    periods = agent.beliefs.periods()
    out = []
    for g in graphs:
        kinds = {r["k"] for r in bindings(agent.beliefs.query(
            f"SELECT ?k WHERE {{ GRAPH <{g}> {{ ?o a ?band }} ?band rdfs:subClassOf ?k }}", agent.beliefs.graphs_of(PUBLIC)))
            if r["k"].startswith("http://example.org/orexis/sensing#")}
        out.append((g, periods.get(g, (None, None)), kinds))
    return out


def test_a_reading_writes_one_prediction_per_horizon_the_first_being_the_next_window(monkeypatch):
    """The water package lists three horizons beside its drift; sensing adds the next reading's
    window first. Each is a graph holding during its window, keyed as the reading is."""
    agent = build_agent("fern", genesis_store({("fern", MOISTURE): 0.55}), monkeypatch)
    write_reading(agent, 0.55)
    rows = _predicted(agent)
    assert len(rows) == 4, [g for g, _, _ in rows]
    sensor = wired_sensors(agent)[0]
    owner = next(m for m in agent.modules if hasattr(m, "sensor_for") and m.sensor_for(sensor.subject, sensor.observes) is not None)
    horizon = owner.stale_after_s(sensor.subject, sensor.observes)
    taken = clock.now()
    (first, (opens, closes), kinds) = rows[0]
    assert abs((closes - taken).total_seconds() - horizon) < 3.0, "the first window closes where the freshness horizon runs out"
    assert opens < closes, "a window: due, then the grace"
    assert kinds == {IN}, "no width stated: the one band the rate reaches"
    ends = [c for _, (_, c), _ in rows]
    assert ends == sorted(ends) and abs((ends[-1] - taken).total_seconds() - 86400) < 3.0, "the ladder ends a day out"
    assert all(o == prev for (_, (o, _), _), prev in zip(rows[1:], ends)), "each window opens where the last closed"
    assert bindings(agent.beliefs.query(f"SELECT ?v WHERE {{ GRAPH <{first}> {{ <http://example.org/orexis#obs_fern_SoilMoisture> sosa:hasSimpleResult ?v }} }}", agent.beliefs.graphs_of(PUBLIC))), \
        "keyed as the present's reading is, with the centre the rate reaches"


def test_the_door_hands_the_prediction_holding_at_an_instant_and_the_records_never_list_it(monkeypatch):
    agent = build_agent("fern", genesis_store({("fern", MOISTURE): 0.55}), monkeypatch)
    write_reading(agent, 0.55)
    rows = _predicted(agent)
    assert agent.beliefs.graphs_of(PREDICTION, at=clock.now()) == [], "nothing holds now: the first window opens at the next reading's due"
    inside = rows[1][1][0] + timedelta(seconds=1)
    assert agent.beliefs.graphs_of(PREDICTION, at=inside) == [rows[1][0]]
    assert agent.beliefs.query(f"ASK {{ ?o sosa:hasFeatureOfInterest <{FERN}> ; sosa:resultTime ?t . FILTER(?t > NOW()) }}",
                               agent.beliefs.graphs_of(*FORESEEN, at=inside))["boolean"], \
        "a reader standing inside the window is handed the predicted reading"
    assert not set(rows[0][0] for _ in [0]) & set(agent.beliefs.graphs_of(RECORD)), "a prediction is never a record of the agent's"
    assert not any("predicted/" in g for g in agent.beliefs.graphs_of(RECORD))


def test_a_spread_beside_the_rate_and_the_instruments_noise_widen_the_bands(monkeypatch):
    """Two hundredths above the floor, with a spread and a noise stated, the far end of the
    first window may be below: the drift types its prediction with both bands, and no width
    leaves the rule."""
    st = genesis_store({("fern", MOISTURE): 0.47})
    sensor = bindings(st.query(f"SELECT ?s WHERE {{ ?s sosa:observes <{MOISTURE}> ; a sosa:Sensor }} LIMIT 1", st.graphs_of(PUBLIC)))[0]["s"]
    st.update(f"""INSERT DATA {{ GRAPH <{WORLD_GRAPH}> {{
        <{FERN}> water:driesPerDaySpread 0.05 . <{sensor}> sensing:noise 0.05 }} }}""")
    agent = build_agent("fern", st, monkeypatch)
    write_reading(agent, 0.47)
    rows = _predicted(agent)
    assert rows[0][2] == {IN, BELOW}, rows[0][2]
    assert BELOW in rows[-1][2], "a day out, the region may be left"


def test_the_next_reading_rewrites_the_ladder_and_a_closed_window_drops_the_first(monkeypatch):
    agent = build_agent("fern", genesis_store({("fern", MOISTURE): 0.55}), monkeypatch)
    write_reading(agent, 0.55)
    first = _predicted(agent)
    write_reading(agent, 0.56)
    second = _predicted(agent)
    assert len(second) == len(first) and second[0][1][1] >= first[0][1][1], "rewritten from the new reading"
    sensor = wired_sensors(agent)[0]
    sensing_of(agent).went_stale(sensor.subject, sensor.observes)
    after = _predicted(agent)
    assert len(after) == len(second) - 1 and after[0][0] == second[1][0], \
        "the first window closed with no reading: gone; the rest predict on from a stale reading"


def test_a_property_no_drift_moves_is_predicted_to_stay(monkeypatch):
    """The gardener's water butt: no drift of its own moves the level (draining is a host's),
    so its next-window prediction is the reading as it stands, stamped at the window's end."""
    STORED = "http://example.org/orexis/water#StoredLitres"
    BUTT = "http://example.org/orexis/world/loner#water_butt"
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    agent = build_agent("gardener", genesis_store({("zz", MOISTURE): 0.3, ("water_butt", STORED): 3.0}, world="loner"), monkeypatch)
    write_reading(agent, 2.5, STORED)
    graphs = predictions.graphs_of(agent.beliefs, agent.id, "water_butt", STORED)
    assert len(graphs) == 1, "the next window alone: no package lists a horizon for it"
    rows = bindings(agent.beliefs.query(f"""SELECT ?v ?t WHERE {{ GRAPH <{graphs[0]}> {{
        ?o sosa:hasFeatureOfInterest <{BUTT}> ; sosa:hasSimpleResult ?v ; sosa:resultTime ?t }} }}""", agent.beliefs.graphs_of(PUBLIC)))
    assert rows and float(rows[0]["v"]) == 2.5, "the reading, unmoved"
    _, (_, closes), _ = _predicted(agent, BUTT, STORED)[0]
    assert rows[0]["t"].startswith(closes.isoformat()[:19]), "stamped at the window's far end"
