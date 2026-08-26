"""The keeper: the ledger of what this agent is committed to, and the patience that makes a
commitment mean something.

**The kernel's, and granted by nothing.** This was Keeping, a member of a family
whose premise was a stake AND a lever. What that could never explain is why `Agent.__init__`
already built an intention STORE for every agent regardless: the modality was unconditional and
the thing that writes it was a grant. Commitment is not plug-in-able, so both are the kernel's.

The family's second member was sketched and never written — something that weighs a commitment
against what has changed since it was made, the open-minded commitment of the BDI literature.
That remains a real alternative, and it is a PICK when someone builds it, not a grant: how
stubborn to be is already each agent's own belief, and which rule decides to drop belongs beside
it rather than in the world graph.

**This existed before it had a name, as module state.** `bidding.pending` was an intention to
observe; a bid awaiting its claim was an intention to acquire; both lived in Python attributes
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

from .beliefs import BeliefError, Picks
from . import vocabulary
from .act import Act
from .module import Module, Timer
from .store import bindings

from .graphs import intentions_graph
from .ontology import AG

#  What an intention is made of — the mind's own words, and they were the kernel's already
#  (the-mind-is-six-graphs). What has joined them is the four figures the KEEPING member used to
#  own privately: a patience, a suspicion threshold and the bounds on the patience. They are the
#  kernel's now for the same reason the class is — every agent keeps a ledger, so a figure that
#  governs keeping is not one package's private setting.
INTENTION_CLASS = AG + "Intention"
BY = AG + "by"
PURSUES = AG + "pursues"
ADOPTED_AT = AG + "adoptedAt"
RESOLVED_AT = AG + "resolvedAt"
OUTCOME = AG + "outcome"
BECAUSE_OF = AG + "becauseOf"

# The means — what kind of act the commitment is to.

# The commitment policy — the belief, not the mechanism.
PATIENCE_S = AG + "patienceS"

# The expectation — the END, judged apart from the action.
EXPECTS_RISE = AG + "expectsRise"
BASELINE_VALUE = AG + "baselineValue"
BASELINE_AT = AG + "baselineAt"
EXPECTS_DELTA = AG + "expectsDelta"
#  `ag:deadlineAt` WAS HERE: the watch's deadline is the ACT's `ag:notAfter` now — one window,
#  read by the keeper, the bidder's give-up and the host's redeem check alike
#  (an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan). `vocabulary` migrates it.
END_MET = AG + "endMet"
END_VERIFIED_AT = AG + "endVerifiedAt"
SUSPECT_AFTER = AG + "suspectAfter"
MET_FRACTION = AG + "metFraction"


def kernel(name: str) -> str:
    """A mind state, by local name."""
    return AG + name

# What this package asks OF others — namespaces, never Python. The direction a lever moves the
# property it is priced in is the domain's statement (#127), copied into the expectation row;
# sensing is asked to look once so the baseline is the freshest thing on record.
#  The sensing family, the two market directions and the direction query WERE HERE. The keeper
#  used to look up which way a dose should move the value (the market's word) and ask sensing
#  to look once (the sensing family's name) when a watch opened — the last package words this
#  file named. Both are the ACTOR's to say: whoever opened the watch knows which way its act
#  pushes and how long a reading of that property takes to arrive, and nudges its own sensing.

# How many consecutive unmet ends make an affordance suspect — the family's figure, like the
# patience bounds: what this society tolerates before it stops trusting a claim.
_SUSPECT_Q = """
SELECT ?n WHERE {
  GRAPH ?g { ag:Intention ag:suspectAfter ?n }
} LIMIT 1"""

# The fraction of an expected delta that counts as the world answering (#165). Carried by
# `ag:Intention` itself now that there is no family to hang it on — what a society accepts as
# evidence is a fact about intentions, not about one way of keeping them.
_MET_FRACTION_Q = """
SELECT ?f WHERE {
  GRAPH ?g { ag:Intention ag:metFraction ?f }
} LIMIT 1"""


@dataclass(frozen=True)
class KeepingBeliefs:
    """The commitment policy, which is the agent's own opinion."""

    patience_s: int


