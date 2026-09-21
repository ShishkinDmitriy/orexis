"""A Grafana dashboard per world, derived from that world's wiring.

  orexis-dashboards society

The same move as everything else onboarding does: the world already says which agents exist,
what each observes, and therefore which bucket holds it. A dashboard listing those by hand is a
second list to drift — and it had already drifted, since the one shipped here queried a bucket
named `sensors` that has not existed since each agent got one of its own.

**Why the output lands in `infra/grafana/` when nothing else world-specific does.** Because
Grafana is the one service that legitimately spans worlds: it is the operator's view of every
society at once, which is why it holds a read-token across all buckets. Splitting it per world
would defeat what it is for. The alternative — mounting each world's directory into Grafana —
would hand a network-facing service read access to every world's private keys, which is worse
than the tidiness is worth.

So the generated files are published into the shared service's directory, gitignored, one
subdirectory per world. With `foldersFromFilesStructure`, Grafana shows a folder per world, and a
world removed from disk simply stops having one.

Vocabulary: nothing new. The panels are built from `sensing:monitors`/`sensing:polls`, and the bucket name
comes from `onboarding.influx`, so the dashboard cannot disagree with what the agent writes to.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import argparse
import json
import logging

from agent import ratified
from agent.config import REPO_ROOT
from agent.genesis import worlds
from orexis_agent_progression.ontology import OREXIS, WORLD_GRAPH
from .namespaces import SENSING, SOSA

SSN_SYSTEM = "http://www.w3.org/ns/ssn/systems/"
SSN = "http://www.w3.org/ns/ssn/"
SCHEMA = "https://schema.org/"
SCALING = "http://example.org/orexis/scaling#"

from .influx import bucket_name

log = logging.getLogger("dashboards")

DASHBOARD_ROOT = REPO_ROOT / "infra" / "grafana" / "dashboards"

# Whatever an agent observes, with the subject it observes it for. The agent is what owns a
# bucket, so it is what a panel is keyed on; the subject is what a person reading it cares about.
_SENSORS_Q = f"""
SELECT DISTINCT ?agentId ?sensorId ?subjectId ?property ?unit WHERE {{
  ?agent a <{OREXIS}Agent> ; <{OREXIS}localId> ?agentId ; <{SENSING}polls> ?sensor .
  ?sensor <{OREXIS}localId> ?sensorId ; <{SENSING}monitors> ?subject ;
          <{SOSA}observes> ?property .
  ?subject <{OREXIS}localId> ?subjectId .
  OPTIONAL {{ ?sensor <{SCALING}quantityUnit> ?unit }}
 }}"""

# What the SUBJECT can stand, per property, from whichever ranges it states. Two predicates and
# one shape, because a range is a range: `ssn-system:OperatingRange` is where a plant does well
# and `hasSurvivalRange` is where it does not die, and a panel wants both — green inside the
# first, amber between them, red outside the second. A world that states neither gets neither,
# and the panel falls back to no opinion rather than to a moisture-shaped guess.
_RANGES_Q = f"""
SELECT DISTINCT ?subjectId ?kind ?property ?lo ?hi WHERE {{
  VALUES ?rel {{ <{SSN_SYSTEM}hasOperatingRange> <{SSN_SYSTEM}hasSurvivalRange> }}
  ?subject <{OREXIS}localId> ?subjectId ; ?rel ?range .
  ?range a ?kind ; <{SSN_SYSTEM}inCondition> ?condition .
  ?condition <{SSN}forProperty> ?property ;
             <{SCHEMA}minValue> ?lo ; <{SCHEMA}maxValue> ?hi .
 }}"""

# Written by agent.influx_writer — named here so a change there fails visibly rather than
# producing a dashboard that queries nothing.
MEASUREMENT = "soil_moisture"
FIELD = "value"
AGENT_MEASUREMENT = "agent_health"
#  One row per WANT — tagged by the want itself, not by a property, because a
#  property cannot name a freshness want (per instrument) or an obligation (per
#  counterparty). Written by whoever sees every desire, which is the deliberator.
WANT_MEASUREMENT = "agent_want"
#  What a planning pass cost and what it did with each lever. Written by the
#  deliberator from its own trace, so a dashboard and an `orexis-ask` of the same
#  agent are reading one fact.
PLANNING_MEASUREMENT = "agent_planning"
SENSOR_MEASUREMENT = "agent_sensor_health"
EVENT_MEASUREMENT = "agent_events"

# Every agent, not only the ones that observe: a market host owns a belief base and a connection
# and can go quiet exactly as loudly as a sensing agent can.
_ROSTER_Q = f"""
SELECT DISTINCT ?agentId WHERE {{ 
  ?agent a <{OREXIS}Agent> ; <{OREXIS}localId> ?agentId .
 }}"""


# QUDT unit IRI -> what Grafana calls it. Only what this project actually states; an unknown
# unit gets "none" rather than a guess, because guessing is how a temperature came to be drawn
# as 2390%.
#
# UNITLESS maps to `percentunit` — a 0-1 fraction rendered as a percentage — and that is a fact
# about THIS project rather than about the unit: soil moisture is a fraction of saturation and
# relative humidity is a fraction of one, and both are stored 0-1. A unitless quantity that was
# not a fraction would want "none", and would need saying here.
_GRAFANA_UNIT = {
    "DEG_C": "celsius",
    "UNITLESS": "percentunit",
    "PERCENT": "percent",
    "LUX": "lux",
}


def _unit_of(unit_iri: str | None) -> str:
    if not unit_iri:
        return "none"
    return _GRAFANA_UNIT.get(unit_iri.rsplit("/", 1)[-1], "none")


def _flux(bucket: str, sensor_id: str) -> str:
    """One sensor's series, and nothing else in the bucket.

    Filtered on the `sensor` tag rather than grouped by it. A bucket holds every property its
    agent records — a board sending soil moisture and air humidity sends two fractions in the
    same 0-1 range and nothing in either says which it is — so one panel per sensor is what lets
    a panel carry that sensor's UNIT and that subject's range. Grouping them into one panel is
    what made a temperature share a moisture's axis.
    """
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")\n'
            f'  |> filter(fn: (r) => r._field == "{FIELD}")\n'
            f'  |> filter(fn: (r) => r.sensor == "{sensor_id}")\n'
            "  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)")


def _steps(ranges: dict) -> list[dict]:
    """Colour by what the SUBJECT can stand, or say nothing.

    Ascending, the way Grafana reads them: red below survival, amber between survival and
    operating, green inside operating, and back out again. Both ranges earn their place — amber
    is precisely "alive but not well", which is the state worth seeing before it is red.

    A subject stating no range gets a single neutral step. The old panel hardcoded 0.25/0.4,
    which is a soil-moisture opinion applied to every property including temperature.
    """
    operating, survival = ranges.get("OperatingRange"), ranges.get("SurvivalRange")
    if not operating and not survival:
        return [{"color": "text", "value": None}]

    outer = survival or operating
    inner = operating or survival
    steps = [{"color": "red", "value": None}]
    if survival and operating:
        steps.append({"color": "orange", "value": outer[0]})
    steps.append({"color": "green", "value": inner[0]})
    if survival and operating:
        steps.append({"color": "orange", "value": inner[1]})
        steps.append({"color": "red", "value": outer[1]})
    else:
        steps.append({"color": "red", "value": inner[1]})
    return steps


def _sensor_panel(title: str, bucket: str, sensor_id: str, unit: str, ranges: dict,
                  y: int, h: int, panel_id: int, desc: str = ""):
    """One panel per sensor: the history, with the latest value in its legend.

    There is no second panel showing the current value. A stat beside the curve repeats what the
    curve's right-hand edge already says, and costs half the width that the history — the thing
    a range is interesting against — could have used. Grafana's table legend carries
    `lastNotNull`, so the number is still on screen and is still the last reading.
    """
    survival = ranges.get("SurvivalRange")
    defaults = {
        "unit": unit,
        "color": {"mode": "thresholds"},
        "thresholds": {"mode": "absolute", "steps": _steps(ranges)},
        # Draw the bands rather than only colouring the line: the question a history panel
        # answers is "was it ever outside", and a line that merely changes colour answers it
        # only where someone happens to be looking.
        "custom": {"thresholdsStyle": {"mode": "area"}, "fillOpacity": 8},
    }
    # The axis is the survival range where one is stated — what the subject can stand is the
    # interesting window, and a curve pinned to 0-1 hides a temperature entirely. Widened a
    # little so a value AT the limit is still drawn rather than clipped to the frame.
    if survival:
        span = survival[1] - survival[0]
        defaults["min"] = survival[0] - span * 0.1
        defaults["max"] = survival[1] + span * 0.1

    return {
        "id": panel_id,
        "type": "timeseries",
        "title": title,
        "description": desc,
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": h, "w": 24, "x": 0, "y": y},
        "targets": [{"refId": "A", "query": _flux(bucket, sensor_id)}],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "legend": {"showLegend": True, "displayMode": "table", "placement": "bottom",
                       "calcs": ["lastNotNull"]},
            "tooltip": {"mode": "single", "sort": "none"},
        },
    }


def _health_flux(bucket: str, measurement: str, field: str, last: bool = False) -> str:
    tail = ("  |> last()" if last
            else "  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)")
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
            f'  |> filter(fn: (r) => r._field == "{field}")\n' + tail)


def _health_panel(title: str, buckets: dict, measurement: str, field: str, kind: str,
                  unit: str, x: int, y: int, w: int, h: int, panel_id: int,
                  desc: str = "") -> dict:
    """One panel, one target per agent — because each agent owns its own bucket.

    There is no union across buckets and there could not be: an agent's token opens only its own,
    so the only client that can see all of them at once is Grafana, holding the read-only token
    minted for exactly that. See knowledge/decisions/series-and-bus-isolation.md.
    """
    return {
        "id": panel_id,
        "type": kind,
        "title": title,
        "description": desc,
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [
            {"refId": chr(ord("A") + i),
             "query": _health_flux(bucket, measurement, field, last=(kind == "stat"))}
            for i, (_, bucket) in enumerate(sorted(buckets.items()))
        ],
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}},
                        "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}}
        if kind == "timeseries" else {},
    }


def _urgency_panel(buckets: dict, y: int, panel_id: int) -> dict:
    """Every want in the world, drawn by how badly it is unmet — one line per (agent, property).

    The health panels above answer "is this society straining"; this answers WHICH WANT is
    straining, which is the question an operator actually has at 3am. `agent_goals.hottest`
    carries the maximum an agent holds and cannot say whether the maximum is one plant's
    moisture or its temperature, and `agent_desire` already carried the region and the aim —
    three curves whose gap between them a reader had to eyeball. Urgency states it.

    Grouped by the WANT rather than by the property it is about — the sovereign's correction,
    and it is what lets one graph hold every kind. A property cannot name a freshness want,
    which is per instrument, or an obligation, which is per counterparty, so a panel keyed on
    `property` could only ever draw stakes and the common currency would stay a claim. One
    target per agent, because a bucket is per agent and a token opens only its own.

    Zero to one, fixed. Urgency IS normalised — 0 at the region's point and 1 at the edge of
    what the subject survives — so an axis that rescaled itself would throw away the only thing
    that makes two properties in different units comparable on one canvas. The threshold at 1 is
    where a reading has left the envelope.
    """
    return {
        "id": panel_id,
        #  A STATUS HISTORY and not a line chart, on the sovereign's call. Five agents holding
        #  several wants each is ten curves over one another, and the question an operator has
        #  is not what shape a curve made — it is WHICH want was hot, and WHEN. A row per want,
        #  each cell coloured by its heat, answers that without reading anything.
        #
        #  What it costs is the shape: a plant drying and being watered draws a saw-tooth, and
        #  that saw-tooth says the society is working. It is still legible here as a rhythm of
        #  colour, and the per-property panels above keep the curve where the curve matters.
        "type": "status-history",
        "title": "How badly each want is unmet",
        "description": (
            "Urgency per want: 0 at the point of the region, 1 at the edge of what the subject "
            "survives. Unit-free by construction, so a moisture and a temperature are "
            "comparable on one axis — and so is a litre owed, and a look overdue. A line "
            "ABSENT is a want nobody has read: unmeasured is not satisfied, so it is drawn as "
            "a gap rather than as zero. A line pinned at 1 with no fall is a want nothing can "
            "repair — check `unactionable` beside it before looking for a fault."),
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": 9, "w": 24, "x": 0, "y": y},
        "targets": [
            {"refId": chr(ord("A") + i),
             "query": ('import "strings"\n'
                       f'from(bucket: "{bucket}")\n'
                       "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
                       f'  |> filter(fn: (r) => r._measurement == "{WANT_MEASUREMENT}")\n'
                       '  |> filter(fn: (r) => r._field == "urgency")\n'
                       "  |> aggregateWindow(every: v.windowPeriod, fn: last, "
                       "createEmpty: false)\n"
                       #  The tag is the want's own node name so it can be pasted straight
                       #  into an `orexis-ask` — and a derived want is minted as
                       #  `bounds.<who>.<property>`, so the agent sits in the MIDDLE of it and
                       #  a legend would say fern twice. Removed for DISPLAY only; what is
                       #  stored stays the name the graph knows it by.
                       #
                       #  The prefix is kept rather than dropped, because it is not always
                       #  redundant: a want the derivation minted is tagged by its ROOT, so a debt
                       #  reads `no_overdue_debts`, and whom it is owed to is `agent_debts`'s
                       #  per-counterparty row, not this panel's.
                       f'  |> map(fn: (r) => ({{ r with _field: "{agent_id}/" + '
                       f'strings.replace(v: r.want, t: ".{agent_id}.", u: ".", i: 1) }}))')}
            for i, (agent_id, bucket) in enumerate(sorted(buckets.items()))
        ],
        "fieldConfig": {"defaults": {
            "unit": "short", "min": 0, "max": 1,
            "color": {"mode": "palette-classic"},
            "thresholds": {"mode": "absolute", "steps": [
                {"color": "green", "value": None},
                {"color": "orange", "value": 0.6},
                {"color": "red", "value": 1},
            ]},
            #  `thresholdsStyle` is a line-chart option and means nothing here; a status
            #  history colours each cell by the same steps instead. Full opacity because a
            #  half-transparent cell in a grid of cells reads as a different colour.
            "custom": {"fillOpacity": 100, "lineWidth": 1},
        }, "overrides": []},
        "options": {
            #  A list, not a table: the table's `lastNotNull` and `max` columns are what a line
            #  chart needs to say where a curve ended, and a status history's right-hand edge
            #  IS where it ended — the number is under the cursor.
            "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "single", "sort": "none"},
            "showValue": "never",
            "colWidth": 0.9,
            "rowHeight": 0.9,
        },
    }


def _levers_panel(buckets: dict, y: int, panel_id: int) -> dict:
    """What the search did with each lever it looked at — and what it could not look at.

    The panels above say how much planning cost and how far it reached. This says WHY it
    reached that far, and every line is diagnostic of something recorded rather than a
    confirmation that things are fine:

    - `cycles` climbing while depth stays at 1 says the search keeps arriving back where it
      started (#258 — the cycle signature is the desire's own value, so a step that moves nothing
      else is indistinguishable from having gone nowhere);
    - `unsimulated` is a rule that RAISED, which is an error rather than a shrug;
    - `better` flat at zero while `worse` climbs is an agent whose levers exist and never help.

    Counts per pass rather than rates, because the trace holds one pass per desire and is cleared
    at the start of the next: each point is what the last pass did, not a total since boot.
    """
    fields = ("worlds", "better", "worse", "cycles", "unsimulated")
    matches = " or ".join(f'r._field == "{f}"' for f in fields)
    return {
        "id": panel_id,
        "type": "timeseries",
        "title": "What the planner did with each lever",
        "description": (
            "Per pass, not since boot — the trace holds the last pass per desire and is cleared "
            "at the start of the next. `cycles` high with depth pinned at 1 is #258; "
            "`unsimulated` is a rule that raised and is a fault, not a shrug. All zero "
            "means nothing was DELIBERATED at all — an agent whose wants are unmeasured or "
            "stale is answered by Observe before any search runs, which is a state to read "
            "beside the freshness wants rather than a planner sitting idle."),
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": y},
        "targets": [
            {"refId": chr(ord("A") + i),
             "query": (f'from(bucket: "{bucket}")\n'
                       "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
                       f'  |> filter(fn: (r) => r._measurement == "{PLANNING_MEASUREMENT}")\n'
                       f"  |> filter(fn: (r) => {matches})\n"
                       "  |> aggregateWindow(every: v.windowPeriod, fn: last, "
                       "createEmpty: false)\n"
                       #  The agent is named on every line because a bucket is per agent and
                       #  Grafana's legend shows the field, not the source it came from.
                       f'  |> map(fn: (r) => ({{ r with _field: "{agent_id}/" + r._field }}))')}
            for i, (agent_id, bucket) in enumerate(sorted(buckets.items()))
        ],
        "fieldConfig": {"defaults": {
            "unit": "short", "min": 0,
            "color": {"mode": "palette-classic"},
            "custom": {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 8,
                       "showPoints": "never"},
        }, "overrides": []},
        "options": {
            "legend": {"showLegend": True, "displayMode": "table", "placement": "bottom",
                       "calcs": ["lastNotNull", "max"]},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def _events_flux(bucket: str, agent_id: str) -> str:
    """One agent's story, shaped for Grafana's annotation reader: `_time`, `text`, `tags`.

    The caption is assembled in Flux rather than stored assembled, because the pieces are tags
    a future query may want to filter on separately — `kind` alone says adopted/satisfied/
    dropped/end-met/end-unmet or belief-taken/belief-refused, and `means` alone says
    Observe/Acquire/Apply. The `exists` guards make each tag OPTIONAL rather than defaulted:
    an intention event carries means and property, a belief event carries term, and the caption
    shows what a kind actually has instead of a placeholder for what it does not.
    """
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{EVENT_MEASUREMENT}")\n'
            '  |> filter(fn: (r) => r._field == "text")\n'
            f'  |> map(fn: (r) => ({{r with text: "{agent_id} " + r.kind\n'
            '      + (if exists r.means then " " + r.means else "")\n'
            '      + (if exists r.property then " (" + r.property + ")" else "")\n'
            '      + (if exists r.term then " " + r.term else "")\n'
            '      + ": " + r._value,\n'
            '      tags: r.kind}))\n'
            '  |> keep(columns: ["_time", "text", "tags"])')


# Annotations are per agent, so each stream can be toggled alone when one agent's story is the
# question — and each gets a colour, cycled, so markers say whose they are before they are read.
_ANNOTATION_COLOURS = ("orange", "purple", "blue", "green", "red", "yellow")


def render_health(world: str) -> dict:
    """How the agents of this world are, as opposed to what they measured.

    Derived from the roster exactly as the readings dashboard is derived from the wiring — so an
    agent added to world.ttl appears here on the next `orexis-onboard` with nothing to remember.
    """
    rows = ratified.rows(ratified.dataset(world), _ROSTER_Q)
    agents = sorted({r["agentId"] for r in rows})
    if not agents:
        raise SystemExit(f"orexis-dashboards: world {world!r} declares no agents")
    buckets = {a: bucket_name(world, a) for a in agents}

    # Ordered by what you would look at when something is wrong, top first.
    spec = [
        ("Seconds since last reading", SENSOR_MEASUREMENT, "reading_age_s", "timeseries", "s", 24, 8,
         "The gap this world's agents are actually seeing. A sawtooth is the cadence; a plateau "
         "is a board that stopped talking. Nothing appears here until a sensor has delivered "
         "once — a flat-zero readings_total below is what says it never has."),
        ("Cadence in force", SENSOR_MEASUREMENT, "cadence_acked_s", "timeseries", "s", 24, 8,
         "The board's own receipt of its rhythm (#135) — what it is actually sleeping, not what "
         "was asked. Cliffs downward are urgency (a scare or an open watch tightens in ONE "
         "step); the geometric staircase upward is the release (#139), confidence earned one "
         "comfortable reading at a time. This line diverging from what the agent believes it "
         "commanded is the #37 detector: a cleared or clamped retained command, visible."),
        ("Write failures", AGENT_MEASUREMENT, "influx_write_failures", "timeseries", "short", 12, 7,
         "Counts since boot of series writes that were caught and logged and otherwise invisible. "
         "Flat at zero is the point; any slope means readings are being lost quietly."),
        ("Belief base — triples", AGENT_MEASUREMENT, "belief_triples", "timeseries", "short", 12, 7,
         "Expected to be FLAT. sensed_writer deletes before it inserts, so an agent holds one "
         "current observation per subject however long it runs. A rising line means something "
         "started appending."),
        ("Belief base — on disk", AGENT_MEASUREMENT, "belief_bytes", "timeseries", "bytes", 12, 7,
         "RocksDB compacts on its own schedule, so this is lumpier than the triple count and "
         "should still be bounded."),
        ("Reconnects", AGENT_MEASUREMENT, "link_reconnects", "timeseries", "short", 12, 7,
         "Since boot. A marginal link shows here before it shows anywhere else."),
        ("Uptime", AGENT_MEASUREMENT, "uptime_s", "stat", "s", 12, 5,
         "Resets to zero on restart, which is how a crash-looping agent announces itself."),
        ("Readings heard", SENSOR_MEASUREMENT, "readings_total", "stat", "short", 12, 5,
         "Since boot, per sensor. Zero on a sensing agent means its board has never once been "
         "heard from — a different fault from one that went quiet."),
        # The BDI series. Contributed by the desire and intention modules through `reports()`,
        # so an agent without those capabilities simply has no line here — the supplier's
        # absence from these panels is itself a reading, not a gap in the dashboard.
        ("Worst gap", AGENT_MEASUREMENT, "worst_gap", "timeseries", "short", 24, 8,
         "|gap| over every property the agent wants held: 0 at the point of its region, 1 at "
         "the edge of what its subject survives. THE line to watch — a society doing its job "
         "keeps everyone's low, and one agent's climb is the story of a round before it opens. "
         "Absent until that agent's sensors have delivered once: unmeasured is not zero."),
        ("Standing intentions", AGENT_MEASUREMENT, "intentions_standing", "timeseries", "short", 12, 7,
         "Commitments adopted and not yet resolved. Saw-toothing with rounds is health; a "
         "plateau above zero is an agent waiting on a world that has stopped answering."),
        ("Oldest standing intention", AGENT_MEASUREMENT, "oldest_intention_s", "timeseries", "s", 12, 7,
         "How long the oldest open commitment has stood. The failure this catches is invisible "
         "everywhere else precisely because nothing is happening: a bid whose round vanished, a "
         "look whose board went quiet. Compare intention:patienceS — past it, the next adoption "
         "supersedes."),
        ("Steps not paying", AGENT_MEASUREMENT, "steps_suspect", "stat", "short", 12, 5,
         "Above zero, an agent's graph claims a movement the world keeps refusing: its acts "
         "succeed (claims arrive) and the property never moves as promised, suspectAfter "
         "times running. The false-knowledge flag — see #131. What to do about it is a "
         "decision, which is why this flags and nothing auto-retracts."),
        ("Seconds spent planning", PLANNING_MEASUREMENT, "seconds", "timeseries", "s", 12, 7,
         "What a reporting tick's planning cost, summed over every desire. Worth watching for a "
         "reason that is not performance: reporting an agent's state RE-PLANS every desire it "
         "holds, so this is the price of being asked what you want, paid on top of the "
         "planning done to decide. Divide by `worlds` beside it before blaming the shape "
         "checker — a pass that built ten worlds and one that built one are not comparable. "
         "Zero means no search ran: a want nobody has read is answered by looking, before "
         "any planning happens."),
        ("Depth reached", PLANNING_MEASUREMENT, "deepest", "timeseries", "short", 12, 7,
         "Steps in the longest path the search considered. PINNED AT 1 is the signature of two "
         "recorded limits at once (#254, #258): a rule's CONSTRUCTs run against the store "
         "rather than the world, and the cycle signature is the desire's own value, so a step "
         "that moves nothing else looks like somewhere already reached. Above 1 means a chain "
         "was genuinely tried. Zero means nothing was weighed at all."),
        ("Desires held", AGENT_MEASUREMENT, "desires", "stat", "short", 12, 5,
         "How many properties this agent wants held — deduced from what its subject states, so "
         "a change here means the WORLD changed, not the agent. Zero on an agent that should "
         "want things means its plant's ranges stopped deriving."),
    ]

    panels, y, pid = [], 0, 1
    for title, measurement, field, kind, unit, w, h, desc in spec:
        panels.append(_health_panel(title, buckets, measurement, field, kind, unit,
                                    x=0 if w == 24 else (pid % 2) * 12, y=y, w=w, h=h,
                                    panel_id=pid, desc=desc))
        pid += 1
        y += h if w == 24 else (h if pid % 2 else 0)

    #  Last, and full width, because it is the panel to read FIRST: everything above says how
    #  hard the society is working, and this says what it is working on.
    panels.append(_urgency_panel(buckets, y=y, panel_id=pid))
    pid += 1
    y += 9

    #  Beneath it, because the order is the reading order: what is wanted, then what was done
    #  about it and why so little.
    panels.append(_levers_panel(buckets, y=y, panel_id=pid))
    pid += 1
    y += 8

    # The story over the series (#125): each agent's intention transitions, drawn as
    # annotations across every panel — `worst_gap` climbing with an `adopted Acquire` marker
    # at the knee is the debugging view the ledger exists to make possible. The prose is the
    # `becauseOf` text, projected into the agent's own bucket by its reporting capability, so
    # this grants nothing: Grafana's read token could already see it.
    annotations = [
        {"name": f"{agent} — intentions",
         "datasource": {"type": "influxdb", "uid": "influxdb"},
         "enable": True,
         "hide": False,
         "iconColor": _ANNOTATION_COLOURS[i % len(_ANNOTATION_COLOURS)],
         "target": {"refId": "A", "query": _events_flux(bucket, agent)}}
        for i, (agent, bucket) in enumerate(sorted(buckets.items()))
    ]

    return {
        "uid": f"orexis-{world}-health"[:40],
        "title": f"Orexis — {world} health",
        "tags": ["orexis", world, "health"],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "1m",
        "time": {"from": "now-6h", "to": "now"},
        "annotations": {"list": annotations},
        "panels": panels,
    }


def _ranges_by_subject(ds) -> dict:
    """{(subjectId, propertyIri): {"OperatingRange": (lo, hi), ...}} — empty when none stated."""
    out: dict = {}
    for r in ratified.rows(ds, _RANGES_Q):
        kind = r["kind"].rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        if kind not in ("OperatingRange", "SurvivalRange"):
            continue
        out.setdefault((r["subjectId"], r["property"]), {})[kind] = (float(r["lo"]),
                                                                     float(r["hi"]))
    return out


def render(world: str) -> dict:
    """One panel per sensor: its history, with the latest reading in the legend.

    Per sensor rather than per agent, which is the whole of the fix. An agent's bucket holds
    every property it records, so one panel per agent drew a temperature and two fractions on
    one axis under one unit — a 23.9 degree reading rendered as 2390%. A sensor observes ONE
    property, states ONE unit, and its subject states the range that property should sit in, so
    a panel keyed on the sensor can be right about all three.
    """
    ds = ratified.dataset(world)
    sensors = ratified.rows(ds, _SENSORS_Q)
    if not sensors:
        raise SystemExit(f"orexis-dashboards: nothing in world {world!r} observes anything")
    ranges = _ranges_by_subject(ds)

    panels, y, pid = [], 0, 1
    for row in sorted(sensors, key=lambda r: (r["subjectId"], r["sensorId"])):
        bucket = bucket_name(world, row["agentId"])
        unit = _unit_of(row.get("unit"))
        prop = row["property"].rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        stated = ranges.get((row["subjectId"], row["property"]), {})
        told = ", ".join(f"{k.replace('Range', '').lower()} {v[0]:g}-{v[1]:g}"
                         for k, v in sorted(stated.items())) or "no range stated"
        desc = (f"{row['sensorId']} observes {prop} of {row['subjectId']}, in {unit}. "
                f"Bands: {told}. Both come from the world, never from this file.")

        panels.append(_sensor_panel(f"{row['subjectId']} — {prop}", bucket, row["sensorId"],
                                    unit, stated, y=y, h=8, panel_id=pid, desc=desc))
        pid += 1
        y += 8

    return {
        "uid": f"orexis-{world}"[:40],
        "title": f"Orexis — {world}",
        "tags": ["orexis", world],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "panels": panels,
    }


def generate(world: str) -> None:
    out_dir = DASHBOARD_ROOT / world
    out_dir.mkdir(parents=True, exist_ok=True)
    # Two dashboards, because they answer different questions and are looked at at different
    # times: one is what the plants are doing, the other is whether the society reporting it is
    # still working. Mixing them would put a flat-zero failure count next to a moisture curve.
    for name, doc in (("orexis.json", render(world)), ("health.json", render_health(world))):
        out = out_dir / name
        out.write_text(json.dumps(doc, indent=2) + "\n")
        out.chmod(0o644)
        log.info("  wrote %s (%d panels)", out.relative_to(REPO_ROOT), len(doc["panels"]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-dashboards",
        description="Generate this world's Grafana dashboard from its own wiring.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
