"""An agent re-picking a belief, inside the room it was given.

A belief is not a constant. It is a **point chosen inside a range** — a computer needs one value
to act on, so genesis picks one and the agent lives with it. What genesis wrote is therefore the
*first pick* and nothing more. Treating it as a bound confuses a choice with a constraint, and
leaves the author's real job — saying how much room the agent has — unwritten.

The room comes from three constraints, intersected, and **all three are public**:

    CONSTITUTION  what the society allows at all — figures the capability family states
    HARDWARE      what the equipment can do — stated on a device (declared; nothing states one yet)
    MANDATE       what THIS agent's world allows it — `review:commits`, narrower than the constitution

The third was briefly private, on the reasoning that how far an agent will let itself move is its
own opinion. That has it backwards: a range is what an agent is *allowed*, imposed by whoever
ratified its world, and **an agent constraining itself is not a constraint, it is a choice**. The
choice — the pick inside the range — is what stays private. Range public, value private.

**And the mandate is what grants this capability at all.** An agent given room to move must be
able to use it, so `review:commits` is the premise the derivation rule reads (see `rules.ru`). An
agent with no mandate does not have this module, keeps no summaries, and never arises: the
mechanism is absent rather than idle, which is what a deployment wanting no drift should get.

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

The one thing this may write is its own beliefs graph. It reads the world as constraint and
`:sensed` as evidence, and changes neither.

**Belief-base upkeep is not here.** Compacting a bloated store is not a choice an agent makes,
so it stayed in the kernel on its own clock when this became optional — otherwise an agent with
no mandate would silently stop compacting and undo the fix for #45. See `agora/upkeep.py`.

See knowledge/decisions/self-review-is-a-capability.md.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from agent import loader
from agent.module import Module
from agent.ontology import beliefs_graph
from agent.store import bindings, decimal
from agent.validate import BeliefsInvalid, validate_agent

from .beliefs import REVIEW_BLOCK
from .graphs import evidence_graph, revisions_graph
from .summary import Summaries
from .terms import RECKONING

log = logging.getLogger("review")

# What a `review.rq` may say instead of an instance identifier. The rule is shipped in a package
# and must name no agent and no graph of one, so the three things it cannot know are substituted
# before it runs. Everything else it needs it discovers, exactly as code here does.
ME, EVIDENCE, BELIEFS = "$me", "$evidence", "$beliefs"


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
  
    ?term a review:RevisableBelief ; review:revisableToward ?bound .
    ?family ?bound ?v .
  
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


class ReviewModule(Module):
    """The agent's second thoughts — `review:Reckoning`, derived from having been given room.

    A module rather than a fixture of the runtime, because the judgement is the replaceable part:
    an implementation that asked a model instead of running a rule would be a sibling of this
    class registered in the same `PROVIDES`, and nothing else would move.
    """

    CAPABILITY = RECKONING
    name = "review"

    def __init__(self, agent):
        super().__init__(agent)
        self.summaries = Summaries(agent.store, agent.id)
        self.rules = loader.review_rules()
        self.revisions = self.declined = self.refused = 0
        # The floor between two arisings. Required now, not optional: an agent holding this
        # module was granted a mandate, and one that may re-pick must say how often it will look.
        # Absence used to mean "never review", which put a public ability's switch in a private
        # file — the mandate is the switch now, and it is in the world where a shape can see it.
        self.interval_s = agent.beliefs.read(REVIEW_BLOCK).interval_s
        self._timer: threading.Timer | None = None
        self._stopped = False

    # --- what I fold in as it arrives ------------------------------------------------------

    def on_reading_recorded(self, subject_uri: str, observed_property: str,
                            value: float) -> None:
        """Keep the running account this module's own judgement is made from.

        Through the hook every module already gets, rather than by the ingest path calling into
        a capability. Two things follow that are worth having: the kernel does not import a
        package that may not be installed, and an agent given no room to move accumulates
        nothing — because there is nothing it could conclude from it.
        """
        try:
            self.summaries.record(subject_uri, observed_property, value)
        except Exception as exc:
            # A lost summary is lost grounds for a later judgement, not a lost reading — the
            # measurement is already recorded by the time this runs.
            self.log.error("summary write failed: %s", exc)

    def reports(self) -> dict:
        """What this module wants in its agent's health series.

        Contributed rather than read out of it: `metrics.py` cannot name a package that may not
        be installed, and an agent with no mandate should be silent on these rather than report
        three zeroes it could never move.
        """
        out = {
            "belief_revisions": self.revisions,
            # Decisions to change nothing. A conscience that only reported the changes it made
            # would look identical whether it was thinking hard and concluding no, or not
            # arising at all — and those are very different states to be in.
            "belief_reviews_declined": self.declined,
            # Revisions the shapes refused. Flat at zero says the rules are proposing only what
            # the constitution allows; a rising line is a rule whose arithmetic disagrees with
            # the shapes, which is a bug in the rule and not a misbehaving agent.
            "belief_revisions_refused": self.refused,
        }
        # TOWARD WHAT, not merely that (#61). The counts say an agent changed its mind and how
        # often, and the range is the whole governance surface: the only evidence a range was
        # mis-authored is what agents do inside it, and every agent relaxing the same figure to
        # its ceiling is the strongest signal this design can produce — unobservable while the
        # picks lived in a private graph in a private container. One field per revisable term
        # the agent holds, into its OWN bucket, so the operator sees it and rivals do not: the
        # channel is the same one every figure above already rides. An author who cannot see
        # how latitude is used grants narrow ranges, which is the same as granting none.
        for term in sorted(self.ranges()):
            value = self.current(term)
            if value is not None:
                out[_field_name(term)] = value
        return out

    # --- the room a term has -------------------------------------------------------------

    def ranges(self) -> dict[str, Range]:
        """The constitution, narrowed by this agent's mandate, and by what its equipment allows.

        The mandate is read from the world rather than from beliefs, which is what lets the
        derivation see it — a capability granted by a private fact could not be derived at all.
        No graph is named: a commitment is the sovereign's and its term may be entailed, so the
        two can live apart and the default graph is what merges them.

        The third source stopped being hypothetical. `review:limitedTo` is what the equipment
        allows, derived at genesis from the `ssn-system:Frequency` an agent's sensors declare —
        so a board that cannot be read faster than every thirty seconds floors its agent at
        thirty, and the agent can no longer commit to a cadence the board will never keep. Both
        narrow by the same arithmetic, which is why one alternation covers them; they are
        separate predicates because a mandate is a governance fact and this is a fact about a
        board, and a revision refused by one should not read as refused by the other.
        """
        out = world_ranges(self.agent.store.query)
        for row in bindings(self.agent.store.query(f"""
