"""`past`: what happened to the agent, for a chat that reads it — its journal's entries, its series' points and its
metrics' windows — and the three tools that read them, `journal`, `series` and `metrics`
(knowledge/domain/translation/translator.md).

**WHAT HOLDS NOW AND WHAT HAPPENED ARE TWO READS.** The store, read with `query`, is the present: what the agent
believes. The journal and the series are the record, watched and never believed (knowledge/domain/kernel/journal.md,
knowledge/domain/kernel/series.md): the events its packages said and the lines of its log, and how each reading went
over time. A chat reads them where it reads `orexis:Event`, since both are what events say; a person reading them
through the agent's model is the person `orexis-explain` already serves, and nothing read here reaches a plan.

**READ IN PLACE, NEVER COPIED.** The journal grows for good, so a SELECT or an ASK runs over it where it is, its
entries their union, read-only from the model's thread as its endpoint is read from the server's, refused where it
holds a `SERVICE` or a `FROM`. The series is asked in Flux the tool writes from the fields the model fills — a
measurement, a sensor, a stretch and a window — over the agent's history bucket, with the token that opens only it;
the model writes no Flux, so it reads no other bucket and runs nothing but that read. The metrics are asked the same way
over the agent's metrics bucket, a measurement and one of its fields summed or otherwise aggregated over a stretch, by a
tag where one is named — which is how a person asks what the agent's model spent, its `translated` windows carrying the
tokens by the API's own names.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from .readable import ROWS, answered, refusal, written

JOURNAL, SERIES, METRICS = "journal", "series", "metrics"
#  HOW FAR BACK THE SERIES IS READ where the model says nothing, and how a stretch may be said.
SINCE = "-24h"
#  HOW FAR BACK A LISTING LOOKS for each measurement's latest point, where the model says nothing: a sensor silent for a
#  day is still listed.
LISTED_SINCE = "-30d"
_DURATION = re.compile(r"-?[0-9]+(?:ns|us|ms|s|m|h|d|w|mo|y)")
_FNS = ("mean", "min", "max", "last", "sum", "count")
#  WHAT A POINT SAYS, beside its instant and its number: the tags sensing writes it under.
_TAGS = ("sensor", "feature", "defective")
_FIELDS = ("measurement", "sensor", "start", "stop", "every", "fn")
_METRIC_FIELDS = ("measurement", "field", "by", "start", "stop", "every", "fn")
#  A FIELD OR A TAG'S NAME, as the metrics part writes them: checked, then quoted.
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Past:
    """What happened to one agent, as a chat may read it: its journal's store, its history sink and its metrics sink,
    each absent where the agent keeps none, and the prefixes the chat's rows are written with."""

    def __init__(self, journal, series, prefixes: dict[str, str], metrics=None):
        self.journal_store, self.history, self.metrics, self.prefixes = journal, series, metrics, prefixes

    def tools(self) -> list[dict]:
        """The tools what happened is read with, each answered by `call`: one per record the agent keeps."""
        out = []
        if self.journal_store is not None:
            out.append({"name": JOURNAL, "description": "What happened to the agent, as its journal kept it: a "
                        "SPARQL SELECT or ASK over its entries. Each is an event at its prov:atTime — `?e a ?class ; "
                        "prov:atTime ?t`, its class its package's and its fields in that package's words — or a line of "
                        "its log, orexis:LogRecord with orexis:logger, orexis:level and orexis:message, kept for the last "
                        "minutes and for good before an incident, which says `a orexis:Incident`. Ask the newest first, "
                        f"ORDER BY DESC(?t) with a LIMIT. The query tool's prefixes are declared. Write no SERVICE or "
                        f"FROM. At most {ROWS} rows come back.",
                        "input_schema": {"type": "object", "properties": {"sparql": {"type": "string"}},
                                         "required": ["sparql"]}})
        if self.history is not None:
            out.append({"name": SERIES, "description": "How the agent's readings went over time, from its own series: "
                        "the points of one measurement, the observed property's local name (SoilMoisture, "
                        "AirTemperature), of one sensor where named, its local name. Leave the measurement out to list "
                        f"each measurement and sensor with its latest point over the last {LISTED_SINCE.lstrip('-')}. A stretch starts and stops at a duration "
                        f"back from now (-24h, -7d) or an ISO instant, {SINCE} where none is given; `every` and `fn` "
                        f"aggregate it per window (1h, mean). The newest {ROWS} points come back, oldest first.",
                        "input_schema": {"type": "object", "properties": {
                            "measurement": {"type": "string"}, "sensor": {"type": "string"},
                            "start": {"type": "string"}, "stop": {"type": "string"},
                            "every": {"type": "string"}, "fn": {"type": "string", "enum": list(_FNS)}}}})
        if self.metrics is not None:
            out.append({"name": METRICS, "description": "How the agent itself has been doing, from its own metrics: a "
                        "window a minute per measurement and tags, each field `count` (how many happened), "
                        "`<value>_sum`, `<value>_mean` and `<value>_max`. `translated` is each use of its model, tagged "
                        "act, outcome and model, its tokens by the API's names (input_tokens, cache_creation_input_tokens, "
                        "cache_read_input_tokens, output_tokens) and its requests and duration_s; `pass`, `planner`, "
                        "`revise` and `received` are its own work. Leave the measurement out to list each one with its "
                        f"fields over the last {LISTED_SINCE.lstrip('-')}. Name a measurement and a field to aggregate it "
                        f"with fn (sum where none is given) over a stretch, {SINCE} where none is given — one figure, or "
                        "one per `every` window (1h, 1d), and one per value of the tag `by` names. A total is the sum of "
                        "a `_sum` field or of `count`, never of a mean or a max.",
                        "input_schema": {"type": "object", "properties": {
                            "measurement": {"type": "string"}, "field": {"type": "string"}, "by": {"type": "string"},
                            "start": {"type": "string"}, "stop": {"type": "string"},
                            "every": {"type": "string"}, "fn": {"type": "string", "enum": list(_FNS)}}}})
        return out

    def call(self, name: str, inputs: dict) -> str | None:
        """What one of the tools answers, or None where `name` is neither."""
        if name == JOURNAL and self.journal_store is not None:
            return self.journaled(str(inputs.get("sparql") or ""))
        if name == SERIES and self.history is not None:
            return self.points(**{k: str(v) for k, v in inputs.items() if k in _FIELDS and v not in (None, "")})
        if name == METRICS and self.metrics is not None:
            return self.windows(**{k: str(v) for k, v in inputs.items() if k in _METRIC_FIELDS and v not in (None, "")})
        return None

    def journaled(self, text: str) -> str:
        """The model's SELECT or ASK over the journal's entries, their union; the reason, where it is refused."""
        refused = refusal(text, self.prefixes)
        if refused:
            return f"refused: {refused}"
        try:
            return answered(self.journal_store.query(text, prefixes=self.prefixes, use_default_graph_as_union=True),
                            lambda value: written(value, self.prefixes))
        except (SyntaxError, OSError, ValueError) as exc:
            return f"the engine would not run it: {exc}"

    def points(self, measurement: str | None = None, sensor: str | None = None, start: str | None = None,
               stop: str | None = None, every: str | None = None, fn: str = "mean") -> str:
        """The series' points the fields ask for, a line each; the reason, where a field will not do."""
        try:
            flux = _flux(self.history.bucket, measurement, sensor, start or (SINCE if measurement else LISTED_SINCE),
                         stop, every, fn)
        except ValueError as exc:
            return f"refused: {exc}"
        found = self.history.read(flux)
        if isinstance(found, str):
            return found
        lines = [", ".join(f"{k.lstrip('_')}: {_said(r[k])}" for k in ("_measurement", *_TAGS, "_time", "_value")
                           if r.get(k) not in (None, "")) for r in found]
        return "\n".join(lines) or "(no points)"

    def windows(self, measurement: str | None = None, field: str | None = None, by: str | None = None,
                start: str | None = None, stop: str | None = None, every: str | None = None, fn: str = "sum") -> str:
        """The metrics the fields ask for, a line each; the reason, where a field will not do."""
        try:
            flux = _metric_flux(self.metrics.bucket, measurement, field, by,
                                start or (SINCE if measurement else LISTED_SINCE), stop, every, fn)
        except ValueError as exc:
            return f"refused: {exc}"
        found = self.metrics.read(flux)
        if isinstance(found, str):
            return found
        shown = ("_measurement", "fields", "_field", *([by] if by else ()), "_start", "_stop", "_time", "_value")
        lines = [", ".join(f"{k.lstrip('_')}: {_said(r[k])}" for k in shown if r.get(k) not in (None, "")
                           and not (k in ("_start", "_stop") and r.get("_time") is not None)) for r in found]
        return "\n".join(lines) or "(no windows)"