#  `capability` only names whoever wanted the pick, for the error a missing one raises. There
#  is no capability here any more, so it names the thing itself: an agent that keeps commitments
#  and states no patience is missing something `ag:Intention` needs, not something it was granted.
KEEPING_PICKS = Picks(
    capability=INTENTION_CLASS,
    cls=KeepingBeliefs,
    terms={"patience_s": PATIENCE_S},
)


@dataclass(frozen=True)
class Standing:
    """One unresolved commitment, as a reader gets it back: the ACT committed to, and the want
    it pursues. `ag:by` names the act node (an-act-is-a-filled-action…); the action, the
    lever and the quantity are the act's, read through it."""

    uri: str
    act: Act
    want: str               # the desire's node — `ag:pursues`; the kernel's only key besides the act
    adopted_at: datetime

    @property
    def action(self) -> str:
        return self.act.action

    @property
    def via(self) -> str | None:
        return self.act.via or None

    def age_s(self, now: datetime | None = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.adopted_at).total_seconds()


@dataclass(frozen=True)
class OpenExpectation:
    """A watch still on: the act happened, and the world has yet to answer as promised."""

    uri: str
    action: str
    want: str
    rises: bool             # which way the act promised to move the value
    baseline: float
    baseline_at: datetime
    deadline: datetime
    expected_delta: float | None = None  # how far the act should move it, when the actor knows


