"""A Grafana dashboard per world, derived from that world's wiring.

  agora-dashboards society

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

Vocabulary: nothing new. The panels are built from `ag:monitors`/`ag:polls`, and the bucket name
comes from `onboarding.influx`, so the dashboard cannot disagree with what the agent writes to.

See knowledge/domain/onboarding.md.
"""

from __future__ import annotations

import argparse
import json
import logging

from agora import ratified
from agora.config import PROJECT_ROOT
from agora.genesis import worlds
from agora.ontology import AG, WORLD_GRAPH

from .influx import bucket_name

log = logging.getLogger("dashboards")

REPO_ROOT = PROJECT_ROOT.parent
DASHBOARD_ROOT = REPO_ROOT / "infra" / "grafana" / "dashboards"

# Whatever an agent observes, with the subject it observes it for. The agent is what owns a
# bucket, so it is what a panel is keyed on; the subject is what a person reading it cares about.
_WATCHERS_Q = f"""
SELECT DISTINCT ?agentId ?subjectId WHERE {{ GRAPH <{WORLD_GRAPH}> {{
  ?agent a <{AG}Agent> ; <{AG}localId> ?agentId .
  {{ ?agent <{AG}polls> ?sensor . ?sensor <{AG}monitors> ?subject }}
  UNION
  {{ ?agent <{AG}actsFor> ?subject }}
  ?subject <{AG}localId> ?subjectId .
}} }}"""

# Written by agora.influx_writer — named here so a change there fails visibly rather than
# producing a dashboard that queries nothing.
MEASUREMENT = "soil_moisture"
FIELD = "value"


def _flux(bucket: str) -> str:
    return (f'from(bucket: "{bucket}")\n'
            "  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
            f'  |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")\n'
            f'  |> filter(fn: (r) => r._field == "{FIELD}")\n'
            "  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)")


def _panel(title: str, bucket: str, kind: str, x: int, y: int, w: int, h: int, panel_id: int):
    return {
        "id": panel_id,
        "type": kind,
        "title": title,
        "datasource": {"type": "influxdb", "uid": "influxdb"},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [{"refId": "A", "query": _flux(bucket)}],
        "fieldConfig": {
            "defaults": {
                "unit": "percentunit",
                # The band is the agent's belief, not the dashboard's, so nothing is asserted
                # here beyond dry-at-the-bottom. Colour is a hint for a human, not a threshold.
                "min": 0, "max": 1,
                "color": {"mode": "thresholds"},
                "thresholds": {"mode": "absolute", "steps": [
                    {"color": "red", "value": None},
                    {"color": "orange", "value": 0.25},
                    {"color": "green", "value": 0.4},
                ]},
            },
            "overrides": [],
        },
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}}
        if kind == "timeseries" else {},
    }


def render(world: str) -> dict:
    rows = ratified.rows(ratified.dataset(world), _WATCHERS_Q)
    watchers = sorted({(r["agentId"], r["subjectId"]) for r in rows})
    if not watchers:
        raise SystemExit(f"agora-dashboards: nothing in world {world!r} observes anything")

    panels, y, pid = [], 0, 1
    # A row of current values across the top, then one history panel per watcher beneath.
    for i, (agent_id, subject_id) in enumerate(watchers):
        panels.append(_panel(subject_id, bucket_name(world, agent_id), "stat",
                             x=(i * 4) % 24, y=0, w=4, h=4, panel_id=pid))
        pid += 1
    y = 4
    for agent_id, subject_id in watchers:
        panels.append(_panel(f"{subject_id} — as {agent_id} sees it",
                             bucket_name(world, agent_id), "timeseries",
                             x=0, y=y, w=24, h=7, panel_id=pid))
        pid += 1
        y += 7

    return {
        "uid": f"agora-{world}"[:40],
        "title": f"Agora — {world}",
        "tags": ["agora", world],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "panels": panels,
    }


def generate(world: str) -> None:
    out_dir = DASHBOARD_ROOT / world
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "agora.json"
    out.write_text(json.dumps(render(world), indent=2) + "\n")
    out.chmod(0o644)
    log.info("  wrote %s (%d panels)", out.relative_to(REPO_ROOT),
             len(render(world)["panels"]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="agora-dashboards",
        description="Generate this world's Grafana dashboard from its own wiring.",
    )
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    generate(p.parse_args().world)


if __name__ == "__main__":
    main()
