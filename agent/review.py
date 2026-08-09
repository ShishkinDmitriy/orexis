"""An agent re-picking a belief, inside the room it committed to.

A belief is not a constant. It is a **point chosen inside a range** — a computer needs one value
to act on, so genesis picks one and the agent lives with it. What genesis wrote is therefore the
*first pick* and nothing more. Treating it as a bound confuses a choice with a constraint, and
leaves the author's real job — saying how much room the agent has — unwritten.

The room comes from three constraints, intersected:

    WORLD   what the society allows at all — figures the capability family states
    SENSOR  what the equipment can do — stated on a device (declared; nothing states one yet)
    SELF    what this agent commits to — `ag:commits`, in its own beliefs, narrower than the world

Four rules make this a re-pick rather than a drift.

**Which beliefs may move is declared by the package that owns the term**, as one triple in its
own `ontology.ttl`, and found by asking the merged T-Box. Nothing lists them and no Python knows
their names — which is what keeps adding a capability the act of adding a directory. A capability
with an ontology nobody here has read is reviewable on the same terms as this one.

**A rule is SPARQL, not code.** `capabilities/<name>/review.rq`, beside the `rules.ru` that
derives the capability itself: one revisable term, one SELECT, one `?value`. It can read the
evidence, the beliefs and the T-Box, and it can do nothing else — a SELECT cannot write, cannot
call out, and cannot loop unboundedly. Because an agent's store already contains only what it
may see, the sandbox is the isolation design rather than anything added here.

**Legitimacy is the boot check re-run.** After applying, the agent calls `validate_agent` — the
identical call `runtime.Agent.__init__` makes, against the identical shapes — and reverts if it
fails. A revision is allowed exactly when the agent could have started holding it, so there is
no second notion of "in bounds" to fall out of step with the first.

**It plans its own next arising, and remembers what it declined.** Every decision — taken or
declined — records when it is worth revisiting, far enough out that a fresh window of readings
could have accumulated. Checking sooner is reading the same evidence twice. Recording a decline
is what separates reflection from a twitch: without it the same question is re-argued at every
arising and the agent can never notice it has said no eleven times.

**Absence is meaningful.** An agent that states no `ag:reviewIntervalS` never reviews itself and
its beliefs are exactly what genesis wrote.

The one thing this may write is its own beliefs graph. It reads the world as constraint and
`:sensed` as evidence, and changes neither.

See knowledge/decisions/a-belief-is-a-pick-within-a-range.md.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import loader
from .beliefs import Block
from .ontology import ONTOLOGY_GRAPH, beliefs_graph, evidence_graph, revisions_graph, term
from .store import bindings, decimal
from .summary import Summaries
from .upkeep import BeliefBaseUpkeep
from .validate import BeliefsInvalid, validate_agent

log = logging.getLogger("review")

SELF_REVIEW = term("SelfReview")

# What a `review.rq` may say instead of an instance identifier. The rule is shipped in a package
# and must name no agent and no graph of one, so the three things it cannot know are substituted
# before it runs. Everything else it needs it discovers, exactly as code here does.
ME, EVIDENCE, BELIEFS = "$me", "$evidence", "$beliefs"


@dataclass(frozen=True)
class SelfReviewBeliefs:
    interval_s: int


SELF_REVIEW_BLOCK = Block(
    capability=SELF_REVIEW,
    cls=SelfReviewBeliefs,
    terms={"interval_s": "reviewIntervalS"},
)


@dataclass(frozen=True)
class Range:
    """The room one term has, after every constraint that applies to it."""

    term: str  # the belief's IRI
    floor: float
    ceiling: float

    def holds(self, value: float) -> bool:
        return self.floor <= value <= self.ceiling

    @property
    def fixed(self) -> bool:
        """No room at all. How an author says a figure is not up for review — by leaving
        nowhere to go, rather than by a flag somewhere that says not to look."""
        return self.floor == self.ceiling


# --- what may be re-picked, and how far --------------------------------------------------

_REVISABLE_Q = f"""
SELECT ?term ?bound (MIN(?v) AS ?low) (MAX(?v) AS ?high) WHERE {{
  GRAPH <{ONTOLOGY_GRAPH}> {{
    ?term a ag:RevisableBelief ; ag:revisableToward ?bound .
    ?family ?bound ?v .
  }}
}} GROUP BY ?term ?bound"""


def world_ranges(query) -> dict[str, Range]:
    """Every revisable term the T-Box declares, and what the society allows for it.

    The two ends are read from the VALUES of the constitutional figures a package points at,
    not from the names of the properties pointing at them — so a package names the two limits it
    already declares and invents no ordering vocabulary.
    """
    seen: dict[str, list[float]] = {}
    for row in bindings(query(_REVISABLE_Q)):
        for key in ("low", "high"):
            if row.get(key) is not None:
                seen.setdefault(row["term"], []).append(float(row[key]))
    return {t: Range(t, min(vs), max(vs)) for t, vs in seen.items() if vs}


class Reviewer:
    """The agent's second thoughts. Built always; arises only when told to."""

    def __init__(self, agent):
        self.agent = agent
        self.upkeep = BeliefBaseUpkeep(agent)
        self.summaries = Summaries(agent.store, agent.id)
        self.rules = loader.review_rules()
        self.revisions = self.declined = self.refused = 0
        # The floor between two arisings, read here rather than handed in at start(), because it
        # bounds the HORIZON as well as the timer — and a reviewer that has not been started can
        # still be asked to review, which is exactly what a test does. Zero means the agent
        # stated none and never reviews itself at all.
        stated = agent.beliefs.read_optional(SELF_REVIEW_BLOCK)
        self.interval_s = stated.interval_s if stated else 0
        self._timer: threading.Timer | None = None
        self._stopped = False

    # --- the room a term has -------------------------------------------------------------

    def ranges(self) -> dict[str, Range]:
        """World, narrowed by what this agent committed to. Sensor constraints when any exist."""
        out = world_ranges(self.agent.store.query)
        for row in bindings(self.agent.store.query(f"""
SELECT ?term ?below ?above WHERE {{ GRAPH <{beliefs_graph(self.agent.id)}> {{
  <{self.agent.me.uri}> ag:commits ?c . ?c ag:onTerm ?term .
  OPTIONAL {{ ?c ag:notBelow ?below }} OPTIONAL {{ ?c ag:notAbove ?above }} }} }}""")):
            held = out.get(row["term"])
            if held is None:
                # A commitment about a term nothing declares revisable. Said out loud rather
                # than ignored: it is an author constraining something that cannot move, which
                # is almost always a typo in a term name.
                log.warning("%s commits on <%s>, which no package declares revisable",
                            self.agent.id, row["term"])
                continue
            floor = max(held.floor, float(row["below"])) if row.get("below") else held.floor
            ceiling = min(held.ceiling, float(row["above"])) if row.get("above") else held.ceiling
            out[row["term"]] = Range(held.term, floor, min(max(floor, ceiling), held.ceiling))
        return out

    def current(self, belief_term: str) -> float | None:
        rows = bindings(self.agent.store.query(f"""
SELECT ?v WHERE {{ GRAPH <{beliefs_graph(self.agent.id)}> {{
  <{self.agent.me.uri}> <{belief_term}> ?v }} }} LIMIT 1"""))
        return float(rows[0]["v"]) if rows else None

    # --- what it saw ---------------------------------------------------------------------

    def publish_evidence(self, ranges: dict[str, Range]) -> int:
        """Derive the statistics a rule reads, and the room each term has. Returns how many.

        Every figure is computable without knowing what a property MEANS — which is exactly what
        lets one rule serve a domain nobody has written yet.
        """
        graph = evidence_graph(self.agent.id)
        now = datetime.now(timezone.utc)
        held = len(self.summaries.completed())
        lines = []
        for window in self.summaries.newest():
            age = (now - window.last_at).total_seconds() if window.last_at else 0.0
            gap = window.gap_s
            lines.append(f"""
  [] a ag:Evidence ;
     sosa:hasFeatureOfInterest <{window.subject}> ;
     ag:ofProperty <{window.observed_property}> ;
     ag:sampleCount {window.count} ;
     ag:sampleMin {decimal(window.minimum)} ;
     ag:sampleMax {decimal(window.maximum)} ;
     ag:sampleMean {decimal(window.mean)} ;
     ag:sampleSpread {decimal(window.spread)} ;
     ag:newestAgeS {decimal(age)} ;
     ag:windowsHeld {held} ;
     {f'ag:sampleGapS {decimal(gap)} ;' if gap else ''}
     ag:windowSeq {window.seq or 0} .""")
        for r in ranges.values():
            lines.append(f"""
  [] a ag:Range ; ag:onTerm <{r.term}> ;
     ag:notBelow {decimal(r.floor)} ; ag:notAbove {decimal(r.ceiling)} .""")
        self.agent.store.put_graph(graph, "")
        if lines:
            self.agent.store.update(
                f"INSERT DATA {{ GRAPH <{graph}> {{ {''.join(lines)} }} }}")
        return len(lines)

    # --- what the rules propose ------------------------------------------------------------

    def proposals(self) -> list[tuple[str, float]]:
        """Every (term, value) the shipped rules propose. A rule with nothing to say returns
        no rows, which is how "not enough evidence yet" is expressed — as an unsatisfied
        pattern rather than a sentinel."""
        out: list[tuple[str, float]] = []
        for path in self.rules:
            query = (path.read_text()
                     .replace(ME, f"<{self.agent.me.uri}>")
                     .replace(EVIDENCE, evidence_graph(self.agent.id))
                     .replace(BELIEFS, beliefs_graph(self.agent.id)))
            try:
                rows = bindings(self.agent.store.query(query))
            except Exception as exc:
                # A rule that will not run is a broken package, not a broken agent.
                log.error("%s: %s would not run: %s", self.agent.id, path.name, exc)
                continue
            for row in rows:
                if row.get("term") is None or row.get("value") is None:
                    log.warning("%s: %s returned a row binding no ?term and ?value",
                                self.agent.id, path.name)
                    continue
                out.append((row["term"], float(row["value"])))
        return out

    # --- one arising -----------------------------------------------------------------------

    def review(self) -> None:
        """Keep the house, close the window, look at what accumulated, decide. Never raises."""
        try:
            self.upkeep.consider()
        except Exception as exc:
            log.error("%s: upkeep failed: %s", self.agent.id, exc)
        try:
            self.summaries.roll()
            ranges = self.ranges()
            self.publish_evidence(ranges)
            due = self._due()
            for belief_term, value in self.proposals():
                room = ranges.get(belief_term)
                if room is None:
                    log.warning("%s: a rule proposed <%s>, which nothing declares revisable",
                                self.agent.id, belief_term)
                    continue
                if belief_term in due:
                    continue  # already settled, and not yet worth re-arguing
                self.settle(room, value)
        except Exception as exc:
            log.error("%s: review failed: %s", self.agent.id, exc)

    def settle(self, room: Range, value: float) -> bool:
        """Take it, or decline it — and either way say when to look again."""
        held = self.current(room.term)
        if held is None:
            return False
        if not room.holds(value):
            # The rule's arithmetic disagrees with the constraints. Not applied, and not
            # silently clamped either: a rule that proposes out of range is wrong about
            # something, and quietly correcting it would hide that.
            log.warning("%s: a rule proposed %s for <%s>, outside %s..%s — ignored",
                        self.agent.id, value, room.term, room.floor, room.ceiling)
            self._remember(room.term, held, value, "refused", "proposed outside its own range")
            self.refused += 1
            return False
        if value == held:
            self._remember(room.term, held, held, "declined", "the evidence supports what I hold")
            self.declined += 1
            return False
        return self._apply(room, held, value)

    def _apply(self, room: Range, was: float, value: float) -> bool:
        graph = beliefs_graph(self.agent.id)
        self._write(graph, room.term, value)
        try:
            validate_agent(self.agent.store, self.agent.id, self.agent.me.uri,
                           self.agent.me.capabilities)
        except BeliefsInvalid as exc:
            self._write(graph, room.term, was)
            self.refused += 1
            self._remember(room.term, was, value, "refused", "the shapes refused it")
            log.warning("%s: <%s> -> %s refused by the shapes, reverted to %s\n%s",
                        self.agent.id, room.term, value, was, exc)
            return False

        self.revisions += 1
        self._remember(room.term, was, value, "taken", "the evidence no longer supports it")
        log.info("%s: <%s> %s -> %s", self.agent.id, room.term, was, value)
        # Modules read their block once, into a frozen dataclass. A revision nothing tells them
        # about would not take effect until the next restart, which makes the whole mechanism
        # look broken rather than absent.
        for module in self.agent.modules:
            try:
                module.on_belief_revised(room.term, value)
            except Exception as exc:
                log.error("%s: %s could not take up the revision: %s",
                          self.agent.id, module.name, exc)
        return True

    def _write(self, graph: str, belief_term: str, value) -> None:
        self.agent.store.update(f"""
DELETE {{ GRAPH <{graph}> {{ <{self.agent.me.uri}> <{belief_term}> ?old }} }}
INSERT {{ GRAPH <{graph}> {{ <{self.agent.me.uri}> <{belief_term}> {_literal(value)} }} }}
WHERE  {{ GRAPH <{graph}> {{ <{self.agent.me.uri}> <{belief_term}> ?old }} }}""")

    # --- memory, which is also the schedule -------------------------------------------------

    def horizon_s(self) -> float:
        """How long until a fresh window could possibly exist, from the rate actually observed.

        Generic on purpose: it is the mean gap between readings times the number of readings a
        window holds, and neither figure needs to know what is being measured. A decision made
        now is worth revisiting when there is genuinely something new to look at, and not before.
        """
        gaps = [w.gap_s for w in self.summaries.newest() if w.gap_s]
        counts = [w.count for w in self.summaries.newest() if w.count]
        if not gaps or not counts:
            return float(self.interval_s)
        return max(float(self.interval_s), max(gaps) * max(counts))

    def _remember(self, belief_term: str, was, now, outcome: str, why: str) -> None:
        at = datetime.now(timezone.utc)
        due = at + timedelta(seconds=self.horizon_s())
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{revisions_graph(self.agent.id)}> {{
  [] a ag:Revision ;
     ag:revisedTerm <{belief_term}> ;
     ag:fromValue {_literal(was)} ;
     ag:toValue {_literal(now)} ;
     ag:outcome "{outcome}" ;
     ag:atTime "{at.isoformat()}"^^xsd:dateTime ;
     ag:dueAt "{due.isoformat()}"^^xsd:dateTime ;
     ag:becauseOf {_string(why)} .
}} }}""")

    def _due(self) -> set[str]:
        """Terms whose last decision is not yet worth revisiting."""
        now = datetime.now(timezone.utc).isoformat()
        return {r["term"] for r in bindings(self.agent.store.query(f"""
