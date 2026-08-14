"""intention:Keeping — the ledger of what this agent is committed to, and the patience that
makes a commitment mean something.

**This existed before it had a name, as module state.** `bidding.pending` was an intention to
observe; a bid awaiting its voucher was an intention to acquire; both lived in Python attributes
that died with the process and answered to nothing. They are rows in a graph now, with an
adoption time, a resolution, and a reason — so an operator can ask what an agent thought it was
doing, and phase 4's deliberator can ask what already stands before deciding anything.

**Nothing here decides, and the seam is deliberate.** Whoever acts calls `adopt` when it acts
and `satisfy`/`drop` when the world answers; this module only keeps the ledger honest. The one
piece of policy it owns is the COMMITMENT itself: `adopt` refuses to re-adopt what is already
standing and younger than the agent's patience, and that refusal is the amortisation the
decision record is named for — within your patience, a second impulse to do the same thing is
absorbed, not re-decided. With an LLM deliberator that absorption is the cost model.

Vocabulary: packages/capability/intention/ontology.ttl. Rules: its shapes.ttl. Derivation: its
rules.ru. See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from agent.beliefs import Block
from agent.module import Module
from agent.store import bindings

from .graphs import intentions_graph
from .terms import (APPLY, BASELINE_AT, BASELINE_VALUE, BECAUSE_OF, DEADLINE_AT, END_MET,
                    END_VERIFIED_AT, EXPECTS_VALUE_TO, KEEPING, NS, PATIENCE_S, term)

# What this package asks OF others — namespaces, never Python. The direction a lever moves the
# property it is priced in is the domain's statement (#127), copied into the expectation row;
# sensing is asked to look once so the baseline is the freshest thing on record.
_SENSING = "http://example.org/agora/sensing#SensingCapability"
_RAISES = "http://example.org/agora/market#Raises"
_LOWERS = "http://example.org/agora/market#Lowers"
_DIRECTION_Q = """
SELECT ?direction WHERE {
  ?term market:aboutProperty <%s> ; market:direction ?direction
} LIMIT 1"""

# How many consecutive unmet ends make an affordance suspect — the family's figure, like the
# patience bounds: what this society tolerates before it stops trusting a claim.
_SUSPECT_Q = """
SELECT ?n WHERE {
  GRAPH ?g { intention:IntentionCapability intention:suspectAfter ?n }
} LIMIT 1"""


@dataclass(frozen=True)
class KeepingBeliefs:
    """intention:Keeping — the commitment policy, which is the agent's own opinion."""

    patience_s: int


KEEPING_BLOCK = Block(
    capability=KEEPING,
    cls=KeepingBeliefs,
    terms={"patience_s": PATIENCE_S},
)


@dataclass(frozen=True)
class Standing:
    """One unresolved commitment, as a reader gets it back."""

    uri: str
    means: str
    observed_property: str
    adopted_at: datetime

    def age_s(self, now: datetime | None = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.adopted_at).total_seconds()


@dataclass(frozen=True)
class OpenExpectation:
    """A watch still on: the act happened, and the world has yet to answer as promised."""

    uri: str
    means: str
    observed_property: str
    direction: str          # market:Raises or market:Lowers — which way the value should move
    baseline: float
    baseline_at: datetime
    deadline: datetime