def _flux(bucket: str, measurement, sensor, start, stop, every, fn) -> str:
    """The one read the fields describe, every field checked before it is written into the text."""
    if fn not in _FNS:
        raise ValueError(f"fn is one of {', '.join(_FNS)}")
    if every is not None and not _DURATION.fullmatch(every.lstrip("-")):
        raise ValueError(f"every is a duration, such as 1h: {every!r}")
    stretch = f"start: {_instant(start)}" + (f", stop: {_instant(stop)}" if stop else "")
    head = f"from(bucket: {json.dumps(bucket)})\n  |> range({stretch})\n"
    if measurement is None:
        return (head + '  |> filter(fn: (r) => r._field == "value")\n'
                '  |> group(columns: ["_measurement", "sensor"])\n  |> last()\n  |> group()\n'
                f"  |> limit(n: {ROWS})")
    text = head + f"  |> filter(fn: (r) => r._measurement == {json.dumps(measurement)} and r._field == \"value\")\n"
    if sensor is not None:
        text += f"  |> filter(fn: (r) => r.sensor == {json.dumps(sensor)})\n"
    if every is not None:
        text += f"  |> aggregateWindow(every: {every.lstrip('-')}, fn: {fn}, createEmpty: false)\n"
    return text + f'  |> group()\n  |> sort(columns: ["_time"], desc: true)\n  |> limit(n: {ROWS})\n' \
                  '  |> sort(columns: ["_time"])'


