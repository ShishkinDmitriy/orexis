"""What an agent's readings came to — a belief about history, in constant space.

`sensed_writer` keeps exactly one observation per subject and property, replaced each reading,
because the *series* lives in Influx. That is right, and it leaves a review nothing to look at:
a rule that wants to know whether a probe has been moving cannot ask a single current value.

The answer is not to keep the readings. It is to keep **what they came to**. One summary node
per subject and property accumulates count, extremes, sum and sum-of-squares — from which mean,
variance and spread all follow — plus the first and last times seen. Nothing else. A summary of
a year is exactly the same size as a summary of an hour, so the triple count stays flat and the
guarantee `agent-metrics.md` makes about it survives.

That is the difference between a log and a belief, and it is why this belongs in the store at
all: **a reading is a measurement and a summary is current state**, which is precisely the line
`two-store-beliefs.md` already draws between Influx and here.

Two more properties follow from keeping it in the store rather than in memory:

- it **survives a restart**, so an agent that reboots does not lose its grounds for judgement
  and have to earn them again;
- reflection **never waits on the series store**, which attention must never do.

`review:sampleMax` is kept beside the sums although a variance could be derived without it, because
equality with the minimum is the one thing a variance cannot express. A variance *approaches*
zero for a nearly-still world and *is* zero only for an instrument that has not moved at all,
and those two cases want opposite responses.

See knowledge/decisions/self-review-is-a-capability.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from orexis_progression_patience.store import Store, bindings, decimal

from .graphs import summaries_graph

# How many completed windows an agent keeps behind the one it is filling. Constant, so the
# belief base stays a fixed size — and more than one, so a rule can tell "steady since I last
# looked" from "steady for as long as I have been keeping track", and can see that its own last
# decision changed nothing.
RING = 8


def _slug(uri: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", uri.rstrip("#/"))[-1])


def summary_uri(subject_uri: str, observed_property: str, seq: int | None = None) -> str:
    """The node one (subject, property) pair owns for one window.

    `seq is None` is the window being filled. Completed ones carry their sequence in the IRI so
    the ring is a set of distinct nodes rather than a list anything has to shuffle.

    Minted from the subject's **URI** and not from its `ag:localId`, even though the two happen
    to slug identically today. A local id is stated rather than inferable from the shape of a
    URI, so deriving one from the other is the exact inference the vocabulary warns against —
    and here it would be load-bearing, because rolling a window over has to reach the same node
    that recording a reading created. Like the observation's own IRI, this only has to be stable
    and distinct; nothing ever looks a summary up by name.
    """
    stem = f"ag:sum_{_slug(subject_uri)}_{_slug(observed_property)}"
    return stem if seq is None else f"{stem}_{seq}"


@dataclass(frozen=True)
class Window:
    """One completed or in-flight summary, as the reviewer wants to read it."""

    subject: str
    observed_property: str
    count: int
    minimum: float
    maximum: float
    total: float
    total_squares: float
    first_at: datetime | None
    last_at: datetime | None
    seq: int | None = None

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    @property
    def spread(self) -> float:
        """The observed range as a fraction of its own mean. Unit-free, and exactly zero only
        when the instrument did not move at all."""
        if self.maximum == self.minimum:
            return 0.0
        mean = abs(self.mean)
        return (self.maximum - self.minimum) / mean if mean else float("inf")

    @property
    def gap_s(self) -> float | None:
        """Mean seconds between the readings actually seen — how long a fresh window costs."""
        if self.count < 2 or self.first_at is None or self.last_at is None:
            return None
        return (self.last_at - self.first_at).total_seconds() / (self.count - 1)


class Summaries:
    """One agent's running account of everything it senses.

    This capability's, not the kernel's: a summary exists as evidence for a judgement, so an
    agent given no room to make one keeps none. Fed through sensing's `on_reading_recorded` hook, so the
    ingest path never learns that summaries exist.
    """

    def __init__(self, store: Store, agent_id: str):
        self.store = store
        self.graph = summaries_graph(agent_id)

    # --- accumulating -------------------------------------------------------------------

    def record(self, subject_uri: str, observed_property: str,
               value: float, ts: str | None = None) -> None:
        """Fold one reading into the window being filled.

        Read-modify-write rather than one clever SPARQL update. The store is embedded, so the
        extra round trip costs nothing measurable, and the arithmetic being visible in Python is
        worth more than a shorter query nobody can check by eye.
        """
        at = ts or datetime.now(timezone.utc).isoformat()
        node = summary_uri(subject_uri, observed_property)
        held = self._read(node)

        count = (held.count if held else 0) + 1
        low = min(held.minimum, value) if held else value
        high = max(held.maximum, value) if held else value
        total = (held.total if held else 0.0) + value
        squares = (held.total_squares if held else 0.0) + value * value
        first = held.first_at.isoformat() if held and held.first_at else at

        self.store.update(f"""
