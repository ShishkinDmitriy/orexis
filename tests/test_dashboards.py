"""The health dashboard carries the story, not only the series (#125).

The BDI figures say THAT something happened — `worst_gap` climbing, `intentions_standing`
saw-toothing — and the annotations say WHAT the agent thought it was doing, in the prose its
ledger wrote for exactly this reader. Derived from the roster like every panel, so an agent
added to world.ttl gets its stream on the next `agora-onboard` with nothing to remember.
"""

from __future__ import annotations

from onboarding.dashboards import EVENT_MEASUREMENT, render_health
from onboarding.influx import bucket_name


def test_every_agent_gets_an_annotation_stream_of_its_own():
    doc = render_health("simulation")
    streams = doc["annotations"]["list"]
    assert streams, "no annotation streams were derived from the roster"
    names = [s["name"] for s in streams]
    assert len(set(names)) == len(names), "streams must be per agent, each toggleable alone"
    # every query reads that agent's own bucket — there is no union and could not be
    buckets = [s["target"]["query"].split('"')[1] for s in streams]
    agents = [n.split(" — ")[0] for n in names]
    assert buckets == [bucket_name("simulation", a) for a in agents]


def test_the_annotation_query_reads_the_events_the_writer_writes():
    """The measurement is restated here the way every other one is — so a rename in
    agent/influx_writer.py fails this visibly instead of producing markers that query
    nothing."""
    from agent.influx_writer import EVENT_MEASUREMENT as WRITTEN

    assert EVENT_MEASUREMENT == WRITTEN
    doc = render_health("simulation")
    queries = [s["target"]["query"] for s in doc["annotations"]["list"]]
    assert queries
    assert all(f'r._measurement == "{EVENT_MEASUREMENT}"' in q for q in queries)
    assert all('r._field == "text"' in q for q in queries)
