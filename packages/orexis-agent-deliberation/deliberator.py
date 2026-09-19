"""The deliberator: given where the agent stands against what it wants, the next move.

**This is the mind's WHETHER, and it is the kernel's because a mind is not plug-in-able.** It
was `deliberation:Reflex` and `deliberation:Planning`, two members of a family, then one class
with two roads through it, and it is one class with ONE road now: every desire is answered by
the search.

**The reflex is gone, and it was ABSORBED rather than retired.** It asked whether a lever
points the right way — the gap's sign against the aim, cheapest rung first — and the search
asks whether taking the lever leaves this agent better off, which is the same question with
the case that matters added: a plant sitting ABOVE its region passes every test the reflex
applied, and that is how a society floods one while every module behaves as written. What kept
the reflex alive after the search subsumed it was three fall-backs, and all three were the
search saying *I cannot answer* — a lever whose package states no effect, a want nothing
measures, and no candidate at all. The first two are now refused at the GATES
(`orexis-validate`), because both are facts about ratified files rather than about a moment;
the third is a want with no lever, which is legitimate, legible, and answered by proposing
nothing. A second road kept for the cases the first cannot answer is a second road that
decides them all silently.

**Consulting survives as a seam, and a better one.** Asking a model what next is a genuine
alternative — it is the reason the extraction happened at all — but WHICH deliberator answers
is a choice, and this project puts choices in beliefs rather than in grants: it becomes a pick
(`orexis:deliberatesBy`) that an agent's review can move inside whatever room its mandate leaves,
not a capability its world derives for it once at genesis. Everything
knowledge/decisions/llm-heavy-deliberation.md fixes about it stands unchanged: a move from this
vocabulary's menu and never free text-to-action, the bid number stays deterministic, and the
keeper's patience bounds how often it is consulted.

**What stays out is everything but the whether.** The HOW is the actor's — a bid's quantity and
price are deterministic code, per knowledge/decisions/deterministic-bid.md, whoever said to bid.
The KEEPING is the ledger's: a deliberator reads what stands and never writes it, because
deciding and remembering what was decided are different things.

See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

import logging

from assembly.contribute import answer as contribution, contributes
from .beliefs import Picks
from orexis_agent_progression.keeper import (INTENTION_CLASS, PATIENCE_S, KeepingBeliefs,
                                                 NoPatience)
from orexis_agent_progression.timer import Timer

from . import planner, pursuit, trace
from orexis_agent_progression.act import Step
from orexis_agent_deliberation.judgment import Judgment


from orexis_agent_progression.ontology import (OREXIS, DELIBERATION_GRAPH, PLAN_FAILED, PLAN_FINISHED,
                                                  SERIES, STATE_GRAPH, STEP_DONE, picks_graph)
from .planner import Planner
from .plan import (EXHAUSTED, IMPROVED, NOTHING, NOT_BETTER, Plan, REFUSED,
                   REMEMBERED, SATISFIED)
from orexis_agent_progression.store import bindings

# What this package asks OF others, by family — their namespaces, never their Python.

# The moves. The intention package's individuals, referenced by IRI: a move IS what the keeper
# records when the actor carries it out, so naming anything else would put a translation table
# between deciding and remembering.
# The means are the kernel's words (the-mind-is-six-graphs): a move IS what the keeper
# records, and four packages name these, which is what makes them lingua franca.


#  THE KEEPER'S PICK, read HERE and handed down (#452): a pick is a belief, and progression —
#  where the keeper lives — reads none. `capability` only names whoever wanted the pick, for
#  the error a missing one raises; there is no capability here, so it names the thing itself.
KEEPING_PICKS = Picks(
    capability=INTENTION_CLASS,
    cls=KeepingBeliefs,
    terms={"patience_s": PATIENCE_S},
)


class Deliberator:
    """The decider. Speaks to no topic; its callers are its siblings, through the agent.

    NOT a `Module`, and it was one — for the reason the keeper gives: `Module` is the
    container's contract for a capability, and a layer may not import the container. The
    four names the runtime asks of everything in its module list are stated here, and the
    one contribution (`series`) is found by `assembly.contribute` on any object.
    """

    name = "deliberation"
    CAPABILITY = ""     # nothing a world grants — `provider()` can never return the deliberator

    def answer(self, term: str):
        """Whatever fills one point on me, as a bound method — or None. The same door a
        `Module` has, so whoever walks `agent.modules` asking by term finds this too."""
        return contribution(self, term)

    def __init__(self, agent):
        self.agent = agent
        self.me = agent.me
        self.log = logging.getLogger(f"{agent.id}.{self.name}")
        self._tick: Timer | None = None
        self._steps_done = 0        # what progression told me, for `series`
        self._steps_declined = 0
        self._plans_finished = 0
        self._decided: dict = {}       # want -> (plan, remembered plan or None) (#469)
        #  ONE PLANNER PER WANT (#553): the cone a pass leaves is the next pass's to resume,
        #  so the planner that holds it lives as long as the want is pursued.
        self._planners: dict = {}
        self._plans_failed = 0

    def pursued(self) -> list[tuple[Judgment, str | None]]:
        """Every desire this agent holds, with the move I propose for it — or None.

        Here because deciding what can be done is exactly what a deliberator is, and because
        the kernel may not name a capability's family: `agent.pursuing()` merges what the modules
        want, and this is the only place that can say whether anything answers.
        """
        return [(judgment, self.propose_for(judgment)) for judgment in self.agent.pursuing()]

    def start(self) -> None:
        """Drop whatever the last process was thinking.

        A trace describes a pass over a world, and the world moved while this agent was not
        running. Keeping one across a restart would leave the graph holding a decision about
        readings nobody has taken since — the same hazard as a trace outliving its pass, one
        lifecycle up. Cheap: the graph holds one pass per desire and most agents hold a handful.
        """
        self.agent.beliefs.clear_graph(DELIBERATION_GRAPH)
        # THE MIND'S OWN CLOCK — the non-market entry into deliberation (#208). On the agent's
        # patience, mark every want for reconsideration. The patience is the rate bound by
        # construction: an impulse younger than it is absorbed by the keeper's `adopt` anyway,
        # so ticking faster would only ask questions whose answers are already standing.
        #
        # This was the keeper's tick, and it searched synchronously on the timer's own thread.
        # Since #452 a timer lands on the reactive loop — the one executing thread, which must
        # never be held for a search — so what the tick does now is MARK (milliseconds) and the
        # reviser's thread does the searching. Same passes, same commitments; the search moved
        # off the clock's thread and onto the mind's, which is where the layering record put it.
        #
        #  No patience, no clock. An agent that states none has no stake (the shape guarantees
        #  the converse), so there are no gaps for this tick to collect and nothing it could
        #  commit — starting a timer to ask would be a clock per agent to answer "nothing".
        try:
            interval = float(self.agent.keeper.beliefs.patience_s)
        except NoPatience:
            self.log.debug("no patience stated and no stake to spend it on — the tick stays off")
            return
        self._tick = Timer(interval, self.tick)
        self._tick.start()

    def stop(self) -> None:
        if self._tick:
            self._tick.stop()

    def tick(self) -> None:
        """The clock landed, on the loop: mark every want that may be acted on and return.
        Never searches here. A want nobody may act on yet — a debt its holder has not
        presented — is left standing and hot; marking it would run a pass to decide nothing.
        It used to be debts that were skipped, by kind: a host serves on a presentation or
        when stock arrives, and hosting wakes the search on those itself. It still does; a
        presented debt the search could not serve is now reconsidered on the tick as any
        other want is, which is one more pass that finds nothing until the stock arrives."""
        for judgment in self.agent.pursuing():
            if judgment.pursuable:
                self.agent.reviser.note(judgment.uri, judgment)

    def deliberate_on_gaps(self) -> None:
        """Every want, through pursuit, NOW. Noticing is plural; deciding is not; doing is one road.

        The synchronous form of the tick — what a test calls to have the consequences before it
        asserts, and what the reviser's drain amounts to once every mark is taken. Deliberation
        used to run only when the market knocked, and then the tick carried out ONE of the
        deliberator's answers — Observe — and dropped the rest on the floor, because an Acquire
        needs a round nobody may convene from here. It still does; what changed is that the
        commitment is made anyway. `pursuit.pursue` plans, writes the head row to the ledger and
        hands it down to its actor, and an actor that cannot act now says so and the intention
        STANDS — so the bidder answers the next offer from what it already committed to,
        without a second search. See knowledge/domain/executor.md.

        What nobody may act on yet is skipped, as the tick skips it — see `tick`.
        """
        for judgment in self.agent.pursuing():
            if not judgment.pursuable:
                continue
            pursuit.pursue(self.agent, judgment)

    # --- what progression tells me (#452): a lower layer speaks upward only as an event -----

    @contributes(STEP_DONE)
    def on_step_done(self, act, intention: str, took: bool) -> None:
        """A committed act was handed to its actors, on the loop. Counted for `series`, and
        nothing more: a take that happened needs no new search, and one that did not is an
        intention standing for its trigger, which `adopt` absorbs until patience runs out."""
        self._steps_done += 1 if took else 0
        self._steps_declined += 0 if took else 1

    @contributes(PLAN_FINISHED)
    def on_plan_finished(self, intention: str, action: str, want: str) -> None:
        """The world answered as promised. COUNTED, not re-planned: the plan concluded, and the
        next trigger that could change the answer — an offer, a reading — wakes the search
        through its actor already. Marking here as well put a bid into a round that was still
        open the instant a dose answered, racing the next offer; the ledger already says the
        want was served, and whether more is due is the next pass's question, not this event's."""
        self._plans_finished += 1
        #  LIFT WHAT WORKED (#469): a plan the search found, walked to its end, is remembered
        #  for this want in the world it was decided in. A remembered plan finishing again is
        #  not lifted twice.
        from . import remembered
        decided = self._decided.get(want)
        if decided is not None and decided[1] is None and decided[0] is not None and decided[0].steps:
            steps = self.agent.keeper.walked(intention) if self.agent.keeper is not None else []
            if steps:
                remembered.lift(self.agent, want, steps, decided[0].cost)
        #  THE WANT DERIVED UNDER A ROOT IS WITHDRAWN WHEN ITS PLAN FINISHES (#618): a root
        #  still unmet derives it again on the next pass, through a fresh want.
        if pursuit.root_of(self.agent, want) is not None:
            pursuit.withdraw(self.agent, want)

    @contributes(PLAN_FAILED)
    def on_plan_failed(self, intention: str, action: str, want: str) -> None:
        """The deadline passed and the world did not answer. Re-plan: the want is marked and
        the worker searches again, with the unmet verdict in the ledger for the menu to
        read — the suspicion an affordance earns is progression's count, and what to do about
        a suspect lever is the search's."""
        self._plans_failed += 1
        #  FORGET WHAT FAILED (#469): a remembered plan that failed a step is not remembered.
        from . import remembered
        decided = self._decided.get(want)
        if decided is not None and decided[1] is not None:
            remembered.forget(self.agent, decided[1], "a step of it failed")
            self._decided.pop(want, None)
        elif decided is not None and decided[0] is not None and decided[0].steps:
            #  A plan the search found may BE a remembered route — walked as a candidate
            #  where the world differed (#469, second form) and chosen — so what failed is
            #  forgotten by its steps, whichever road adopted it.
            remembered.forget_matching(self.agent, want, decided[0].steps, "a step of it failed")
            self._decided.pop(want, None)
        self.agent.reviser.note(want)

    @contributes(SERIES)
    def series(self) -> list[tuple[str, dict, dict]]:
        """The ranking, as figures — and the split that stops it misleading.

        `unactionable` is a want nothing I can propose would move: a fern above its region and
        a fern below it are both unmet at urgency 1.00, and only one of them is anybody's to
        fix, because no lever in this society lowers moisture. Counting it needs both halves —
        the wants, which are the modules', and the moves, which are mine — so it is reported
        by the one module that sees both.
        """
        pursued = self.pursued()
        #  NOTHING TO DECIDE IS NOT ZERO THINGS DECIDED. An agent with no stake — world/sensing's
        #  records and wants nothing — used to contribute no rows here because it was granted no
        #  deliberation capability at all, and `Module.reports` says outright that the ABSENCE of
        #  a module's lines is itself a reading. Dissolving the capability into the kernel would
        #  have silently turned that reading into a row of zeros on every dashboard.
        #
        #  So absence follows the FACT rather than the grant: no wants, no rows. It says the same
        #  thing the missing capability used to say, and says it about what is true of the agent
        #  now rather than about what its world provisioned for it once.
        if not pursued:
            return []
        wanting = [(g, move) for g, move in pursued if not g.is_met]
        #  `agent_goals`, like `agent_want` below, KEEPS THE RETIRED WORD. The noun gave way to
        #  `desire` when the vocabulary was ruled on (domain/desire.md), and a measurement name
        #  is the one surface where the rename costs more than it buys: it has history behind it
        #  in the series store, so renaming splits every series at the cutover and leaves a
        #  dashboard reading half of one.
        rows = [("agent_goals", {}, {
            "desires": float(len(pursued)),
            "unmet": float(len(wanting)),
            "unactionable": float(sum(1 for _, move in wanting if move is None)),
            "hottest": max((g.urgency for g, _ in pursued), default=0.0),
        })]
        #  ONE ROW PER WANT, which is what makes a single graph able to show all of them.
        #  The tag is the want ITSELF and not the property it is about, because a property
        #  cannot name every want: freshness is per instrument, a debt is per claim, and a
        #  panel keyed on `property` could only ever draw stakes. Urgency is unit-free by
        #  construction, so a moisture, a look overdue and a litre owed belong on one axis —
        #  that is the whole claim of a common currency, and this is where it becomes visible.
        #
        #  NEVER BY THE INSTANCE a derived want is about. A jti is unique per round, so a debt
        #  tagged by its claim would mint a new series every time the society traded and make
        #  the store's cardinality grow with its history — the cost of a dashboard nobody
        #  could then load. A debt used to be tagged by whom it is owed to instead, which the
        #  kernel could say only by knowing what a debt was; whom a host owes is the market's
        #  figure now (`agent_debts`, per counterparty), and here a debt is a want under its
        #  root like any other.
        for judgment, _ in pursued:
            #  A want pursued under a root is reported as the ROOT (#618): one series per
            #  desire the agent holds, whichever node the pass is currently handed.
            about = (judgment.derived_from or judgment.uri).rsplit("#", 1)[-1]
            #  `agent_want` and its tag KEEP THE RETIRED WORD, deliberately. The noun "want"
            #  gave way to "desire" everywhere else when the vocabulary was ruled on
            #  (domain/desire.md), and a measurement name is the one place the rename costs more
            #  than it buys: it is an external surface with history behind it, so renaming
            #  splits every series at the cutover and leaves a dashboard reading half of one.
            #  The word is wrong and the continuity is worth more.
            rows.append(("agent_want", {"want": about}, {"urgency": float(judgment.urgency)}))

        #  HOW IT DECIDED, not just what it wants (#256). `pursued()` above has just re-planned
        #  every desire, so the trace holds this tick's verdicts — read from there rather than
        #  counted here, so the figure a dashboard shows and the answer `orexis-ask` gives are
        #  one fact. Six fields because a planner has six answers where returning a move or
        #  None had two, and the pair worth watching is `no candidate` against `exhausted`:
        #  one says equip me, the other says my doses are too coarse.
        verdicts = trace.outcomes(self.agent.beliefs.query_union)
        rows.append(("agent_deliberation", {}, {
            outcome.replace(" ", "_"): float(verdicts.get(outcome, 0))
            for outcome in (SATISFIED, IMPROVED, NOTHING,
                            EXHAUSTED, NOT_BETTER, REFUSED)}))
        #  WHAT IT COST, from the same pass and not a second one. `pursued()` above re-planned
        #  every desire this agent holds, so these are that work's own figures — asking again to
        #  measure would double the cost being measured, which is the one thing an observability
        #  change must not do.
        #
        #  Three of these exist to make a RECORDED LIMIT visible rather than to confirm health.
        #  `deepest` pinned at 1 was two of them at once — a rule's CONSTRUCTs running against
        #  the store rather than the world (#254), and a cycle signature that was only the
        #  desire's own value, so a step that moved nothing else looked like somewhere already
        #  reached (#258); both are closed. `blind` above zero is a package that never stated
        #  what its lever does. A number that shows a known defect is worth more than one that
        #  says things are fine.
        rows.append(("agent_planning", {}, {**trace.effort(self.agent.beliefs.query_union),
                                            #  what progression told me since the process
                                            #  started (#452): acts its actors took, and
                                            #  acts declined as "not now"
                                            "steps_taken": self._steps_done,
                                            "steps_declined": self._steps_declined,
                                            "plans_finished": self._plans_finished,
                                            "plans_failed": self._plans_failed}))
        return rows

    def propose_for(self, judgment: Judgment) -> str | None:
        """The MEANS of the move for one judgment, or None — `decide` projected to its head.

        Kept for every caller that wants only the kind of act; execution wants the row and
        asks `decide`. Silencing a deliberator means silencing both.
        """
        plan = self.decide(judgment)
        return plan.first if plan is not None and plan.steps else None

    def decide(self, judgment: Judgment, surprise: tuple | None = None) -> Plan | None:
        """The PLAN for one judgment, whoever sourced it — the deliberator's real question.

        Returns the plan as ROWS, because a step is a row and not a means: which lever it
        goes through is half of what it says, and execution writes that half to the ledger
        as `progression:through`. None where there is nothing to do, and that None is a decision.

        It takes the want itself, so an obligation reaches deliberation as what it is: a thing wanted,
        ranked in the same currency, pursued through an affordance like anything else. It is
        the widening the obligation record predicted — "the filter lifts when a member can
        pursue a judgment that is a diff rather than a distance".

        A obligation's means is not deduced here and could not be: it is the row OWED to that
        counterparty, which the market's own `honoured.rq` derives from the delivery chain.
        None where no lever answers — a debt to somebody my hardware cannot reach — and that
        None is the point. It used to be an exception thrown deep inside actuation; now it is
        a judgment that stays hot, stays owed, and shows up in the ledger unpaid, which is this
        project's posture towards everything it cannot prevent: leave evidence.
        """
        #  A ROOT IS NEVER HANDED TO THE SEARCH (#618): an `orexis:Desire` is law and
        #  premise, and what is decided is the want derived under it — minted the first time
        #  the root reads unmet, withdrawn once it reads met with nothing standing for it. A
        #  met root with nothing derived under it is nothing to pursue, and no pass runs.
        handed = pursuit.handed(self.agent, judgment)
        if handed is None:
            return None
        judgment = handed
        keeper = getattr(self.agent, "keeper", None)
        if (judgment.derived_from is not None and judgment.is_met
                and (keeper is None or not keeper.standing(want=judgment.uri))):
            pursuit.withdraw(self.agent, judgment.uri)
            return None
        #  NOTHING IS ANSWERED BY HARDCODE HERE ANY MORE, and the line that was is the whole
        #  of what this change existed to remove.
        #
        #  `if judgment.state in ("unmeasured", "stale"): return OBSERVE` stood at the top of
        #  this method — the last descendant of the reflex's `if value is None: return
        #  OBSERVE`, kept because nothing else could answer it. What made it removable was
        #  saying the want out loud: freshness is a shape (there exists a reading of this, and
        #  it was taken recently enough to be about now), Observe's effect predicts a reading
        #  stamped now, and the search finds that the shape holds in the world a look would
        #  make. Same first move, reached by the one road. The plan record set exactly this as
        #  its own acceptance test: a widening that leaves the special case beside it has not
        #  widened anything.
        #  WANTED IS NOT ACTIONABLE. A want nobody may act on yet is visible, rankable and left
        #  standing: a debt the holder has not presented, since a host that doses early spends
        #  the water where nothing is looking (#132). A stake is always pursuable — a plant does
        #  not ask — so this says nothing to it.
        if not judgment.pursuable:
            return None
        #  THE SEARCH, and there is nowhere else to go. Asking whether a lever points the
        #  right way is not the same as asking whether taking it leaves this agent better
        #  off, and only the second question refuses to water a plant that is already too
        #  wet — the direction test says Raises, the gap says below the aim, and both are
        #  true of a drowning plant whose aim sits above it. A debt is simulated exactly as a
        #  stake is (#255): the search sees the row owed to its counterparty AND this agent's
        #  own levers, so a host owing water it does not hold plans the refill — Acquire
        #  raises the level Apply's premise reads, and "refill, then serve" falls out of two
        #  rules that never mention each other.
        #
        #  None here is a DECISION and no longer a hand-off. Every case that used to fall
        #  through to the reflex is either refused at the gates or genuinely means "nothing
        #  I hold moves this", which is a true answer worth leaving in the trace.
        if plan := self._planned(judgment, surprise):
            return plan
        #  A ROW OWED TO SOMEONE THAT NAMES THIS WANT is taken without a search. The search
        #  speaks for a debt only when it FOUND a path — a vessel nobody has read binds no
        #  premise, and a premise that cannot bind proves nothing about serving — so anything
        #  short of a plan falls through to the pre-#255 road, unchanged: the row the market
        #  joined to this want, and the actuation boundary judges the vessel when it pours.
        #  Handed back as a one-row plan labelled OBLIGATION, which is not a search outcome and
        #  is not written to the trace. A stake has no such row, and nothing here asks what
        #  kind of want it is holding.
        for row in self.agent.afforder.offered():
            if not row.is_own and row.want == judgment.uri:
                #  Unsized: the host sizes the serve from the claim it holds.
                return Plan(OBLIGATION, ((Step.from_row(row)),))
        return None

    def _planned(self, judgment: Judgment, surprise: tuple | None = None) -> Plan | None:
        """The plan the search found for one judgment, or None — which is now always a DECISION.

        It used to hand back `(answered, move)`, because there were three answers and only two
        would fit in one: take this, take nothing, and *I cannot decide this by simulation*.
        The third is gone rather than collapsed into the second, and the difference is where it
        went. A lever with no stated effect and a want with no measure are refused by
        `orexis-validate` before a society is onboarded, so at runtime they are a world that
        should not have started; NOTHING — no lever this agent holds points at this want — is
        not a defect at all but a fern wanting a temperature it cannot move, which proposes
        nothing and says so in its trace.

        WHAT REPLACES THE DEFERRAL IS NOISE, not silence. Both refused conditions are still
        reachable by a world onboarded before the gate existed, or by one started past it, and
        an agent meeting either must say so loudly rather than decide quietly on half the
        evidence.
        """
        #  A STAKE NOTHING MEASURES is complained about by the package that holds the
        #  regions, once per want, the first time the planner asks it (sensing's
        #  `desire_urgency`) — the kernel used to ask the live world once here to say so,
        #  and could tell a stake from a debt only by kind.
        #  A PLAN THAT WORKED HERE BEFORE is adopted without a search (#469, #551): the same
        #  want, a world where the plan's regressed precondition holds and its first step is
        #  on the menu. The trace says so; the world verifies it step by step.
        from . import remembered, trace
        search = self._planners.get(judgment.uri)
        if search is None:
            search = self._planners[judgment.uri] = Planner(self.agent, self.me)
        kept = None
        if remembered.remembered_for(self.agent, judgment.uri):
            #  KEYED BY WHAT A READING IS (#576): a remembered plan's premises state readings
            #  by the bands the domain asserted, plain triples asked of the present.
            kept = remembered.applicable(self.agent, judgment.uri, self.agent.desires)
        if kept is not None:
            uri, steps, cost = kept
            plan = Plan(REMEMBERED, tuple(steps), judgment.urgency, None, cost=cost)
            trace.write(self.agent.beliefs, self.agent.id, judgment, plan, [], judgment.urgency, 0.0,
                        (trace.UNJUDGED, None), surprise=surprise)
            self._decided[judgment.uri] = (plan, uri)
            self.log.info("%s: remembered — %d step(s) whose precondition holds here",
                          _short(judgment.uri), len(steps))
            return plan
        plan = search.plan(judgment, surprise=surprise)
        self._decided[judgment.uri] = (plan, None)
        if plan.steps:
            self.log.info("%s: %s (urgency %.2f -> %.2f)",
                          _short(judgment.uri), plan.outcome, plan.urgency_now, plan.urgency_after)
            return plan
        #  A world reachable and not worth reaching, or no lever pointing at this want at all.
        #  THIS is the decision the reflex could not make, and returning None here is the whole
        #  point rather than a failure to answer — a met judgment quietly holding near its pick
        #  included, which is most passes and not worth a log line; the unmet ones still say
        #  why nothing was done.
        if plan.outcome != SATISFIED:
            self.log.info("%s: %s — no move improves on doing nothing",
                          _short(judgment.uri), plan.outcome)
        return None

# WHAT WENT WITH THE REFLEX, and what that costs: the dealer's shop query — the lot my
# downstream venue owes, if the property in hand is my own vessel's stock. It was the reflex's
# one clause past the region, and it pursued serveability: buy while the barrel holds less than
# the lot it has promised, even where the aim is already met. Nothing derives that as a DESIRE,
# so the search cannot pursue what it is never handed, and the clause was the only carrier.
#
# Inert in every shipped world, which is why deleting it moves nothing: `world/simulation`'s
# supplier aims at 3.0 L and offers a 2.0 L lot, so any stock below the lot is below the aim and
# the search buys for the ordinary reason. It bites only for an author who picks an aim BELOW
# the lot they promise — a dealer that would then sit content while unable to serve. Said out
# loud here rather than left implied: see a-plan-is-a-path-of-graph-diffs.md.

#  A obligation's fallback plan — the row owed to its counterparty when the search found no path.
#  Not one of the planner's outcomes and never in the trace; it labels a row handed to
#  execution so the ledger's prose says where the step came from.
OBLIGATION = "obligation"


def _short(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
