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
(`ag:deliberatesBy`) that an agent's review can move inside whatever room its mandate leaves,
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

from . import planner, trace
from .act import Act, Step
from modality.desire import Desire
from .afforder import affordances_of
from .module import Module
from modality.ontology import AG, DELIBERATION_GRAPH, STATE_GRAPH, beliefs_graph
from .planner import Planner
from modality.store import bindings

# What this package asks OF others, by family — their namespaces, never their Python.

# The moves. The intention package's individuals, referenced by IRI: a move IS what the keeper
# records when the actor carries it out, so naming anything else would put a translation table
# between deciding and remembering.
# The means are the kernel's words (the-mind-is-six-graphs): a move IS what the keeper
# records, and four packages name these, which is what makes them lingua franca.

#  WHAT IS NOT HERE ANY MORE: the rung order, the direction terms and the venue join that read
#  them. Preferring the cheaper rung and matching a lever's stated direction against the gap's
#  sign were the reflex's whole apparatus, and simulation answers both without being told —
#  the rung a plan takes is the one whose predicted world scores best, and a lever pointing the
#  wrong way reaches a world no better than standing still. `market:direction` itself stays: the
#  keeper's verification arc reads it to know which way a dose should move a reading, and its
#  retirement rides with repair-matching rather than with this deletion.

#  The line above is also this file's whole remaining relationship with `market:`. It used to
#  spell four of that package's IRIs — two directions, a venue join and a hosting belief — and
#  spells none now, which is the ratchet #334 asks for arriving as a consequence rather than as
#  a rule anybody had to keep.


