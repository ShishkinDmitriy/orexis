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

from agent.runtime import world_of
from agent.store import graphs_of, rows
from agent_old.config import REPO_ROOT
from agent_old.genesis import world_dir, worlds

OREXIS = "http://example.org/orexis#"
SOSA = "http://www.w3.org/ns/sosa/"
PUBLIC = OREXIS + "PublicGraph"

SSN_SYSTEM = "http://www.w3.org/ns/ssn/systems/"
SSN = "http://www.w3.org/ns/ssn/"
SCHEMA = "https://schema.org/"

from .influx import bucket_name

log = logging.getLogger("dashboards")

DASHBOARD_ROOT = REPO_ROOT / "infra" / "grafana" / "dashboards"

# Whatever an agent observes, with the subject it observes it for: every sensor hosted by what the
# agent acts for, which is what it listens to. The agent owns the bucket, so it is what a panel is
# keyed on; the subject is what a person reading it cares about. The unit is the sensor's own
# `schema:unitCode`.
_SENSORS_Q = f"""
SELECT DISTINCT ?agentId ?sensorId ?subjectId ?property ?unit WHERE {{
  ?agent a <{OREXIS}Agent> ; <{OREXIS}localId> ?agentId ; <{OREXIS}actsFor> ?subject .
  ?sensor <{OREXIS}localId> ?sensorId ; <{SOSA}isHostedBy> ?subject ; <{SOSA}observes> ?property .
  ?subject <{OREXIS}localId> ?subjectId .
  OPTIONAL {{ ?sensor <{SCHEMA}unitCode> ?unit }}
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


def _ranges_by_subject(store) -> dict:
    """{(subjectId, propertyIri): {"OperatingRange": (lo, hi), ...}} — empty when none stated."""
    out: dict = {}
    for r in rows(store, _RANGES_Q, graphs_of(store, PUBLIC)):
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
    store = world_of(world_dir(world))
    sensors = rows(store, _SENSORS_Q, graphs_of(store, PUBLIC))
    if not sensors:
        raise SystemExit(f"orexis-dashboards: nothing in world {world!r} observes anything")
    ranges = _ranges_by_subject(store)

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
    # What the plants are doing. The 0.1.0 agent also reported its own health, drawn in a second
    # dashboard; Agent 0.2.0 reports readings alone, so there is nothing for one to draw.
    for name, doc in (("orexis.json", render(world)),):
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