def _metric_flux(bucket: str, measurement, field, by, start, stop, every, fn) -> str:
    """The one read of the metrics the fields describe, every field checked before it is written into the text."""
    if fn not in _FNS:
        raise ValueError(f"fn is one of {', '.join(_FNS)}")
    if every is not None and not _DURATION.fullmatch(every.lstrip("-")):
        raise ValueError(f"every is a duration, such as 1h: {every!r}")
    for what, name in (("field", field), ("by", by)):
        if name is not None and not _NAME.fullmatch(name):
            raise ValueError(f"{what} is a name, such as output_tokens_sum: {name!r}")
    stretch = f"start: {_instant(start)}" + (f", stop: {_instant(stop)}" if stop else "")
    head = f"from(bucket: {json.dumps(bucket)})\n  |> range({stretch})\n"
    if measurement is None:
        return (head + '  |> keep(columns: ["_measurement", "_field"])\n  |> group(columns: ["_measurement"])\n'
                '  |> distinct(column: "_field")\n'
                '  |> reduce(identity: {fields: ""}, fn: (r, accumulator) => ({fields: accumulator.fields + " " + r._value}))\n'
                f"  |> group()\n  |> limit(n: {ROWS})")
    if field is None:
        raise ValueError("name the field to aggregate, count or a `<value>_sum`; leave the measurement out to list them")
    groups = json.dumps([by] if by else [])
    text = (head + f"  |> filter(fn: (r) => r._measurement == {json.dumps(measurement)} and r._field == {json.dumps(field)})\n"
            f"  |> group(columns: {groups})\n")
    if every is None:
        return text + f"  |> {fn}()\n  |> limit(n: {ROWS})"
    return text + (f"  |> aggregateWindow(every: {every.lstrip('-')}, fn: {fn}, createEmpty: false)\n"
                   f'  |> sort(columns: ["_time"], desc: true)\n  |> limit(n: {ROWS})\n  |> sort(columns: ["_time"])')


def _instant(text: str) -> str:
    """A stretch's end as Flux says it: a duration back from now, or an ISO instant."""
    if _DURATION.fullmatch(text):
        return text if text.startswith("-") else "-" + text
    try:
        return f'time(v: {json.dumps(datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat())})'
    except ValueError:
        raise ValueError(f"a stretch's end is a duration, such as -24h, or an ISO instant: {text!r}") from None


def _said(value) -> str:
    return value.isoformat(timespec="seconds") if isinstance(value, datetime) else " ".join(str(value).split())