class Keeper(Module):
    """The keeper. Speaks to no topic; its callers are its siblings, through the agent."""

    name = "intention"

    def __init__(self, agent):
        super().__init__(agent)
        self.graph = intentions_graph(agent.id)
        self._tick: Timer | None = None
        self._picks = None
        #  A volume from before the ledger keyed on the want: rows carrying a property are
        #  given the want that property names for this agent, once, at construction.
        about_of = {r["want"]: r["about"] for r in bindings(agent.desires.query_union(
            f"SELECT ?want ?about WHERE {{ <{self.me.uri}> <{AG}holds> ?want . "
            f"?want <{AG}about> ?about }}"))}
        if (n := vocabulary.migrate_ledger(agent.intentions, self.graph, about_of)):
            self.log.info("ledger migrated: %d row(s) keyed by a property now pursue a want", n)
        if (n := vocabulary.migrate_ledger_acts(agent.intentions, self.graph)):
            self.log.info("ledger migrated: %d row(s) naming an action now commit to an act", n)

    @property
    def beliefs(self) -> KeepingBeliefs:
        """The commitment policy, read on FIRST USE and not at construction.

        This was read in `__init__`, which was right while keeping was a capability: an agent
        that had been granted it had also been given a patience, and a missing one was a
        genesis error worth refusing to boot over. Every agent has a keeper now, and reading
        eagerly turned "this agent states no patience" into "this agent cannot start" — which
        killed `world/sensing`'s stakeless agent and every minimal fixture in the suite.

        Lazy is not a softening of the check, and this is the part worth being careful about.
        `ag:KeeperShape` still REFUSES to let an agent with a stake boot without a patience
        inside the constitutional bounds, so nothing that commits can reach this without one.
        What lazy buys is that an agent with nothing to commit about never asks — the same rule
        the deliberator's `series()` follows, one level down: the need follows the fact rather
        than the grant. An agent with neither a stake nor a patience that somehow reaches a
        commitment still raises here, naming the missing term, exactly as before.
        """
        if self._picks is None:
            self._picks = self.agent.desires.read(KEEPING_PICKS)
        return self._picks

    @beliefs.setter
    def beliefs(self, picks: KeepingBeliefs) -> None:
        """Install a policy directly, skipping the read.

        A setter because the attribute WAS one, and two callers legitimately assign it: a test
        pinning behaviour at a chosen patience, and any future `on_belief_revised` taking up a
        re-picked one. Making it lazy must not quietly turn an assignment into an AttributeError
        at the one moment a revision lands.
        """
        self._picks = picks

    def start(self) -> None:
        # The non-market entry into deliberation (#208): on my own patience clock, collect
        # what the modules notice, ask the one deliberator, commit what it proposes. The
        # patience is the rate bound by construction — an impulse younger than it is absorbed
        # by adopt() anyway, so ticking faster would only ask questions whose answers are
        # already standing.
        #  No patience, no clock. An agent that states none has no stake (the shape guarantees
        #  the converse), so there are no gaps for this tick to collect and nothing it could
        #  commit — starting a timer to ask would be a thread per agent to answer "nothing".
        try:
            interval = float(self.beliefs.patience_s)
        except BeliefError:
            self.log.debug("no patience stated and no stake to spend it on — the tick stays off")
            return
        self._tick = Timer(interval, self.deliberate_on_gaps)
        self._tick.start()

    def stop(self) -> None:
        if self._tick:
            self._tick.stop()

    # --- gap-driven deliberation (#208) --------------------------------------------------

    def deliberate_on_gaps(self) -> None:
        """Every want, through execution. Noticing is plural; deciding is not; doing is one road.

        Deliberation used to run only when the market knocked, and then this tick carried out
        ONE of the deliberator's answers — Observe — and dropped the rest on the floor, because
        an Acquire needs a round nobody may convene from here. It still does; what changed is
        that the commitment is made anyway. `execution.pursue` plans, writes the head row to
        this ledger and hands it to its actor, and an actor that cannot act now says so and
        the intention STANDS — so the bidder answers the next offer from what it already
        committed to, without a second search. See knowledge/domain/execution.md.

        Duties are skipped: a host serves on a presentation or when stock arrives with a
        claim held, and hosting runs execution on those events itself.

        The cost is a plan per want per patience period, which is the same work `series()`
        already does on the metrics clock.
        """
        from . import revision

        for desire in self.agent.pursuing():
            if desire.is_duty:
                continue
            revision.wake_for(self.agent, desire)

    # --- the ledger, written -------------------------------------------------------------

    def adopt(self, act, want: str, because: str, via: str | None = None) -> str | None:
        """Commit to one ACT toward one want. Returns the intention's IRI, or None.

        `act` is an `Act` — the plan's head, sized, through its lever — or, for an actor
        committing on its own event with nothing sized (a held claim), the action's IRI and
        the lever as `via`. Either way the ledger holds an act NODE: `ag:by` names it, and it
        carries `ag:fills` the action, `ag:through` the lever, `ag:quantity` and the window
        (an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan).

        KEYED ON (ACTION, WANT) and nothing else: a want is its node, and the kernel no longer
        knows what one is about (the-stake-is-sensings-want). Two commitments about one
        property but different wants were always distinct — a dealer owing water to fern and
        to tomato holds two Serving rows — and the property was only ever the coarser key.

        `via` is the lever the plan's head goes through — written as `ag:through`, so the
        ledger says which valve or venue and the actor handed the row later knows too.
        Execution passes it; an actor adopting on its own event (a held claim) may not.

        `desire` is which end this serves — the bounds an agent is held to, or the obligation a
        claim raised. Optional, because the first three means predate desires having names; a
        commitment without one is keyed as it always was. WITH one, two commitments about the
        same property but different desires are distinct: a dealer owing water to fern and to
        tomato holds two Apply rows that would otherwise be indistinguishable, so satisfying
        one would satisfy both and the patience would absorb the second impulse as the first.

        **None is the amortisation**: an intention with the same means and property already
        stands and is younger than my patience, so the impulse is absorbed rather than
        re-decided — the caller should treat it exactly as it treats its own cooldowns. A
        standing one PAST my patience is superseded: resolved as dropped with the reason
        recorded, and the new commitment adopted, because honouring a commitment forever is as
        wrong as honouring it not at all.
        """
        if isinstance(act, str):
            act = Act(action=act, via=via or "")
        action = act.action
        now = datetime.now(timezone.utc)
        for standing in self.standing(action=action, want=want):
            if standing.age_s(now) <= self.beliefs.patience_s:
                return None
            self._resolve(standing, "dropped",
                          f"outwaited: stood {standing.age_s(now):.0f}s against a patience "
                          f"of {self.beliefs.patience_s}s, superseded by a new adoption")
        stem = uuid.uuid4().hex[:8]
        uri = f"{AG}intent_{self.agent.id}_{stem}"
        act_uri = f"{AG}act_{self.agent.id}_{stem}"
        xsd = "http://www.w3.org/2001/XMLSchema#"
        facts = [f'<{kernel("fills")}> <{action}>']
        if act.via:
            facts.append(f'<{kernel("through")}> <{act.via}>')
        if act.for_agent:
            facts.append(f'<{kernel("forAgent")}> <{act.for_agent}>')
        if act.quantity is not None:
            facts.append(f'<{kernel("quantity")}> "{act.quantity}"^^<{xsd}decimal>')
        if act.not_before:
            facts.append(f'<{kernel("notBefore")}> "{act.not_before.isoformat()}"^^<{xsd}dateTime>')
        if act.not_after:
            facts.append(f'<{kernel("notAfter")}> "{act.not_after.isoformat()}"^^<{xsd}dateTime>')
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> a <{kernel("Intention")}> ;
    <{kernel("pursues")}> <{want}> ;
    <{kernel("by")}> <{act_uri}> ;
    <{kernel("adoptedAt")}> "{now.isoformat()}"^^<{xsd}dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
  <{act_uri}> a <{kernel("Act")}> ; {" ; ".join(facts)} .
}} }}""")
        self.log.info("adopted %s for %s: %s", action.rsplit("#", 1)[-1], _short(want), because)
        self._tell("adopted", action, want, because)
        return uri

    def satisfy(self, action: str, want: str | None, because: str) -> list[str]:
        """The world answered: whatever stood for this action and want is done — or, with the
        want omitted, for this action toward anything.

        Returns the resolved rows' IRIs, because resolving the MEANS is where an expectation
        about the END begins — the caller hands them straight to `expect`.

        Naming the desire is what keeps one debt from discharging another: without it, a dose
        that answered fern's claim would resolve tomato's too, since both are Apply rows about
        soil moisture. Omitted, it resolves every row for the means and property, which is
        what every caller predating desires meant and still action.
        """
        resolved = []
        for standing in self.standing(action=action, want=want):
            self._resolve(standing, "satisfied", because)
            resolved.append(standing.uri)
        return resolved

    def drop(self, action: str, want: str | None, because: str) -> None:
        """The commitment died without being met, and the reason is the record.

        A commitment abandoned without a reason is indistinguishable from one forgotten, which
        is why the argument is not optional.
        """
        for standing in self.standing(action=action, want=want):
            self._resolve(standing, "dropped", because)

    def _resolve(self, standing: Standing, outcome: str, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{standing.uri}> <{kernel("resolvedAt")}> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
          <{kernel("outcome")}> {_literal(outcome)} ;
          <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("%s: %s", outcome, because)
        self._tell(outcome, standing.action, standing.want, because)

    def _tell(self, kind: str, action: str, want: str, because: str) -> None:
        """One transition into the kernel's event buffer (#125), for the operator's eyes.

        The ledger stays the record; this is a projection — the reporting capability drains it
        into the agent's own bucket on its own tick, so nothing new is granted and an agent
        without that sink simply keeps a bounded buffer nobody empties. Local names, because a
        dashboard tag is for filtering by a person, exactly as the log lines above shorten.
        """
        self.agent.metrics.event(kind, because, means=action.rsplit("#", 1)[-1],
                                 want=_short(want))

    # --- the expectation: the end, judged apart from the means (#131) ---------------------

    def expect(self, intention_uri: str, because: str,
               expected_delta: float | None = None,
               lands_after_s: float | None = None,
               rises: bool | None = None,
               seeing_s: float | None = None,
               baseline=None,
               not_after: datetime | None = None) -> bool:
        """Open the watch: the act happened, now the world owes a movement.

        THE DEADLINE IS THE ACT'S WINDOW. `not_after`, where the actor states it (the act it
        committed to carries one), or else the landing time plus the seeing time computed
        here — and either way it is written as the act's `ag:notAfter`, so the ledger holds
        one window and every reader reads that one.

        The BASELINE — the reading the actor holds, handed in — is copied into the row: the
        sensed graph keeps only the current witness, so the before of any before/after survives
        nowhere but the ledger. WHICH WAY the value
        should move is the actor's to say: `rises`, or the sign of `expected_delta` — how far
        the act should move the property when the actor can size it (#165), which is what the
        met-verdict measures its margin against. An act that cannot size itself passes `rises`
        alone and keeps the exact-crossing verdict. The keeper used to look the direction up
        from the market's statement on the valuation; that is a package word, and the actor
        that opened the watch already holds it.

        The DEADLINE is the act's landing time (`lands_after_s`, asked of the effect rule by
        the actor, #247) PLUS how long a reading of that property may honestly take to arrive
        (`seeing_s`, the cadence the actor's sensing keeps) — both figures somebody already
        states. An act that cannot size itself gets the patience, unchanged: how long an agent
        waits before re-deciding, not how long the physics takes, and holding a dose to it
        called a valve late at 120s while the pot's own sensor reported every 600.

        The actor also asks its sensing to look once after opening the watch, so the freshest
        before is on record; the keeper no longer names the sensing family to do it.

        False rather than a row when something needed is missing — no reading to baseline on,
        no direction said — and the reason is logged: an expectation that cannot be judged
        would sit unverified forever, which is indistinguishable from the failure it exists to
        catch.
        """
        #  THE BASELINE IS THE ACTOR'S TO HAND IN: the reading it holds, value and instant.
        #  The keeper used to read it off the belief base itself, which meant knowing what a
        #  reading looks like — sensing's knowledge, not the ledger's. Anything with `.value`
        #  and `.result_time` will do; a reading with no instant cannot be a before.
        reading = baseline
        if reading is None or getattr(reading, "result_time", None) is None:
            self.log.warning("cannot expect an end for %s — no baselined reading to leave from",
                             _short(intention_uri))
            return False
        if rises is None and expected_delta:
            rises = expected_delta > 0
        if rises is None:
            self.log.warning("cannot expect an end for %s — the actor said which way it "
                             "should move neither by sign nor by word", _short(intention_uri))
            return False
        expected_delta = abs(expected_delta) if expected_delta else None
        now = datetime.now(timezone.utc)
        window = (lands_after_s + (seeing_s or 0.0) if lands_after_s is not None
                  else float(self.beliefs.patience_s))
        deadline_dt = not_after or datetime.fromtimestamp(now.timestamp() + window,
                                                          tz=timezone.utc)
        window = (deadline_dt - now).total_seconds()
        delta = (f"""
    <{EXPECTS_DELTA}> "{expected_delta}"^^<http://www.w3.org/2001/XMLSchema#decimal> ;"""
                 if expected_delta else "")
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention_uri}>{delta}
    <{EXPECTS_RISE}> {"true" if rises else "false"} ;
    <{BASELINE_VALUE}> "{reading.value}"^^<http://www.w3.org/2001/XMLSchema#decimal> ;
    <{BASELINE_AT}> "{reading.result_time.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.window(intention_uri, deadline_dt)
        self.log.info("expecting %s to %s from %.3f within %ss: %s",
                      _short(intention_uri),
                      "rise" if rises else "fall", reading.value, round(window), because)
        return True

    def window(self, intention_uri: str, not_after: datetime) -> None:
        """Set the window's close on the act an intention names — the one figure the bidder's
        give-up, the host's redeem check and the expectation's verdict all read."""
        self.agent.intentions.update(f"""
DELETE {{ GRAPH <{self.graph}> {{ ?act <{kernel("notAfter")}> ?was }} }}
INSERT {{ GRAPH <{self.graph}> {{ ?act <{kernel("notAfter")}> "{not_after.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
WHERE  {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("by")}> ?act .
                                  OPTIONAL {{ ?act <{kernel("notAfter")}> ?was }} }} }}""")

    def open_expectations(self, want: str | None = None) -> list[OpenExpectation]:
        """Every watch still on: expectation adopted, end not yet verified — for one want, or
        for all of them."""
        prop = f"FILTER(?want = <{want}>)" if want else ""
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?i ?action ?want ?rises ?baseline ?baselineAt ?deadline ?delta WHERE {{
  GRAPH <{self.graph}> {{
    ?i <{kernel("by")}> ?act ;
       <{kernel("pursues")}> ?want .
    ?act <{kernel("fills")}> ?action ;
         <{kernel("notAfter")}> ?deadline .
    ?i <{EXPECTS_RISE}> ?rises ;
       <{BASELINE_VALUE}> ?baseline ;
       <{BASELINE_AT}> ?baselineAt .
    OPTIONAL {{ ?i <{EXPECTS_DELTA}> ?delta }}
    FILTER NOT EXISTS {{ ?i <{END_MET}> ?met }}
    {prop}
  }} }}"""))
        return [OpenExpectation(
            uri=r["i"], action=r["action"], want=r["want"],
            rises=r["rises"] in ("true", "1"), baseline=float(r["baseline"]),
            baseline_at=datetime.fromisoformat(r["baselineAt"]),
            deadline=datetime.fromisoformat(r["deadline"]),
            expected_delta=float(r["delta"]) if r.get("delta") else None) for r in rows]

    def judge(self, want: str, value: float) -> None:
        """A number arrived for this want: judge every open watch on it.

        Told by sensing, per want — a reading is about a property, and which wants that is
        about is sensing's to say (the-stake-is-sensings-want). This was a choir hook on a
        reading, keyed by property in the ledger; the ledger keys on the want now.

        Met when the value crosses the baseline in the promised direction — early is fine,
        that is the dose landing — and, where the act sized itself (expectsDelta), crosses by
        at least metFraction of that size (#165): a lying instrument can breathe past a
        baseline, and a watch closed by grain is the false-knowledge detector defeated by
        noise. Unmet only at the deadline: movement the wrong way before it proves nothing,
        since a dose may land late. The verdict is a separate fact from the outcome, written
        beside it — satisfied-and-unmet is the false-knowledge signature review and the
        dashboard look for.

        A reading is also a look that happened (#208), and the sensing module — the actor
        for the look — satisfies the standing Observe itself now; this used to do it by name,
        and it was the last kernel reference holding that means here. An Observe
        can stand that no auction is waiting on, and the reading IS its arrival.
        """
        now = datetime.now(timezone.utc)
        for watch in self.open_expectations(want):
            moved = value > watch.baseline if watch.rises else value < watch.baseline
            if moved and watch.expected_delta:
                # The margin (#165): a movement is the world answering only when it is
                # commensurate with the act — metFraction of what the dose should have moved.
                # A breath of instrument grain past the baseline closed a watch two seconds
                # before its dose landed, live, and the closed watch then let the same gap be
                # bought twice (#167). Crossing alone stops counting where the act sized itself.
                moved = (abs(value - watch.baseline)
                         >= self._met_fraction() * watch.expected_delta)
            if moved:
                self._verdict(watch, True, f"moved from {watch.baseline} to {value}")
            elif now >= watch.deadline:
                self._verdict(watch, False,
                              f"deadline passed at {value}, baseline {watch.baseline} — the "
                              f"act was honoured and the world did not answer as the graph "
                              f"promised")

    def _verdict(self, watch: OpenExpectation, met: bool, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{watch.uri}> <{END_MET}> "{'true' if met else 'false'}"^^<http://www.w3.org/2001/XMLSchema#boolean> ;
                <{END_VERIFIED_AT}> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
                <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        (self.log.info if met else self.log.warning)(
            "end %s for %s: %s", "met" if met else "UNMET", _short(watch.want), because)
        self._tell("end-met" if met else "end-unmet", watch.action, watch.want, because)
        #  A COMMITMENT THAT STOOD UNTIL THE WORLD ANSWERED is done now, either way. An
        #  Actuate stands from the command to this verdict (#353) — the intention is to the
        #  END, and while it stands `adopt` absorbs the next impulse by the ordinary rule,
        #  which is what the actuator's ledger-reading guard used to do by hand. Satisfied,
        #  not dropped, whatever the verdict: the act was taken, and satisfied-and-unmet is
        #  the false-knowledge signature this ledger exists to record. An Acquire was already
        #  satisfied by its claim and this finds nothing standing.
        for s in self.standing(action=watch.action, want=watch.want):
            if s.uri == watch.uri:
                self._resolve(s, "satisfied",
                              f"the world answered — end {'met' if met else 'unmet'}")
        if not met and self._is_suspect(watch.action, watch.want):
            self.log.warning(
                "AFFORDANCE SUSPECT: %s toward %s has not paid %d times running — the graph "
                "claims a movement the world keeps refusing",
                watch.action.rsplit("#", 1)[-1], _short(watch.want), self._suspect_after())

    def _suspect_after(self) -> int:
        rows = bindings(self.agent.beliefs.query(_SUSPECT_Q))
        return int(rows[0]["n"]) if rows else 3

    def _met_fraction(self) -> float:
        rows = bindings(self.agent.beliefs.query(_MET_FRACTION_Q))
        return float(rows[0]["f"]) if rows else 0.25

    def _is_suspect(self, action: str, want: str) -> bool:
        """The last suspectAfter verdicts for this pair, all unmet, none met among them.

        Consecutive rather than cumulative, so one success resets the count: an affordance
        that mostly pays is noisy, not false.
        """
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?met WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("by")}> ?act ;
     <{kernel("pursues")}> <{want}> ;
     <{END_MET}> ?met .
  ?act <{kernel("fills")}> <{action}> .
  ?i
     <{END_VERIFIED_AT}> ?at .
}} }} ORDER BY DESC(?at) LIMIT {self._suspect_after()}"""))
        n = self._suspect_after()
        return len(rows) >= n and all(r["met"] == "false" for r in rows)

    def suspects(self) -> list[tuple[str, str]]:
        """Every (action, want) pair currently suspect. What review and the report read."""
        pairs = {(r["action"], r["want"]) for r in bindings(self.agent.intentions.query(f"""
SELECT DISTINCT ?action ?want WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("by")}> ?act ;
     <{kernel("pursues")}> ?want ;
     <{END_MET}> ?met .
  ?act <{kernel("fills")}> ?action .
}} }}"""))}
        return sorted(p for p in pairs if self._is_suspect(*p))

    # --- what sensing asks me: the verification watch ----------------------------------

    def watching(self, want: str) -> bool:
        """Is a watch on for this want, its deadline not yet passed?

        The two processes run at different speeds — evaporation is fractions per day, a dose
        lands in seconds — and the one place urgency-by-state gets it wrong is right after
        acting: the value improves, attention would relax, and the dose would land unobserved.
        So an open expectation IS urgency, and sensing folds this into its cadence as the
        maximal answer: it tightens the moment the watch opens and relaxes the moment it
        resolves, bounded by the deadline so a dead sensor cannot hold the fast cadence for
        ever. This was the keeper's answer to the reading choir, keyed by property; the want
        is the key now, and sensing asks per want it holds about the property it is pacing.
        """
        now = datetime.now(timezone.utc)
        return any(now < w.deadline for w in self.open_expectations(want))

    def standing(self, action: str | None = None, want: str | None = None) -> list[Standing]:
        """What stands: adopted and not resolved. The question a deliberator asks first."""
        clauses = [f"?i a <{kernel('Intention')}> ; <{kernel('by')}> ?act ; "
                   f"<{kernel('pursues')}> ?want ; "
                   f"<{kernel('adoptedAt')}> ?at .",
                   f"?act <{kernel('fills')}> ?action .",
                   f"FILTER NOT EXISTS {{ ?i <{kernel('resolvedAt')}> ?done }}"]
        if action:
            clauses.append(f"FILTER(?action = <{action}>)")
        if want:
            clauses.append(f"FILTER(?want = <{want}>)")
        for term in ("through", "quantity", "forAgent", "notBefore", "notAfter"):
            clauses.append(f'OPTIONAL {{ ?act <{kernel(term)}> ?{term} }}')
        rows = bindings(self.agent.intentions.query(
            "SELECT ?i ?act ?action ?want ?at ?through ?quantity ?forAgent ?notBefore ?notAfter "
            "WHERE { GRAPH <%s> { %s } }" % (self.graph, " ".join(clauses))))
        return [Standing(
            uri=r["i"], want=r["want"], adopted_at=datetime.fromisoformat(r["at"]),
            act=Act(action=r["action"], via=r.get("through") or "", want=r["want"],
                    quantity=float(r["quantity"]) if r.get("quantity") else None,
                    for_agent=r.get("forAgent"),
                    not_before=datetime.fromisoformat(r["notBefore"]) if r.get("notBefore") else None,
                    not_after=datetime.fromisoformat(r["notAfter"]) if r.get("notAfter") else None))
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
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?met (COUNT(?i) AS ?n) WHERE {{ GRAPH <{self.graph}> {{
  ?i <{END_MET}> ?met }} }} GROUP BY ?met"""))
        counts = {r["met"]: int(r["n"]) for r in rows}
        out["expectations_open"] = len(self.open_expectations())
        out["expectations_met"] = counts.get("true", 0)
        out["expectations_unmet"] = counts.get("false", 0)
        out["affordances_suspect"] = len(self.suspects())
        return out


def _short(iri: str) -> str:
    """A node's local name, for a log line or a dashboard tag."""
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _literal(text: str) -> str:
    """A prose reason as a safe SPARQL string literal."""
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