class Deliberator(Module):
    """The decider. Speaks to no topic; its callers are its siblings, through the agent."""

    name = "deliberation"
    def pursued(self) -> list[tuple[Desire, str | None]]:
        """Every desire this agent holds, with the move I propose for it — or None.

        Here because deciding what can be done is exactly what a deliberator is, and because
        the kernel may not name a capability's family: `agent.pursuing()` merges what the modules
        want, and this is the only place that can say whether anything answers.
        """
        return [(desire, self.propose_for(desire)) for desire in self.agent.pursuing()]

    def start(self) -> None:
        """Drop whatever the last process was thinking.

        A trace describes a pass over a world, and the world moved while this agent was not
        running. Keeping one across a restart would leave the graph holding a decision about
        readings nobody has taken since — the same hazard as a trace outliving its pass, one
        lifecycle up. Cheap: the graph holds one pass per desire and most agents hold a handful.
        """
        self.agent.beliefs.clear_graph(DELIBERATION_GRAPH)

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
        #  cannot name every want: freshness is per instrument, an obligation is per counterparty, and
        #  a panel keyed on `property` could only ever draw stakes. Urgency is unit-free by
        #  construction, so a moisture, a look overdue and a litre owed belong on one axis —
        #  that is the whole claim of a common currency, and this is where it becomes visible.
        #
        #  A OBLIGATION is tagged by whom it is owed to and never by its claim. A jti is unique per
        #  round, so tagging by it would mint a new series every time the society traded and
        #  make the store's cardinality grow with its history — the cost of a dashboard nobody
        #  could then load. Whom I owe is a handful of agents and says the thing worth seeing.
        for desire, _ in pursued:
            about = (desire.owed_to.rsplit("#", 1)[-1] if desire.is_obligation
                     else desire.uri.rsplit("#", 1)[-1])
            #  `agent_want` and its tag KEEP THE RETIRED WORD, deliberately. The noun "want"
            #  gave way to "desire" everywhere else when the vocabulary was ruled on
            #  (domain/desire.md), and a measurement name is the one place the rename costs more
            #  than it buys: it is an external surface with history behind it, so renaming
            #  splits every series at the cutover and leaves a dashboard reading half of one.
            #  The word is wrong and the continuity is worth more.
            rows.append(("agent_want", {"want": f"obligation.{about}" if desire.is_obligation else about},
                         {"urgency": float(desire.urgency)}))

        #  HOW IT DECIDED, not just what it wants (#256). `pursued()` above has just re-planned
        #  every desire, so the trace holds this tick's verdicts — read from there rather than
        #  counted here, so the figure a dashboard shows and the answer `orexis-ask` gives are
        #  one fact. Six fields because a planner has six answers where returning a move or
        #  None had two, and the pair worth watching is `no candidate` against `exhausted`:
        #  one says equip me, the other says my doses are too coarse.
        verdicts = trace.outcomes(self.agent.beliefs.query_union)
        rows.append(("agent_deliberation", {}, {
            outcome.replace(" ", "_"): float(verdicts.get(outcome, 0))
            for outcome in (planner.SATISFIED, planner.IMPROVED, planner.NOTHING,
                            planner.EXHAUSTED, planner.NOT_BETTER, planner.REFUSED)}))
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
        rows.append(("agent_planning", {}, trace.effort(self.agent.beliefs.query_union)))
        return rows

    #  `propose_about(property)` and `desire_about(property)` WERE HERE — the actors' door by
    #  property, and the rule that an unmet epistemic want answers before the stake. Which
    #  wants a property carries is sensing's to say, so the door is sensing's `want_about`
    #  now and the rule went with it (the-stake-is-sensings-want); what an actor hands the
    #  kernel is the want's node, through `execution.pursue_for`.

    def propose_for(self, desire: Desire) -> str | None:
        """The MEANS of the move for one desire, or None — `decide` projected to its head.

        Kept for every caller that wants only the kind of act; execution wants the row and
        asks `decide`. Silencing a deliberator means silencing both.
        """
        plan = self.decide(desire)
        return plan.first if plan is not None and plan.steps else None

    def decide(self, desire: Desire) -> planner.Plan | None:
        """The PLAN for one desire, whoever sourced it — the deliberator's real question.

        Returns the plan as ROWS, because a step is a row and not a means: which lever it
        goes through is half of what it says, and execution writes that half to the ledger
        as `ag:through`. None where there is nothing to do, and that None is a decision.

        It takes the want itself, so an obligation reaches deliberation as what it is: a thing wanted,
        ranked in the same currency, pursued through an affordance like anything else. It is
        the widening the obligation record predicted — "the filter lifts when a member can
        pursue a desire that is a diff rather than a distance".

        A obligation's means is not deduced here and could not be: it is the row OWED to that
        counterparty, which the market's own `honoured.rq` derives from the delivery chain.
        None where no lever answers — a debt to somebody my hardware cannot reach — and that
        None is the point. It used to be an exception thrown deep inside actuation; now it is
        a desire that stays hot, stays owed, and shows up in the ledger unpaid, which is this
        project's posture towards everything it cannot prevent: leave evidence.
        """
        #  NOTHING IS ANSWERED BY HARDCODE HERE ANY MORE, and the line that was is the whole
        #  of what this change existed to remove.
        #
        #  `if desire.state in ("unmeasured", "stale"): return OBSERVE` stood at the top of
        #  this method — the last descendant of the reflex's `if value is None: return
        #  OBSERVE`, kept because nothing else could answer it. What made it removable was
        #  saying the want out loud: freshness is a shape (there exists a reading of this, and
        #  it was taken recently enough to be about now), Observe's effect predicts a reading
        #  stamped now, and the search finds that the shape holds in the world a look would
        #  make. Same first move, reached by the one road. The plan record set exactly this as
        #  its own acceptance test: a widening that leaves the special case beside it has not
        #  widened anything.
        if not desire.is_obligation:
            #  THE SEARCH, and there is nowhere else to go. Asking whether a lever points the
            #  right way is not the same as asking whether taking it leaves this agent better
            #  off, and only the second question refuses to water a plant that is already too
            #  wet — the direction test says Raises, the gap says below the aim, and both are
            #  true of a drowning plant whose aim sits above it.
            #
            #  None here is a DECISION and no longer a hand-off. Every case that used to fall
            #  through to the reflex is either refused at the gates or genuinely means "nothing
            #  I hold moves this", which is a true answer worth leaving in the trace.
            return self._planned(desire)
        #  Nobody has asked. The holder is waiting for its own watch to be live, and a host
        #  that doses early spends the water where nothing is looking (#132) — so a standing
        #  debt is visible, rankable, and still not actionable until it is presented.
        if not desire.pursuable:
            return None
        #  SIMULATE FIRST, exactly as a stake does (#255): the search sees the honoured row
        #  AND this agent's own levers, so a host owing water it does not hold plans the
        #  refill — Acquire raises the level Apply's premise reads, and "refill, then serve"
        #  falls out of two rules that never mention each other. A search that answered and
        #  found no move is the evidence the issue demands: the obligation stays hot, stays owed,
        #  and is not pursued into a world where serving discharges nothing.
        if plan := self._planned(desire):
            return plan
        #  The search speaks for an obligation only when it FOUND a path — a vessel nobody has read
        #  binds no premise, and a premise that cannot bind proves nothing about serving. So
        #  anything short of a plan falls through to the pre-#255 road, unchanged: the
        #  honoured row for this counterparty, and the actuation boundary judges the vessel
        #  when it pours. Handed back as a one-row plan labelled OBLIGATION, which is not a
        #  search outcome and is not written to the trace: it is the row the obligation names.
        for row in affordances_of(self.agent.beliefs.query, self.me.uri, self.agent.desires.query_union,
                           beliefs_graph(self.agent.id)):
            if row.for_agent == desire.owed_to:
                #  A obligation's row, unsized: the host sizes the serve from the claim it holds.
                return planner.Plan(OBLIGATION, (Step(Act.from_row(row)),))
        return None

    def _planned(self, desire: Desire) -> planner.Plan | None:
        """The plan the search found for one desire, or None — which is now always a DECISION.

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
        #  ASKED OF THE LIVE WORLD ONCE, purely to complain. The planner asks the same
        #  question of every candidate and takes the flat 1.0 when nobody answers — which
        #  makes every possible world score alike, so "no move improves" comes back with
        #  confidence from an unrankable comparison. An EPISTEMIC want is the freshness case
        #  and legitimately unmeasured (it has no distance to scale); any other want about a
        #  property is a stake, and a stake nothing measures is what the gate refuses. Told
        #  apart by the kernel's own structure — the kernel holds no region to consult.
        if (not desire.is_obligation and not desire.is_epistemic
                and self.agent.desire_urgency(
                    desire, self.agent.beliefs.query, STATE_GRAPH) is None):
            self.log.error(
                "%s: I hold a stake here and nothing I composed can measure it — every world "
                "I could reach scores alike, so I am about to conclude that nothing helps from "
                "a comparison that means nothing. `orexis-validate` refuses this world.",
                _short(desire.uri))
        plan = Planner(self.agent, self.me).plan(desire)
        #  A SEARCH OVER PART OF THE MENU CANNOT SAY "NOTHING HELPS", and it no longer has
        #  anywhere to hand the question to. Some lever had no stated effect and was passed
        #  over, so the one that works may be the one nobody simulated — fern buys its water,
        #  and a search blind to Acquire would find that looking does not wet soil and stop
        #  the plant buying. The gate exists to make this unreachable; if it is reached, the
        #  agent acts on what it could see and the log says what it could not.
        if plan.partial:
            self.log.error(
                "%s: a lever on my menu states no effect, so I weighed part of my options and "
                "am answering as if that were all of them. `orexis-validate` refuses this "
                "world.", _short(desire.uri))
        if plan.steps:
            self.log.info("%s: %s (urgency %.2f -> %.2f)",
                          _short(desire.uri), plan.outcome, plan.urgency_now, plan.urgency_after)
            return plan
        #  A world reachable and not worth reaching, or no lever pointing at this want at all.
        #  THIS is the decision the reflex could not make, and returning None here is the whole
        #  point rather than a failure to answer — a met desire quietly holding near its pick
        #  included, which is most passes and not worth a log line; the unmet ones still say
        #  why nothing was done.
        if plan.outcome != planner.SATISFIED:
            self.log.info("%s: %s — no move improves on doing nothing",
                          _short(desire.uri), plan.outcome)
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

#  `plan.rq` and `plan_for` WERE HERE — the dealer's two-step as a hand-written exposition,
#  "acquire upstream, then offer downstream", kept as a narrative for a reader after the reflex
#  went. The search FINDS that plan now (a-round-is-a-fact-and-offering-is-an-action): a call on
#  a dry vessel with an upstream round open plans exactly those two rows from two action nodes
#  that never mention each other, and the trace shows it. A narrative beside a search that
#  produces the same thing is a second statement that can disagree — and it was the kernel's
#  last reason to spell the market's `Offer`.

#  A obligation's fallback plan — the row owed to its counterparty when the search found no path.
#  Not one of the planner's outcomes and never in the trace; it labels a row handed to
#  execution so the ledger's prose says where the step came from.
OBLIGATION = "obligation"


def _short(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
