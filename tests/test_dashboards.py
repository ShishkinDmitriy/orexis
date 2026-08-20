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


def test_urgency_is_drawn_per_want_and_per_agent():
    """The panel that answers WHICH want is straining, not merely that one is.

    `agent_goals.hottest` carries the maximum an agent holds and cannot say whether that
    maximum is a plant's moisture or its temperature. This draws one line per (agent, WANT) —
    by the want and not by the property it is about, because a property cannot name a
    freshness want (per instrument) or a duty (per counterparty), and a panel keyed on
    property could only ever draw stakes.

    The axis is pinned 0–1 because urgency IS normalised — 0 at the region's point, 1 at the
    edge of what the subject survives — so a rescaling axis would throw away the only thing
    that makes a moisture and a temperature comparable on one canvas. That is asserted, not
    left to whoever next opens the panel in the UI.
    """
    from onboarding.dashboards import WANT_MEASUREMENT

    doc = render_health("simulation")
    panel = next((p for p in doc["panels"] if p.get("title") == "How badly each want is unmet"),
                 None)
    assert panel, "the urgency panel is not in the generated dashboard"

    agents = {t["query"].split('bucket: "')[1].split('"')[0] for t in panel["targets"]}
    assert len(agents) == len(panel["targets"]), "one target per agent — a bucket is per agent"
    for target in panel["targets"]:
        assert WANT_MEASUREMENT in target["query"]
        assert '_field == "urgency"' in target["query"]
        assert "r.want" in target["query"], \
            "lines are split by the WANT, so freshness and duties can share the axis"

    assert panel["type"] == "status-history", \
        "a row per want, coloured by heat — five agents' curves over one another answer " \
        "'which want is hot' far worse than a grid does"

    defaults = panel["fieldConfig"]["defaults"]
    assert (defaults["min"], defaults["max"]) == (0, 1), \
        "urgency is normalised; an axis that rescales hides what normalisation bought"