WITH <{self.graph}>
DELETE {{ {node} ?p ?o }} WHERE {{ {node} ?p ?o }} ;
INSERT DATA {{ GRAPH <{self.graph}> {{
  {node} a review:ObservationSummary ;
    sosa:hasFeatureOfInterest <{subject_uri}> ;
    sosa:observedProperty <{observed_property}> ;
    review:sampleCount {count} ;
    review:sampleMin {decimal(low)} ;
    review:sampleMax {decimal(high)} ;
    review:sampleSum {decimal(total)} ;
    review:sampleSumSquares {decimal(squares)} ;
    review:firstAt "{first}"^^xsd:dateTime ;
    review:lastAt "{at}"^^xsd:dateTime .
}} }}""")

    # --- rolling over -------------------------------------------------------------------

    def roll(self) -> int:
        """Close every window being filled and drop anything past the ring. Returns how many.

        Called by the reviewer when it arises, which is what makes **the window the interval
        between arisings** rather than a fixed count of readings. The agent chose when to look
        again; the evidence is therefore exactly what accumulated while it was not looking.
        """
        closed = 0
        for window in self.accumulating():
            seq = self._next_seq(window.subject, window.observed_property)
            live = summary_uri(window.subject, window.observed_property)
            completed = summary_uri(window.subject, window.observed_property, seq)
            self.store.update(f"""
WITH <{self.graph}>
DELETE {{ {live} ?p ?o }}
INSERT {{ {completed} ?p ?o ; review:windowSeq {seq} }}
WHERE  {{ {live} ?p ?o }}""")
            self._prune(window.subject, window.observed_property, seq)
            closed += 1
        return closed

    def _next_seq(self, subject_uri: str, observed_property: str) -> int:
        rows = bindings(self.store.query(f"""
SELECT (MAX(?n) AS ?seq) WHERE {{ GRAPH <{self.graph}> {{
  ?s a review:ObservationSummary ; sosa:hasFeatureOfInterest <{subject_uri}> ;
     sosa:observedProperty <{observed_property}> ; review:windowSeq ?n }} }}"""))
        held = rows[0].get("seq") if rows else None
        return (int(held) + 1) if held is not None else 1

    def _prune(self, subject_uri: str, observed_property: str, newest: int) -> None:
        """Drop windows older than the ring. This is what keeps the cardinality fixed."""
        self.store.update(f"""
WITH <{self.graph}>
DELETE {{ ?s ?p ?o }}
WHERE  {{ ?s a review:ObservationSummary ; sosa:hasFeatureOfInterest <{subject_uri}> ;
            sosa:observedProperty <{observed_property}> ; review:windowSeq ?n ; ?p ?o .
          FILTER(?n <= {newest - RING}) }}""")

    # --- reading ------------------------------------------------------------------------

    def accumulating(self) -> list[Window]:
        """Every window currently being filled — one per subject and property."""
        return self._windows("FILTER NOT EXISTS { ?s review:windowSeq ?any }")

    def completed(self) -> list[Window]:
        """Every closed window still held, newest first."""
        return sorted(self._windows("?s review:windowSeq ?seq"),
                      key=lambda w: w.seq or 0, reverse=True)

    def newest(self) -> list[Window]:
        """The most recently closed window for each subject and property.

        What a review actually looks at: everything observed since the last time it looked.
        """
        out: dict[tuple[str, str], Window] = {}
        for window in self.completed():
            out.setdefault((window.subject, window.observed_property), window)
        return list(out.values())

    def _windows(self, extra: str) -> list[Window]:
        rows = bindings(self.store.query(f"""
SELECT ?subject ?property ?count ?min ?max ?sum ?squares ?first ?last ?seq
WHERE {{ GRAPH <{self.graph}> {{
  ?s a review:ObservationSummary ;
     sosa:hasFeatureOfInterest ?subject ; sosa:observedProperty ?property ;
     review:sampleCount ?count ; review:sampleMin ?min ; review:sampleMax ?max ;
     review:sampleSum ?sum ; review:sampleSumSquares ?squares ;
     review:firstAt ?first ; review:lastAt ?last .
  {extra}
}} }}"""))
        return [Window(
            subject=r["subject"], observed_property=r["property"],
            count=int(r["count"]), minimum=float(r["min"]), maximum=float(r["max"]),
            total=float(r["sum"]), total_squares=float(r["squares"]),
            first_at=_time(r.get("first")), last_at=_time(r.get("last")),
            seq=int(r["seq"]) if r.get("seq") is not None else None,
        ) for r in rows]

    def _read(self, node: str) -> Window | None:
        rows = bindings(self.store.query(f"""
SELECT ?count ?min ?max ?sum ?squares ?first ?last WHERE {{ GRAPH <{self.graph}> {{
  {node} review:sampleCount ?count ; review:sampleMin ?min ; review:sampleMax ?max ;
         review:sampleSum ?sum ; review:sampleSumSquares ?squares ;
         review:firstAt ?first ; review:lastAt ?last }} }} LIMIT 1"""))
        if not rows:
            return None
        r = rows[0]
        return Window(
            subject="", observed_property="",
            count=int(r["count"]), minimum=float(r["min"]), maximum=float(r["max"]),
            total=float(r["sum"]), total_squares=float(r["squares"]),
            first_at=_time(r.get("first")), last_at=_time(r.get("last")))


def _time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
