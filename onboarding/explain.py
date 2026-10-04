"""orexis-explain — one agent's season from its series: a report answering reflection's fixed
questions, model-less, in the world's own words as the series tags them.

  orexis-explain <world> <agent> [--since 30d]

REFLECTION READS THE SERIES AND NEVER THE BELIEFS (reflection-is-genesis-run-again-over-the-series).
This tool opens no agent's volume and imports nothing that reads one: it asks the agent's two buckets
— its history, every observation and every step, and its metrics, what each pass searched, reached,
exhausted and failed — with the admin-side token the installation holds, which is why it lives beside
the onboarding commands and outside `agent/`. It answers the SEASON and never the present: what an
agent observes, wants and does now is its account, over chat; what a month of its series says is this.
It names and writes nothing: a probe by its `sensor` tag, an action by its `action` tag, a desire by its
`desire` tag, each the local name of the world's own IRI, so a proposal that follows is an edit to the
world the sovereign ratifies, and no belief is read to find it.

THE QUESTIONS RUN OVER ROWS, AND THE ROWS COME FROM ONE OF TWO SOURCES: a Flux query against the store
(`read`, built as `dashboards.py` builds its queries, pivoted back into the points the agent wrote by
`points_of`), or points handed in directly — the dicts a `Sink` records — so every question is tested
on points a real runtime wrote in-process, with no InfluxDB in the room (`world/greenhouse/tests/
test_explain.py`). Each question is a function over the history, the metrics and what the world STATES
that the series cannot (`Stated`): the desires the agent holds, since a desire never read unmet leaves
no trace on the series at all, and which sensors read a fraction, since "past 1.0" is a calibration
point for a probe and nothing for a thermometer. Both are read off the world's documents — public,
ratified, nobody's belief — which the record's last seam calls the honest default.

THE FIVE, in the record's order, each answering what it found or that nothing stood out:

| the series says | reflection names |
|---|---|
| a want stood `unreachable`, pass after pass, under a desire | an action the world lacks, or a scope that cannot reach it |
| a step's `landing` timed out, or landed late, for one action | a landing band declared wrong, or an instrument past its calibration |
| a desire with no `search` tagged with it over the window | dead weight, a desire to retire |
| every `search` under a desire ended `Exhausted` | a budget too small or an estimate too weak |
| a probe's reading past 1.0 or below 0.0 for a stretch, its raw count unchanged for a run, or the agent itself saying it `doubted` | a recalibration to schedule |

The fifth reads the two fields #894 put on the series for it: the raw count beside the reading on
every observation point, and `doubted`, which sensor the agent said silent or stuck and when.

See knowledge/runbooks/reflect.md.
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pyoxigraph as ox

from agent.runtime import boot
from agent.series import HISTORY, METRICS
from agent.store import graphs_of, rows

from . import installation, reading
from .compose import roster
from .influx import _admin_token, bucket_name
from .worlds import world_dir, worlds

log = logging.getLogger("explain")

OREXIS = "http://example.org/orexis#"
PUBLIC = OREXIS + "PublicGraph"
DESIRE_GRAPH = "http://example.org/orexis/planning#DesireGraph"
#  THE ONE UNIT THAT MAKES A READING A FRACTION OF ONE, as the dashboards read it: QUDT's UNITLESS,
#  stated of the sensor or of the range its host states for the property it observes.
UNITLESS = "http://qudt.org/vocab/unit/UNITLESS"

#  WHAT THE SERIES CANNOT SAY, read off the world: the desires the agent holds, by local name — in the
#  agent's own documents, which `boot` reads from the world's directory as `reading.lasts` does, into a
#  store in memory and never from a volume.
_DESIRES_Q = """
SELECT ?d WHERE { ?a a orexis:Agent ; orexis:localId $id ; planning:holds ?d . ?d a planning:Desire }"""

#  And which sensors read a fraction: a unit of UNITLESS on the sensor, or on a range its host — or what
#  its host is a sample of — states for the property it observes.
_FRACTIONS_Q = f"""
SELECT DISTINCT ?sensor WHERE {{
  ?sensor sosa:observes ?property ; sosa:isHostedBy ?host .
  {{ ?sensor schema:unitCode <{UNITLESS}> }}
  UNION {{ ?host sosa:isSampleOf* ?subject . ?subject ?rel ?range . ?range ssn-system:inCondition ?c .
          ?c ssn:forProperty ?property ; schema:unitCode <{UNITLESS}> }} }}"""

#  THE OUTCOME A SEARCH THE BUDGET CUT SHORT IS TAGGED WITH: the local name of `planning:Exhausted`.
EXHAUSTED = "Exhausted"
#  THE MEASUREMENT A STEP IS HISTORY UNDER, as execution writes it (`agent.execution.events.MEASUREMENT`).
STEP = "Step"


@dataclass(frozen=True)
class Stated:
    """What the world states that the series does not: the desires the agent holds, and the sensors
    whose reading is a fraction of one, each by the local name the series tags it with."""
    desires: frozenset[str] = frozenset()
    fractions: frozenset[str] = frozenset()


def _local(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def stated(world: str, agent: str) -> Stated:
    """`Stated` for `agent` of `world`, read off the world's documents as onboarding reads them: the
    agent booted from them in memory for the desires it holds, the public graphs for the fractions."""
    store = boot(world_dir(world), agent, others=reading.ours())
    public = graphs_of(store, PUBLIC)
    desires = {_local(r["d"]) for r in rows(store, _DESIRES_Q, public + graphs_of(store, DESIRE_GRAPH), id=ox.Literal(agent))}
    fractions = {_local(r["sensor"]) for r in rows(store, _FRACTIONS_Q, public)}
    return Stated(frozenset(desires), frozenset(fractions))


# ---------------------------------------------------------------- the rows

#  THE COLUMNS A FLUX ROW CARRIES THAT ARE NOT TAGS.
_META = frozenset({"result", "table", "_start", "_stop", "_time", "_value", "_field", "_measurement"})


def flux(bucket: str, since: str | None = None) -> str:
    """Everything `bucket` holds — or since `since`, a Flux duration back from now (`30d`) or an RFC 3339
    instant — as `dashboards.py` builds a query: from the bucket, over the range, and nothing else."""
    start = "0" if since is None else (f"-{since}" if re.fullmatch(r"\d+(ms|s|m|h|d|w|mo|y)", since) else since)
    return f'from(bucket: "{bucket}")\n  |> range(start: {start})'


def points_of(tables) -> list[dict]:
    """The points the agent wrote, back from the rows the store answers: a row per field, pivoted by
    measurement, instant and tag set into one point each, in the shape a `Sink` was handed."""
    grouped: dict[tuple, dict] = {}
    for table in tables:
        for record in table.records:
            values = record.values
            tags = {k: v for k, v in values.items() if k not in _META and v is not None}
            key = (values["_measurement"], values["_time"], tuple(sorted(tags.items())))
            grouped.setdefault(key, {})[values["_field"]] = values["_value"]
    return [{"measurement": m, "time": t, "tags": dict(tags), "fields": fields}
            for (m, t, tags), fields in sorted(grouped.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


def read(url: str, org: str, token: str, bucket: str, since: str | None = None) -> list[dict]:
    """Every point `bucket` holds over the window, read from the store at `url`."""
    from influxdb_client import InfluxDBClient

    with InfluxDBClient(url=url, token=token, org=org, timeout=600_000) as client:
        return points_of(client.query_api().query(flux(bucket, since), org=org))


# ---------------------------------------------------------------- the questions

def _of(points: list[dict], measurement: str) -> list[dict]:
    return sorted((p for p in points if p["measurement"] == measurement), key=lambda p: p["time"])


def _when(at: datetime) -> str:
    at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    return at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _span(points: list[dict]) -> str:
    first, last = points[0]["time"], points[-1]["time"]
    return f"from {_when(first)} to {_when(last)} ({_stretch(last - first)})"


def _stretch(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    return f"{days}d {hours}h" if days else (f"{hours}h {minutes}m" if hours else f"{minutes}m")


def _sum(points: list[dict], name: str) -> float:
    return sum(float(p["fields"].get(name) or 0) for p in points)


def _by(points: list[dict], tag: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for p in points:
        out[p["tags"].get(tag) or f"(no {tag})"].append(p)
    return dict(sorted(out.items()))


def unreachable(history: list[dict], metrics: list[dict], stated: Stated) -> list[str]:
    """A want stood `unreachable`, pass after pass, under a desire: by desire, how many passes said so,
    over how many windows and what span."""
    return [f"{desire}: unreachable in {int(_sum(points, 'count'))} pass(es) over {len(points)} window(s), {_span(points)}"
            for desire, points in _by(_of(metrics, "unreachable"), "desire").items()]


def landings(history: list[dict], metrics: list[dict], stated: Stated) -> list[str]:
    """The verdicts on steps, by action: how many, landed, timed out, and how late the world answered —
    the mean and the max of `late_s` over the window — beside what the history says of the action's
    steps, taken and landed. A line stands out where a verdict timed out or did not land."""
    out = []
    steps = _by(_of(history, STEP), "action")
    for action, points in _by(_of(metrics, "landing"), "action").items():
        count, landed, timed_out = (int(_sum(points, f)) for f in ("count", "landed", "timed_out"))
        with_late = [p for p in points if p["fields"].get("late_s_mean") is not None]
        n = sum(round(p["fields"]["late_s_sum"] / p["fields"]["late_s_mean"]) if p["fields"]["late_s_mean"] else int(p["fields"].get("count") or 0)
                for p in with_late)
        late = (f"late_s mean {_sum(with_late, 'late_s_sum') / n:.0f} s, max {max(p['fields'].get('late_s_max') or 0 for p in with_late):.0f} s"
                if with_late and n else "no late_s said")
        line = f"{action}: {count} verdict(s), {landed} landed, {timed_out} timed out, {count - landed - timed_out} ended undone; {late}; {_span(points)}"
        if action in steps:
            taken = sum(1 for p in steps[action] if p["fields"].get("taken") is True)
            answered = sum(1 for p in steps[action] if p["fields"].get("landed") is True)
            line += f"; history: {taken} step(s) taken, {answered} landed"
        out.append(line + (" — STOOD OUT" if timed_out or landed < count else ""))
    return out


def idle(history: list[dict], metrics: list[dict], stated: Stated) -> list[str]:
    """Desires the agent holds with no `search` tagged with them over the window: never read unmet."""
    searched = {p["tags"].get("desire") for p in _of(metrics, "search")} - {None}
    return [f"{desire}: no search over the window" for desire in sorted(stated.desires - searched)]


def exhausted(history: list[dict], metrics: list[dict], stated: Stated) -> list[str]:
    """Desires whose every search ended `Exhausted`, the budget spent: how many searches, the budget
    they had, and what they weighed."""
    out = []
    for desire, points in _by(_of(metrics, "search"), "desire").items():
        outcomes = {p["tags"].get("outcome") for p in points}
        if outcomes != {EXHAUSTED}:
            continue
        count = int(_sum(points, "count"))
        budget = max(p["fields"].get("budget_max") or 0 for p in points)
        weighed = _sum(points, "weighed_sum") / count if count else 0
        out.append(f"{desire}: every one of {count} search(es) exhausted, budget {budget:g}, weighed {weighed:.0f} a search, "
                   f"max {max(p['fields'].get('weighed_max') or 0 for p in points):g}; {_span(points)}")
    return out


def probes(history: list[dict], metrics: list[dict], stated: Stated) -> list[str]:
    """Per probe: stretches of readings past 1.0 or below 0.0 where the world says the reading is a
    fraction; the longest run of an unchanged raw count; and the windows in which the agent itself said
    the sensor silent or stuck."""
    out = []
    readings: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in sorted(history, key=lambda p: p["time"]):
        if p["measurement"] != STEP and "value" in p["fields"] and p["tags"].get("sensor"):
            readings[(p["tags"]["sensor"], p["measurement"])].append(p)
    for (sensor, measurement), points in sorted(readings.items()):
        if sensor in stated.fractions:
            for side, outside in (("past 1.0", lambda v: v > 1.0), ("below 0.0", lambda v: v < 0.0)):
                for stretch in _runs(points, lambda p: outside(p["fields"]["value"])):
                    extreme = max((p["fields"]["value"] for p in stretch), key=abs)
                    out.append(f"{sensor} ({measurement}): {len(stretch)} reading(s) {side}, to {extreme:g}, {_span(stretch)}")
        counted = [p for p in points if p["fields"].get("raw") is not None]
        longest = max(_runs(counted, lambda p: True, same=lambda p: p["fields"]["raw"]), key=len, default=[])
        if len(longest) >= 2:
            out.append(f"{sensor} ({measurement}): raw count {longest[0]['fields']['raw']:g} unchanged for "
                       f"{len(longest)} readings, {_span(longest)}")
    for sensor, points in _by(_of(metrics, "doubted"), "sensor").items():
        for how in ("silent", "stuck"):
            said = [p for p in points if p["fields"].get(how)]
            if said:
                out.append(f"{sensor}: said {how} in {len(said)} window(s), {_span(said)}")
    return out


def _runs(points: list[dict], where, same=lambda p: True) -> list[list[dict]]:
    """Maximal runs of consecutive `points` for which `where` holds and `same` answers one value."""
    runs: list[list[dict]] = []
    run: list[dict] = []
    for p in points:
        if where(p) and run and same(run[-1]) == same(p):
            run.append(p)
        else:
            if run:
                runs.append(run)
            run = [p] if where(p) else []
    if run:
        runs.append(run)
    return runs


#  THE FIXED SET, in the record's order: a title, what the series says and reflection names, the question.
QUESTIONS = (
    ("wants nothing reached", "a want stood unreachable, pass after pass, under a desire — an action the world lacks, "
                              "or a scope that cannot reach the want", unreachable),
    ("landings", "a step's landing timed out, or landed late by a stretch, for one action — a landing band "
                 "declared wrong, or an instrument past its calibration", landings),
    ("desires never unmet", "a desire with no search tagged with it over the window — dead weight, a desire to retire", idle),
    ("searches exhausted", "every search under a desire ended exhausted, the budget spent — a budget too small or an "
                           "estimate too weak", exhausted),
    ("probes", "a probe's reading sat past a calibration point for a stretch, its raw count has not moved for a run, "
               "or the agent said it silent or stuck — a recalibration to schedule", probes),
)


@dataclass
class Report:
    """One agent's season: the sections, each the question's title, its gloss and what it found."""
    world: str
    agent: str
    sections: list[tuple[str, str, list[str]]] = field(default_factory=list)
    history: int = 0
    metrics: int = 0
    window: str = "everything the buckets hold"

    def text(self) -> str:
        head = [f"{self.world}/{self.agent} — {self.window}: {self.history} history point(s), {self.metrics} metrics point(s)"]
        for title, gloss, lines in self.sections:
            head += ["", f"== {title} ==", f"   ({gloss})"]
            head += [f" - {line}" for line in lines] or ["   nothing stood out"]
        return "\n".join(head) + "\n"


def report(world: str, agent: str, history: list[dict], metrics: list[dict], stated: Stated, *,
           window: str | None = None) -> Report:
    """Every question of the fixed set over `history` and `metrics`, with what the world `stated`."""
    out = Report(world, agent, history=len(history), metrics=len(metrics), window=window or Report.window)
    for title, gloss, question in QUESTIONS:
        out.sections.append((title, gloss, question(history, metrics, stated)))
    return out


# ---------------------------------------------------------------- the command

def explain(world: str, agent: str, since: str | None = None) -> Report:
    """The report for `agent` of `world`, read from the buckets the installation's store holds for it."""
    if agent not in roster(world):
        raise SystemExit(f"orexis-explain: world {world!r} states no agent {agent!r} — it states {', '.join(roster(world)) or 'none'}")
    told = installation.purposes(world)
    token = _admin_token()
    started = time.perf_counter()
    url, org = installation.series(HISTORY)
    history = read(url, org, token, bucket_name(world, agent, HISTORY), since)
    metrics: list[dict] = []
    if METRICS in told:
        url, org = installation.series(METRICS)
        metrics = read(url, org, token, bucket_name(world, agent, METRICS), since)
    else:
        log.warning("%s is not monitored, so %s writes no metrics: four of the five questions have nothing to read", world, agent)
    read_s = time.perf_counter() - started
    started = time.perf_counter()
    out = report(world, agent, history, metrics, stated(world, agent), window=f"since {since}" if since else None)
    log.info("read %d point(s) in %.2f s, answered in %.3f s", len(history) + len(metrics), read_s, time.perf_counter() - started)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-explain",
        description="One agent's season from its series: a report answering reflection's fixed questions, "
                    "read from its history and metrics buckets and never from its beliefs.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("agent", help="which of its agents, by id")
    p.add_argument("--since", help="how far back: a Flux duration (30d, 12h) or an RFC 3339 instant; everything held where not given")
    args = p.parse_args()
    if args.since and not (re.fullmatch(r"\d+(ms|s|m|h|d|w|mo|y)", args.since) or _instant(args.since)):
        raise SystemExit(f"orexis-explain: --since {args.since!r} is neither a Flux duration (30d) nor an RFC 3339 instant")
    print(explain(args.world, args.agent, args.since).text(), end="")


def _instant(text: str) -> bool:
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()
