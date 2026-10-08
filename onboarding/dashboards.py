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

Vocabulary: nothing new. The panels are built from what each sensor `sosa:observes`, the bucket
name comes from `onboarding.influx` and the measurement and the tags from `agent.sensing.events` —
sensing's, since sensing contributes the observation — so the dashboard cannot disagree with where
the agent writes or under what name. A sensor and a subject go by the local names of their IRIs
(`tag_of`), as sensing tags them; keyed by a stated `orexis:localId` instead, the greenhouse — whose
devices the society names by their topics — read as observing nothing and got no readings
dashboard (#885).

**Steps have no panel yet.** Execution writes a step taken and how it ended under
`agent.execution.events.MEASUREMENT`, tagged by action, want and parameter. A panel for them would
be keyed on the actions an agent may take — read off the world's action graphs, as sensors are
here — and draw `taken` and `landed` as events rather than a line, which is a panel type and a
query shape this module does not build.

**A DASHBOARD PER PACKAGE draws the agents' health** (`<package>.json`), for a world that is
`onboarding:monitored` and for no other: what each package reports, learnt by importing the
packages' `events.py` and reading every event class that names a measurement — and the runtime's
own, in `agent.runtime` — so no list of metrics is kept here and adding an event that reports draws
it. One for the runtime and one for each package some agent of the world loads that reports, each
linked to the others by the tags they share; a ROW PER MEASUREMENT, in the order the package declares
its events, each panel described by the event's own docstring; the AGENT is every dashboard's
variable, picking whose bucket every panel reads, carried from one dashboard to the next. A counted
event is a panel of how many and of each flag, summed per window, and one per value, drawing its
mean, its max and its sum; its levels are a panel per unit, their last per window — each field of a
point the agent writes drawn by exactly one panel, which the terrace's test holds.

See knowledge/domain/onboarding/onboarding.md.
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging

from agent import runtime as the_runtime
from agent.metrics import FLAG, LEVEL, VALUE, counted, fields_of, measurement, reported
from agent.runtime import KERNEL, every_package
from agent.sensing.events import FIELD, measurement_of, tag_of
from agent.series import METRICS
from agent.store import graphs_of, rows
from . import installation, reading
from .worlds import REPO_ROOT
from .worlds import world_dir, worlds

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
# agent acts for, which is what it listens to. The agent owns the bucket, so its id — the one short
# string a process is handed — is what a panel is keyed on; the sensor and the subject go by the
# local names of their IRIs, as sensing tags them (`tag_of`), and no `orexis:localId` is asked of
# either, since a world need not state one (#885). The unit is the sensor's own `schema:unitCode`.
_SENSORS_Q = f"""
SELECT DISTINCT ?agentId ?sensor ?subject ?property ?unit WHERE {{
  ?agent a <{OREXIS}Agent> ; <{OREXIS}localId> ?agentId ; <{OREXIS}actsFor> ?subject .
  ?sensor <{SOSA}isHostedBy> ?subject ; <{SOSA}observes> ?property .
  OPTIONAL {{ ?sensor <{SCHEMA}unitCode> ?unit }}
 }}"""

# What the SUBJECT can stand, per property, from whichever ranges it states. Two predicates and
# one shape, because a range is a range: `ssn-system:OperatingRange` is where a plant does well
# and `hasSurvivalRange` is where it does not die, and a panel wants both — green inside the
# first, amber between them, red outside the second. A world that states neither gets neither,
# and the panel falls back to no opinion rather than to a moisture-shaped guess.
_RANGES_Q = f"""
SELECT DISTINCT ?subject ?kind ?property ?lo ?hi WHERE {{
  VALUES ?rel {{ <{SSN_SYSTEM}hasOperatingRange> <{SSN_SYSTEM}hasSurvivalRange> }}
  ?subject ?rel ?range .
  ?range a ?kind ; <{SSN_SYSTEM}inCondition> ?condition .
  ?condition <{SSN}forProperty> ?property ;
             <{SCHEMA}minValue> ?lo ; <{SCHEMA}maxValue> ?hi .
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
    "V": "volt",                 # a battery's voltage, the terrace's LiPo
    "HectoPA": "pressurehpa",    # the air's pressure, the terrace's BME280
}


def _unit_of(unit_iri: str | None) -> str:
    if not unit_iri:
        return "none"
    return _GRAFANA_UNIT.get(unit_iri.rsplit("/", 1)[-1], "none")


def _flux(bucket: str, sensor_id: str, measurement: str) -> str:
    """One sensor's series, and nothing else in the bucket.

    The measurement is the observed property's, asked of `agent.sensing.history` — the writer — so the
    panel and the point cannot name it two ways; the terrace's test holds the two together.
    Filtered on the `sensor` tag rather than grouped by it. A bucket holds every property its
    agent records — a board sending soil moisture and air humidity sends two fractions in the
    same 0-1 range and nothing in either says which it is — so one panel per sensor is what lets
    a panel carry that sensor's UNIT and that subject's range. Grouping them into one panel is
    what made a temperature share a moisture's axis.
    """
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{measurement}")\n'
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


def _sensor_panel(title: str, bucket: str, sensor_id: str, measurement: str, unit: str,
                  ranges: dict, y: int, h: int, panel_id: int, desc: str = ""):
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
        "targets": [{"refId": "A", "query": _flux(bucket, sensor_id, measurement)}],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "legend": {"showLegend": True, "displayMode": "table", "placement": "bottom",
                       "calcs": ["lastNotNull"]},
            "tooltip": {"mode": "single", "sort": "none"},
        },
    }


def _ranges_by_subject(store) -> dict:
    """{(subjectIri, propertyIri): {"OperatingRange": (lo, hi), ...}} — empty when none stated."""
    out: dict = {}
    for r in rows(store, _RANGES_Q, graphs_of(store, PUBLIC)):
        kind = r["kind"].rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        if kind not in ("OperatingRange", "SurvivalRange"):
            continue
        out.setdefault((r["subject"], r["property"]), {})[kind] = (float(r["lo"]),
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
    store = reading.world(world_dir(world))
    sensors = rows(store, _SENSORS_Q, graphs_of(store, PUBLIC))
    if not sensors:
        raise SystemExit(f"orexis-dashboards: nothing in world {world!r} observes anything")
    ranges = _ranges_by_subject(store)

    panels, y, pid = [], 0, 1
    for row in sorted(sensors, key=lambda r: (tag_of(r["subject"]), tag_of(r["sensor"]))):
        bucket = bucket_name(world, row["agentId"])
        sensor_id, subject_id = tag_of(row["sensor"]), tag_of(row["subject"])
        unit = _unit_of(row.get("unit"))
        prop = row["property"].rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        stated = ranges.get((row["subject"], row["property"]), {})
        told = ", ".join(f"{k.replace('Range', '').lower()} {v[0]:g}-{v[1]:g}"
                         for k, v in sorted(stated.items())) or "no range stated"
        desc = (f"{sensor_id} observes {prop} of {subject_id}, in {unit}. "
                f"Bands: {told}. Both come from the world, never from this file.")

        panels.append(_sensor_panel(f"{subject_id} — {prop}", bucket, sensor_id,
                                    measurement_of(row["property"]), unit, stated,
                                    y=y, h=8, panel_id=pid, desc=desc))
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


#  THE DASHBOARD'S ONE VARIABLE: whose metrics bucket every panel reads.
AGENT_VARIABLE = "agent"


def reporting(world: str) -> list[tuple[str, list[type]]]:
    """What the agents of `world` report, by who reports it: the runtime's own, then each package
    some agent of the world loads whose `events.py` has an event that reports, in the order an agent
    loads them — read off the event classes themselves, so this file names no metric."""
    #  WHAT AN AGENT RUNS IS ITS ROLES', declared in its own self graph, which a world's store does not
    #  hold — so each agent is booted as its container boots it, and the packages are those SOME agent
    #  of the world loads.
    loaded = reading.loaded(world_dir(world))
    out = [("runtime", reported(the_runtime))]
    for package in every_package():
        if package in loaded and (KERNEL / package / "events.py").exists():
            said = reported(importlib.import_module("agent." + package.replace("/", ".") + ".events"))
            if said:
                out.append((package, said))
    return out


def _metric_flux(bucket: str, measurement: str, fields: tuple[str, ...] = (), fn: str = "last") -> str:
    """One measurement's figures — every field, or those named — aggregated per window by `fn`. Every
    tag stays in the group, so a search is drawn a line per outcome and per desire."""
    only = ("\n  |> filter(fn: (r) => " + " or ".join(f'r._field == "{f}"' for f in fields) + ")") if fields else ""
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{measurement}"){only}\n'
            f"  |> aggregateWindow(every: v.windowPeriod, fn: {fn}, createEmpty: false)")


def _drawn(bucket: str, event: type) -> list[tuple[str, list[str], str, str]]:
    """The panels one event class is drawn in, as (title, queries, unit, description): its levels, a
    panel per unit; then, where it is counted, how many and its flags; then a panel per value."""
    name, out = measurement(event), []
    about = " ".join((event.__doc__ or "").split())
    flags, levels = fields_of(event, FLAG), fields_of(event, LEVEL)
    for unit, these in (("none", [f for f in levels if not f.endswith("_s")]), ("s", [f for f in levels if f.endswith("_s")])):
        if these:
            out.append((", ".join(these), [_metric_flux(bucket, name, tuple(these))], unit,
                        f"{about} As each stood last in a window."))
    if not counted(event):
        return out
    out.append(("how many" + (f", {', '.join(flags)}" if flags else ""),
                [_metric_flux(bucket, name, ("count", *flags), fn="sum")], "none",
                f"{about} How many happened per window" + (f", and of them how many were {', '.join(flags)}"
                                                           if flags else "") + "."))
    for value in fields_of(event, VALUE):
        out.append((value,
                    [_metric_flux(bucket, name, (f"{value}_mean",), fn="mean"),
                     _metric_flux(bucket, name, (f"{value}_max",), fn="max"),
                     _metric_flux(bucket, name, (f"{value}_sum",), fn="sum")],
                    "s" if value.endswith("_s") else "none",
                    f"{about} `{value}`: its mean and its max over each window, and its sum."))
    return out


def _health_panel(title: str, queries: list[str], unit: str, x: int, y: int, panel_id: int, desc: str) -> dict:
    return {
        "id": panel_id, "type": "timeseries", "title": title, "description": desc,
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": 7, "w": 8, "x": x, "y": y},
        "targets": [{"refId": chr(ord("A") + i), "query": q} for i, q in enumerate(queries)],
        "fieldConfig": {"defaults": {"unit": unit, **({"decimals": 0} if unit == "none" else {})}, "overrides": []},
        "options": {"legend": {"showLegend": True, "displayMode": "table", "placement": "bottom",
                               "calcs": ["lastNotNull"]},
                    "tooltip": {"mode": "multi", "sort": "none"}},
    }


def health_file(package: str) -> str:
    """The file a package's dashboard is written to: its name, a member's family and member joined."""
    return package.replace("/", "-") + ".json"


def render_health(world: str) -> list[tuple[str, dict]]:
    """What the world's agents report of how they are doing, a dashboard per package that reports —
    the runtime's first — as (file, dashboard): a row per measurement, and the agent a variable every
    panel reads `<world>-${agent}-metrics` by."""
    from .compose import roster

    agents = roster(world)
    bucket = bucket_name(world, "${" + AGENT_VARIABLE + "}", METRICS)
    first = agents[0] if agents else ""
    variable = {"name": AGENT_VARIABLE, "label": "agent", "type": "custom", "query": ",".join(agents),
                "current": {"text": first, "value": first},
                "options": [{"text": a, "value": a, "selected": a == first} for a in agents],
                "multi": False, "includeAll": False, "hide": 0}
    out = []
    for package, reported in reporting(world):
        panels, y, pid = [], 0, 1
        for event in reported:
            panels.append({"id": pid, "type": "row", "title": measurement(event), "collapsed": False,
                           "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []})
            pid, y = pid + 1, y + 1
            drawn = _drawn(bucket, event)
            for i, (title, queries, unit, desc) in enumerate(drawn):
                panels.append(_health_panel(f"{measurement(event)} — {title}", queries, unit, x=8 * (i % 3),
                                            y=y + 7 * (i // 3), panel_id=pid,
                                            desc=desc + f" Said by {package}'s own events, never by this file."))
                pid += 1
            y += 7 * ((len(drawn) + 2) // 3)
        out.append((health_file(package), {
            "uid": f"orexis-{world}-{package.replace('/', '-')}"[:40],
            "title": f"Orexis — {world} — {package}",
            "tags": ["orexis", world, "health"],
            "timezone": "browser",
            "schemaVersion": 39,
            "refresh": "1m",
            "time": {"from": "now-6h", "to": "now"},
            "links": [{"type": "dashboards", "title": "packages", "tags": ["orexis", world, "health"],
                       "asDropdown": True, "includeVars": True, "keepTime": True}],
            "templating": {"list": [dict(variable)]},
            "panels": panels,
        }))
    return out


def generate(world: str) -> None:
    out_dir = DASHBOARD_ROOT / world
    # What the plants are doing where anything observes them, and how the agents are doing where the
    # world is monitored — a world whose agents observe nothing, the allotment's, may still be; one
    # that is not monitored has no health dashboard, and a stale one from before is taken away.
    docs = []
    store = reading.world(world_dir(world))
    if rows(store, _SENSORS_Q, graphs_of(store, PUBLIC)):
        docs.append(("orexis.json", render(world)))
    else:
        log.info("  nothing in %s observes anything — no readings dashboard", world)
    if METRICS in installation.purposes(world):
        docs += render_health(world)
    else:
        log.info("  %s is not monitored — no health dashboards", world)
    #  A HEALTH DASHBOARD NOT WRITTEN NOW IS STALE — a package no longer loaded, a world no longer
    #  monitored, or the one `health.json` a world had before a dashboard was a package's — and goes.
    written = {name for name, _ in docs}
    for name in ["health.json", *(health_file(p) for p in ("runtime", *every_package()))]:
        if name not in written and (stale := out_dir / name).exists():
            stale.unlink()
            log.info("  removed %s, which nothing reports any more", stale.relative_to(REPO_ROOT))
    if docs:
        out_dir.mkdir(parents=True, exist_ok=True)      # a world with nothing to draw gets no folder
    for name, doc in docs:
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
