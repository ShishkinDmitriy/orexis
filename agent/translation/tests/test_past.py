"""What happened to the agent, as a chat reads it: the journal queried where it is, its entries their union, and the
series read by a Flux the tool writes from the fields the model fills — never one the model writes."""

from __future__ import annotations

from datetime import datetime, timezone

import pyoxigraph as ox
import pytest

from agent.journal import Journal
from agent.series import HISTORY, Sink
from agent.store import NAMESPACES
from agent.translation.past import JOURNAL, ROWS, SERIES, Past

AT = datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc)


@pytest.fixture
def kept():
    journal = Journal(now=lambda: AT)
    node = ox.NamedNode("urn:uuid:one")
    journal.record(node, [ox.Triple(node, ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                                    ox.NamedNode("http://example.org/orexis/sensing#Observed"))], at=AT)
    return journal


class Store:
    """An InfluxDB as the sink reads it: every Flux it was handed kept, and `rows` answered."""

    def __init__(self, rows):
        self.asked, self.rows = [], rows

    def __call__(self, flux):
        self.asked.append(flux)
        return self.rows


def test_the_journal_is_read_where_it_is_and_newest_first(kept):
    past = Past(kept.store, None, NAMESPACES)
    assert [t["name"] for t in past.tools()] == [JOURNAL], "no series where the agent keeps none"
    found = past.call(JOURNAL, {"sparql": "SELECT ?c ?t WHERE { ?e a ?c ; prov:atTime ?t } ORDER BY DESC(?t)"})
    assert "c: sensing:Observed, t: 2026-11-02T21:00:00Z" in found, found
    assert past.call(JOURNAL, {"sparql": "SELECT * WHERE { SERVICE <http://x.example/> { ?s ?p ?o } }"}).startswith(
        "refused: it holds a SERVICE clause")
    assert past.call(SERIES, {}) is None and past.call("query", {}) is None


def test_the_series_is_read_by_the_fields_and_the_tool_writes_the_flux():
    store = Store([{"_measurement": "SoilMoisture", "sensor": "moisture_sensor_terrace",
                    "_time": datetime(2026, 10, 16, 8, 38, tzinfo=timezone.utc), "_value": 0.427}])
    past = Past(None, Sink(HISTORY, "terrace-terrace", lambda bucket, record: None, store), NAMESPACES)
    assert [t["name"] for t in past.tools()] == [SERIES]
    found = past.call(SERIES, {"measurement": "SoilMoisture", "sensor": "moisture_sensor_terrace", "start": "-7d",
                               "every": "1h", "fn": "max", "flux": "drop everything"})
    assert found == "measurement: SoilMoisture, sensor: moisture_sensor_terrace, time: 2026-10-16T08:38:00+00:00, value: 0.427"
    (flux,) = store.asked
    assert 'from(bucket: "terrace-terrace")' in flux and "range(start: -7d)" in flux
    assert 'r._measurement == "SoilMoisture"' in flux and 'r.sensor == "moisture_sensor_terrace"' in flux
    assert "aggregateWindow(every: 1h, fn: max" in flux and f"limit(n: {ROWS})" in flux
    past.call(SERIES, {"start": "2026-10-16T00:00:00Z"})
    assert 'group(columns: ["_measurement", "sensor"])' in store.asked[-1], "no measurement: each one's latest"
    assert 'time(v: "2026-10-16T00:00:00+00:00")' in store.asked[-1]


@pytest.mark.parametrize(("fields", "why"), [
    ({"measurement": "SoilMoisture", "start": "yesterday"}, "refused: a stretch's end is a duration"),
    ({"measurement": "SoilMoisture", "every": "1h) |> drop()"}, "refused: every is a duration"),
    ({"measurement": "SoilMoisture", "fn": "exec"}, "refused: fn is one of"),
])
def test_a_field_that_is_no_stretch_window_or_aggregate_is_refused_before_anything_is_read(fields, why):
    store = Store([])
    past = Past(None, Sink(HISTORY, "b", lambda bucket, record: None, store), NAMESPACES)
    assert past.call(SERIES, fields).startswith(why) and store.asked == []


def test_a_name_is_quoted_so_it_stays_a_string():
    store = Store([])
    Past(None, Sink(HISTORY, "b", lambda bucket, record: None, store), NAMESPACES).call(
        SERIES, {"measurement": 'x") |> drop(columns: ["_value"]) //'})
    assert 'r._measurement == "x\\") |> drop(columns: [\\"_value\\"]) //"' in store.asked[0]


def test_a_store_that_reads_nothing_or_refuses_says_so():
    written_only = Past(None, Sink(HISTORY, "b", lambda bucket, record: None), NAMESPACES)
    assert written_only.call(SERIES, {}) == "the history store is written here and never read"
    def refuse(flux):
        raise RuntimeError("unauthorized")
    refused = Past(None, Sink(HISTORY, "b", lambda bucket, record: None, refuse), NAMESPACES)
    assert refused.call(SERIES, {}) == "the history store would not answer: unauthorized"