SELECT ?term ?below ?above WHERE {{
  <{self.agent.me.uri}> review:commits|review:limitedTo ?c . ?c review:onTerm ?term .
  OPTIONAL {{ ?c review:notBelow ?below }} OPTIONAL {{ ?c review:notAbove ?above }} }}""")):
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
  [] a review:Evidence ;
     sosa:hasFeatureOfInterest <{window.subject}> ;
     review:ofProperty <{window.observed_property}> ;
     review:sampleCount {window.count} ;
     review:sampleMin {decimal(window.minimum)} ;
     review:sampleMax {decimal(window.maximum)} ;
     review:sampleMean {decimal(window.mean)} ;
     review:sampleSpread {decimal(window.spread)} ;
     review:newestAgeS {decimal(age)} ;
     review:windowsHeld {held} ;
     {f'review:sampleGapS {decimal(gap)} ;' if gap else ''}
     review:windowSeq {window.seq or 0} .""")
        for r in ranges.values():
            lines.append(f"""
  [] a review:Range ; review:onTerm <{r.term}> ;
     review:notBelow {decimal(r.floor)} ; review:notAbove {decimal(r.ceiling)} .""")
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
        """Close the window, look at what accumulated, decide. Never raises."""
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
  [] a review:Revision ;
     review:revisedTerm <{belief_term}> ;
     review:fromValue {_literal(was)} ;
     review:toValue {_literal(now)} ;
     review:outcome "{outcome}" ;
     review:atTime "{at.isoformat()}"^^xsd:dateTime ;
     review:dueAt "{due.isoformat()}"^^xsd:dateTime ;
     review:becauseOf {_string(why)} .
}} }}""")
        # A change of mind is a marker over the series (#125), beside the intention story: the
        # picked_* fields show WHERE a belief sits, this shows the MOMENT it moved and why.
        # Taken and refused only — a decline is the routine outcome of most arisings, and its
        # count above is the right voice for something that happens on schedule.
        if outcome != "declined":
            local = belief_term.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            self.agent.metrics.event(f"belief-{outcome}",
                                     f"{local}: {was} -> {now} — {why}", term=local)

    def _due(self) -> set[str]:
        """Terms whose last decision is not yet worth revisiting."""
        now = datetime.now(timezone.utc).isoformat()
        return {r["term"] for r in bindings(self.agent.store.query(f"""
SELECT DISTINCT ?term WHERE {{ GRAPH <{revisions_graph(self.agent.id)}> {{
  ?r a review:Revision ; review:revisedTerm ?term ; review:dueAt ?due .
  FILTER(?due > "{now}"^^xsd:dateTime) }} }}"""))}

    def next_wake_s(self) -> float:
        """When to arise again: the soonest outstanding decision, floored by the stated interval.

        The floor is all `review:reviewIntervalS` is. It stops a review planning something absurdly
        soon; it does not set the schedule, because only the decision knows when its own effect
        could show.
        """
        rows = bindings(self.agent.store.query(f"""
SELECT (MIN(?due) AS ?soonest) WHERE {{ GRAPH <{revisions_graph(self.agent.id)}> {{
  ?r a review:Revision ; review:dueAt ?due }} }}"""))
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
        """Begin arising. Reached only by an agent the world gave room to move."""
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


def _field_name(term: str) -> str:
    """`picked_sensing_slowSleepS` from a term IRI — a series field, filtered by a person.

    The namespace's tail is kept, not stripped: two packages may each declare a `slowSleepS`
    in their own namespace, and the stripped form cannot tell them apart — the exact latent
    collision `on_belief_revised`'s comment records one level down.
    """
    ns, _, local = term.rpartition("#")
    if not ns:
        ns, _, local = term.rpartition("/")
    return f"picked_{ns.rstrip('/').rsplit('/', 1)[-1]}_{local}"


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