class IntentionModule(Module):
    """The keeper. Speaks to no topic; its callers are its siblings, through the agent."""

    CAPABILITY = KEEPING
    name = "intention"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(KEEPING_BLOCK)
        self.graph = intentions_graph(agent.id)

    # --- the ledger, written -------------------------------------------------------------

    def adopt(self, means: str, observed_property: str, because: str) -> str | None:
        """Commit to one means toward one property. Returns the intention's IRI, or None.

        **None is the amortisation**: an intention with the same means and property already
        stands and is younger than my patience, so the impulse is absorbed rather than
        re-decided — the caller should treat it exactly as it treats its own cooldowns. A
        standing one PAST my patience is superseded: resolved as dropped with the reason
        recorded, and the new commitment adopted, because honouring a commitment forever is as
        wrong as honouring it not at all.
        """
        now = datetime.now(timezone.utc)
        for standing in self.standing(means=means, observed_property=observed_property):
            if standing.age_s(now) <= self.beliefs.patience_s:
                return None
            self._resolve(standing, "dropped",
                          f"outwaited: stood {standing.age_s(now):.0f}s against a patience "
                          f"of {self.beliefs.patience_s}s, superseded by a new adoption")
        uri = f"{NS}intent_{self.agent.id}_{uuid.uuid4().hex[:8]}"
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> a <{term("Intention")}> ;
    <{term("by")}> <{means}> ;
    <http://www.w3.org/ns/ssn/forProperty> <{observed_property}> ;
    <{term("adoptedAt")}> "{now.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("adopted %s(%s): %s",
                      means.rsplit("#", 1)[-1], observed_property.rsplit("#", 1)[-1], because)
        self._tell("adopted", means, observed_property, because)
        return uri

    def satisfy(self, means: str, observed_property: str, because: str) -> list[str]:
        """The world answered: whatever stood for this means and property is done.

        Returns the resolved rows' IRIs, because resolving the MEANS is where an expectation
        about the END begins — the caller hands them straight to `expect`.
        """
        resolved = []
        for standing in self.standing(means=means, observed_property=observed_property):
            self._resolve(standing, "satisfied", because)
            resolved.append(standing.uri)
        return resolved

    def drop(self, means: str, observed_property: str, because: str) -> None:
        """The commitment died without being met, and the reason is the record.

        A commitment abandoned without a reason is indistinguishable from one forgotten, which
        is why the argument is not optional.
        """
        for standing in self.standing(means=means, observed_property=observed_property):
            self._resolve(standing, "dropped", because)

    def _resolve(self, standing: Standing, outcome: str, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{standing.uri}> <{term("resolvedAt")}> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
          <{term("outcome")}> {_literal(outcome)} ;
          <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("%s: %s", outcome, because)
        self._tell(outcome, standing.means, standing.observed_property, because)

    def _tell(self, kind: str, means: str, observed_property: str, because: str) -> None:
        """One transition into the kernel's event buffer (#125), for the operator's eyes.

        The ledger stays the record; this is a projection — the reporting capability drains it
        into the agent's own bucket on its own tick, so nothing new is granted and an agent
        without that sink simply keeps a bounded buffer nobody empties. Local names, because a
        dashboard tag is for filtering by a person, exactly as the log lines above shorten.
        """
        self.agent.metrics.event(kind, because, means=means.rsplit("#", 1)[-1],
                                 property=observed_property.rsplit("#", 1)[-1])

    # --- the expectation: the end, judged apart from the means (#131) ---------------------

    def expect(self, intention_uri: str, observed_property: str, because: str) -> bool:
        """Open the watch: the act happened, now the world owes a movement.

        The BASELINE is copied into the row — the sensed graph keeps only the current witness,
        so the before of any before/after survives nowhere but the ledger. The DIRECTION comes
        from the domain's own statement on its valuation (#127), copied so the row stays
        judgeable even if the vocabulary is later amended. The DEADLINE is the patience — a
        recorded seam; the dose and the physics could derive a better one. And sensing is
        asked to look once, so the freshest possible before is on record and the first after
        arrives sooner.

        False rather than a row when something needed is missing — no reading to baseline on,
        no direction stated — and the reason is logged: an expectation that cannot be judged
        would sit unverified forever, which is indistinguishable from the failure it exists to
        catch.
        """
        reading = self.agent.beliefs.current_reading(self.me.acts_for, observed_property)
        if reading is None or reading.result_time is None:
            self.log.warning("cannot expect an end for %s — no baselined reading to leave from",
                             observed_property)
            return False
        rows = bindings(self.agent.store.query(_DIRECTION_Q % observed_property))
        if not rows:
            self.log.warning("cannot expect an end for %s — the domain states no direction",
                             observed_property)
            return False
        direction = rows[0]["direction"]
        now = datetime.now(timezone.utc)
        deadline = now.timestamp() + self.beliefs.patience_s
        deadline_dt = datetime.fromtimestamp(deadline, tz=timezone.utc)
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention_uri}>
    <{EXPECTS_VALUE_TO}> <{direction}> ;
    <{BASELINE_VALUE}> "{reading.value}"^^<http://www.w3.org/2001/XMLSchema#decimal> ;
    <{BASELINE_AT}> "{reading.result_time.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <{DEADLINE_AT}> "{deadline_dt.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("expecting %s to move %s from %.3f within %ss: %s",
                      observed_property.rsplit("#", 1)[-1],
                      direction.rsplit("#", 1)[-1], reading.value,
                      self.beliefs.patience_s, because)
        if (sensing := self.agent.provider(_SENSING)) is not None:
            sensing.sense_now()
        return True

    def open_expectations(self, observed_property: str | None = None) -> list[OpenExpectation]:
        """Every watch still on: expectation adopted, end not yet verified."""
        prop = f"FILTER(?property = <{observed_property}>)" if observed_property else ""
        rows = bindings(self.agent.store.query(f"""
SELECT ?i ?means ?property ?direction ?baseline ?baselineAt ?deadline WHERE {{
  GRAPH <{self.graph}> {{
    ?i <{term("by")}> ?means ;
       <http://www.w3.org/ns/ssn/forProperty> ?property ;
       <{EXPECTS_VALUE_TO}> ?direction ;
       <{BASELINE_VALUE}> ?baseline ;
       <{BASELINE_AT}> ?baselineAt ;
       <{DEADLINE_AT}> ?deadline .
    FILTER NOT EXISTS {{ ?i <{END_MET}> ?met }}
    {prop}
  }} }}"""))
        return [OpenExpectation(
            uri=r["i"], means=r["means"], observed_property=r["property"],
            direction=r["direction"], baseline=float(r["baseline"]),
            baseline_at=datetime.fromisoformat(r["baselineAt"]),
            deadline=datetime.fromisoformat(r["deadline"])) for r in rows]

    def on_reading_recorded(self, subject_uri: str, observed_property: str,
                            value: float) -> None:
        """Every reading is a chance to judge an open watch.

        Met the moment the value crosses the baseline in the promised direction — early is
        fine, that is the dose landing. Unmet only at the deadline: movement the wrong way
        before it proves nothing, since a dose may land late. The verdict is a separate fact
        from the outcome, written beside it — satisfied-and-unmet is the false-knowledge
        signature review and the dashboard look for.
        """
        if subject_uri != self.me.acts_for:
            return
        now = datetime.now(timezone.utc)
        for watch in self.open_expectations(observed_property):
            moved = (value > watch.baseline if watch.direction == _RAISES
                     else value < watch.baseline)
            if moved:
                self._verdict(watch, True, f"moved from {watch.baseline} to {value}")
            elif now >= watch.deadline:
                self._verdict(watch, False,
                              f"deadline passed at {value}, baseline {watch.baseline} — the "
                              f"act was honoured and the world did not answer as the graph "
                              f"promised")

    def _verdict(self, watch: OpenExpectation, met: bool, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{watch.uri}> <{END_MET}> "{'true' if met else 'false'}"^^<http://www.w3.org/2001/XMLSchema#boolean> ;
                <{END_VERIFIED_AT}> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        (self.log.info if met else self.log.warning)(
            "end %s for %s: %s", "met" if met else "UNMET",
            watch.observed_property.rsplit("#", 1)[-1], because)
        self._tell("end-met" if met else "end-unmet", watch.means,
                   watch.observed_property, because)
        if not met and self._is_suspect(watch.means, watch.observed_property):
            self.log.warning(
                "AFFORDANCE SUSPECT: %s toward %s has not paid %d times running — the graph "
                "claims a movement the world keeps refusing",
                watch.means.rsplit("#", 1)[-1],
                watch.observed_property.rsplit("#", 1)[-1], self._suspect_after())

    def _suspect_after(self) -> int:
        rows = bindings(self.agent.store.query(_SUSPECT_Q))
        return int(rows[0]["n"]) if rows else 3

    def _is_suspect(self, means: str, observed_property: str) -> bool:
        """The last suspectAfter verdicts for this pair, all unmet, none met among them.

        Consecutive rather than cumulative, so one success resets the count: an affordance
        that mostly pays is noisy, not false.
        """
        rows = bindings(self.agent.store.query(f"""
SELECT ?met WHERE {{ GRAPH <{self.graph}> {{
  ?i <{term("by")}> <{means}> ;
     <http://www.w3.org/ns/ssn/forProperty> <{observed_property}> ;
     <{END_MET}> ?met ;
     <{END_VERIFIED_AT}> ?at .
}} }} ORDER BY DESC(?at) LIMIT {self._suspect_after()}"""))
        n = self._suspect_after()
        return len(rows) >= n and all(r["met"] == "false" for r in rows)

    def suspects(self) -> list[tuple[str, str]]:
        """Every (means, property) pair currently suspect. What review and the report read."""
        pairs = {(r["means"], r["property"]) for r in bindings(self.agent.store.query(f"""
SELECT DISTINCT ?means ?property WHERE {{ GRAPH <{self.graph}> {{
  ?i <{term("by")}> ?means ;
     <http://www.w3.org/ns/ssn/forProperty> ?property ;
     <{END_MET}> ?met .
}} }}"""))}
        return sorted(p for p in pairs if self._is_suspect(*p))

    # --- what sensing asks me: the verification watch ----------------------------------

    def urgency(self, subject_uri: str, observed_property: str, value: float) -> float | None:
        """Maximum, while a watch is on and its deadline has not passed.

        The two processes run at different speeds — evaporation is fractions per day, a dose
        lands in seconds — and the one place urgency-by-state gets it wrong is right after
        acting: the value improves, attention would relax, and the dose would land unobserved.
        So an open expectation IS urgency, and sensing's ordinary max-of-answers does the
        rest: cadence tightens the moment the watch opens and relaxes the moment it resolves.
        Bounded by the deadline so a dead sensor cannot hold the fast cadence forever.
        """
        if subject_uri != self.me.acts_for:
            return None
        now = datetime.now(timezone.utc)
        if any(now < w.deadline for w in self.open_expectations(observed_property)):
            return 1.0
        # A HELD claim is the same need one step earlier (#132): the dose is coming the moment
        # the watch is live, and the watch becomes live by exactly this urgency reaching the
        # board. Bounded by the patience like everything the keeper answers, so a claim the
        # bound will redeem blind anyway cannot hold the fast cadence forever.
        if any(s.age_s(now) <= self.beliefs.patience_s
               for s in self.standing(means=APPLY, observed_property=observed_property)):
            return 1.0
        return None

    # --- the ledger, read ----------------------------------------------------------------

    def standing(self, means: str | None = None,
                 observed_property: str | None = None) -> list[Standing]:
        """What stands: adopted and not resolved. The question a deliberator asks first."""
        clauses = [f"?i a <{term('Intention')}> ; <{term('by')}> ?means ; "
                   f"<http://www.w3.org/ns/ssn/forProperty> ?property ; "
                   f"<{term('adoptedAt')}> ?at .",
                   f"FILTER NOT EXISTS {{ ?i <{term('resolvedAt')}> ?done }}"]
        if means:
            clauses.append(f"FILTER(?means = <{means}>)")
        if observed_property:
            clauses.append(f"FILTER(?property = <{observed_property}>)")
        rows = bindings(self.agent.store.query(
            "SELECT ?i ?means ?property ?at WHERE { GRAPH <%s> { %s } }"
            % (self.graph, " ".join(clauses))))
        return [Standing(uri=r["i"], means=r["means"], observed_property=r["property"],
                         adopted_at=datetime.fromisoformat(r["at"]))
                for r in rows]

    def reports(self) -> dict:
        """How many commitments stand, and how old the oldest is.

        The second number is the one that catches trouble: a standing intention growing old is
        an agent that committed to something the world never answered — a bid whose round
        vanished, a look whose board went quiet — and that is invisible in every other series
        precisely because nothing is happening.
        """
        standing = self.standing()
        out: dict = {"intentions_standing": len(standing)}
        if standing:
            out["oldest_intention_s"] = round(max(s.age_s() for s in standing), 1)
        # The end-verdicts, counted from the ledger. `expectations_unmet` climbing while
        # `satisfied` outcomes accumulate is the false-knowledge signature in series form;
        # `affordances_suspect` above zero is the flag itself.
        rows = bindings(self.agent.store.query(f"""
SELECT ?met (COUNT(?i) AS ?n) WHERE {{ GRAPH <{self.graph}> {{
  ?i <{END_MET}> ?met }} }} GROUP BY ?met"""))
        counts = {r["met"]: int(r["n"]) for r in rows}
        out["expectations_open"] = len(self.open_expectations())
        out["expectations_met"] = counts.get("true", 0)
        out["expectations_unmet"] = counts.get("false", 0)
        out["affordances_suspect"] = len(self.suspects())
        return out


def _literal(text: str) -> str:
    """A prose reason as a safe SPARQL string literal."""
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