SELECT DISTINCT ?term WHERE {{ GRAPH <{revisions_graph(self.agent.id)}> {{
  ?r a ag:Revision ; ag:revisedTerm ?term ; ag:dueAt ?due .
  FILTER(?due > "{now}"^^xsd:dateTime) }} }}"""))}

    def next_wake_s(self) -> float:
        """When to arise again: the soonest outstanding decision, floored by the stated interval.

        The floor is all `ag:reviewIntervalS` is. It stops a review planning something absurdly
        soon; it does not set the schedule, because only the decision knows when its own effect
        could show.
        """
        rows = bindings(self.agent.store.query(f"""
SELECT (MIN(?due) AS ?soonest) WHERE {{ GRAPH <{revisions_graph(self.agent.id)}> {{
  ?r a ag:Revision ; ag:dueAt ?due }} }}"""))
        soonest = rows[0].get("soonest") if rows else None
        if not soonest:
            return float(self.interval_s)
        try:
            at = datetime.fromisoformat(str(soonest).replace("Z", "+00:00"))
        except ValueError:
            return float(self.interval_s)
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        wait = (at - datetime.now(timezone.utc)).total_seconds()
        return max(float(self.interval_s), wait)

    # --- lifecycle ---------------------------------------------------------------------------

    def start(self) -> None:
        """Begin arising. A no-op for an agent that stated no interval — absence is the decision,
        and it is checked here so there is one place that knows what silence means."""
        if not self.interval_s:
            return
        log.info("%s: reviewing itself, no sooner than every %ss",
                 self.agent.id, self.interval_s)
        self._schedule(float(self.interval_s))

    def _schedule(self, delay: float) -> None:
        if self._stopped:
            return
        self._timer = threading.Timer(delay, self._arise)
        self._timer.daemon = True
        self._timer.start()

    def _arise(self) -> None:
        try:
            self.review()
        finally:
            self._schedule(self.next_wake_s())

    def stop(self) -> None:
        self._stopped = True
        if self._timer:
            self._timer.cancel()


def _literal(value) -> str:
    """A number as SPARQL. Integers stay integers: the shapes demand xsd:integer, and a cadence
    written as a decimal would fail its own validation the moment it was applied."""
    if isinstance(value, bool):
        return f'"{str(value).lower()}"^^xsd:boolean'
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return f'"{int(value)}"^^xsd:integer'
    return f'"{value}"^^xsd:decimal'


def _string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
