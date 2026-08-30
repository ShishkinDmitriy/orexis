"""Plan by simulating: build the world each lever would make, and keep the one worth reaching.

The reflex asks whether a lever points the right way. This asks whether taking it would leave
the agent BETTER OFF, which is a different question and the one worth asking — a society floods
a plant while every module behaves as written, because "the direction matches" was never a claim
that the outcome improves anything.

The loop is short because the pieces existed before it. `effects` runs a means' rule and
hands back what it would add and retract, so a possible world is `(beliefs − retracts) + adds`
and nothing is written. The desire is a shape, so "would this work" is a validation. The menu is a
query, so "would this lever even exist afterwards" is the same query run against the simulated
world — which is the whole of chaining, with no precondition language of its own.

See knowledge/decisions/a-plan-is-a-path-of-graph-diffs.md. Four things there are constraints
rather than refinements, and each is here because a question found the failure it prevents:

- CYCLE DETECTION. +3 then −3 returns to the world you started in, and a search that does not
  notice spends its whole depth budget going nowhere.
- DEPTH EXHAUSTION IS AN ANSWER. "No bounded plan reaches this" and "no lever repairs this" are
  different findings — one says equip me, the other says my doses are too coarse — and a
  planner that reports them alike sends somebody to buy a fan when the problem is dose size.
- SATISFICE. Prefer the world with the lowest urgency, and act only if it beats doing nothing.
- A SENSING ACTION ENDS A PLAN. A world with no violations means "nothing I can foresee is
  wrong", not "the world will be fine": what to do after looking depends on what the look
  returns, so "look, then water" is a plan whose second step was chosen against a value nobody
  has seen.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import rdflib
from pyshacl import validate as shacl_validate
from rdflib import RDF, URIRef

from . import effects, signature, trace
from orexis_progression_patience.act import Act, Step
from orexis_deliberation_search.desire import Desire
from .afforder import wants_of
from .imaginarium import Imaginarium
from orexis_progression_patience.ontology import (DESIRE_ASSERTED_GRAPH, DESIRE_DERIVED_GRAPH,
                            STATE_GRAPH, beliefs_graph)
from orexis_deliberation_search.conformance import conforms, graph_from

log = logging.getLogger("search")

#  Why a pass ended, and they are not interchangeable. The two failures in particular: NOTHING
#  proposed anything (equip me), against EXHAUSTED, where levers exist and no bounded sequence
#  of them lands inside the region (my doses are too coarse, or my region is too tight for them).
SATISFIED = "satisfied"      # a world where the desire is met
IMPROVED = "improved"        # not met, but nearer than doing nothing
NOTHING = "no candidate"     # no lever this agent holds points at this want
EXHAUSTED = "exhausted"      # levers exist; none reaches the desire within the depth allowed
NOT_BETTER = "not better"    # every world reachable is as bad as this one, or worse
REFUSED = "refused"          # the world it would reach is one the society would not accept


@dataclass(frozen=True)
class Plan:
    """What the search found: the steps, why it stopped, and what it would cost to be wrong.

    A plan with no steps is an ANSWER — `outcome` says which of the four silences it is, and the
    difference is the whole reason this returns a record rather than a means or None.
    """

    outcome: str
    steps: tuple = ()                 # of `act.Step`: an act each, with what it would reach
    urgency_now: float | None = None
    urgency_after: float | None = None
    #  Whether some lever was passed over for want of a stated effect. A search that could not
    #  see every row must never report "nothing helps" as a finding: it did not look at
    #  everything, and the lever it could not simulate may be the one that works. Caught by
    #  fern, which buys its water — Acquire has no effect rule, so the search saw only Observe,
    #  correctly found that looking does not wet soil, and would have concluded that nothing
    #  does. The plant would have stopped buying.
    partial: bool = False

    @property
    def first(self) -> str | None:
        """The one move to commit. A plan is re-derived every pass, so only its head is acted
        on: the world moves, and a committed tail is a promise about a future nobody can see."""
        return self.steps[0].action if self.steps else None


@dataclass
class _Node:
    """One point in the search: a world, how it was reached, and what it is worth.

    The world is held TWICE, and the pair is what makes depth 2 mean what it says. `graph` names
    this node's readings inside the plan's imaginarium, which is what the next step's rule reads
    and where its `$state` points; `world` is the same readings flattened over public knowledge
    into the one rdflib graph pySHACL and `_value_in` want. Two engines want different shapes of
    the same fact, and materialising the second from the first is the piece of work the design
    does not remove — see the seams in
    knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.
    """

    world: object
    graph: str = STATE_GRAPH                     # this node's readings, in the imaginarium
    taken: tuple = field(default_factory=tuple)   # the STEPS taken to get here, in order
    urgency: float = 1.0
    #  The net diff against the base world, in canonical facts — where this node IS, for cycle
    #  detection. The root stands nowhere but the world itself, so its diff is empty.
    diff: tuple = signature.EMPTY


class Planner:
    """Bounded search over the levers an agent holds, scored by simulation.

    Held by the module rather than free-standing because every question it asks — what do I
    want, what could I do, what would that do — is asked of the agent's own providers, and the
    answers are its own.
    """

    #  Depth 2 is what the record argues for and what the one real customer needs. It is a
    #  constant here rather than a belief because it is not a preference: it is the ceiling on
    #  how much compute a pass may spend, and an agent that could revise it could spend an
    #  afternoon planning while its plant died.
    MAX_DEPTH = 2

    def __init__(self, agent, me):
        self.agent = agent
        self.me = me
        #  Alive only during a pass. Between passes there is no imaginarium, which is the point:
        #  a hypothesis explored against a world that has moved is not a hypothesis, so the
        #  snapshot is per plan and nothing carries over.
        self.imaginarium = None

    # --- what a world is worth ---------------------------------------------------------------

    def _urgency_in(self, world, graph: str, desire: Desire) -> float:
        """How bad this desire is, in the world given. Lower is better; 1.0 is the worst there is.

        A CAPABILITY'S ANSWER, never this file's arithmetic: the choir is asked
        (`Agent.desire_urgency`) with the imaginarium as the world and `$state`-equivalent
        `graph` naming this node's readings — the same question every other consumer asks
        against the belief base, answered by the same module from the same declaration, so a
        plan is scored by the measure the agent already steers by. That is what declaring
        it bought: the reflex used to steer for the AIM while this scored distance from the
        region's CENTRE, so the two mechanisms pursued different targets whenever the pick sat
        off-centre, silently. The imaginarium is passed rather than the flat rdflib copy,
        because sensing runs its measure on pyoxigraph against live beliefs and one stored
        query answered by two engines is the disagreement this repo already closed once —
        the module's own hook docstring carries the argument.

        Counting violations instead would have been simpler and wrong in a way that matters: a
        dose that moves a fern from 0.30 to 0.44 leaves the same single violation it started
        with, so a planner scoring by count would refuse every dose too small to finish the job
        — and refuse the second one for the same reason, having never taken the first.

        `world` (the flat copy) stays a parameter for the wants that state no measure: an obligation
        is met-or-not over the record, and anything else unmeasured scores 1.0, the not-knowing
        answer.
        """
        answer = self.agent.desire_urgency(desire, self.imaginarium.query, graph)
        if answer is not None:
            return answer
        if desire.is_obligation:                        # met-or-not over the record
            return 0.0 if self._met_in(world, desire) else 1.0
        #  A want whose kind nothing loaded answers for, scoring the defined fallback:
        #  maximal, because not knowing how bad IS how bad. It used to serve the freshness
        #  want too — epistemic wants had no declared measure, so every candidate world
        #  scored 1.0 and no look could be preferred to standing still. Sensing declares one
        #  now, so what is left here is a want in a society composed without whoever measures
        #  it, which `orexis-validate` refuses for a stake and cannot for anything else.
        return 1.0

    #  `_value_in` and `_value_of` WERE HERE — the planner reading a property's value out of a
    #  candidate world by walking sosa. Nothing here reads a value now: an effect rule reads
    #  where the property stands from `$state` itself, and an actor sizing a step asks
    #  sensing at the node's graph (`Module.size(query, graph, property)`).

    def _met_in(self, world, desire: Desire, graph: str | None = None) -> bool:
        """Whether the desire's OWN shape is satisfied in this world.

        Its own and no others, which is what makes a pass affordable. Measured on the bench:
        validating one desire's shape costs 0.083s, and validating everything the packages ship
        costs 1.73s — twenty times more, for an answer about rules no effect here can have
        broken. A depth-2 pass would have taken twenty-two seconds instead of under two.
        Legality is asked once, of the winner, in `_offer`.

        UNFOCUSED, and that is not a detail either: pySHACL answers qualified value shapes
        wrong under `focus_nodes` — measured both ways round — and every desire shape here is
        qualified. A candidate judged with a focus would be judged by the wrong answer, with
        nothing to show that it had been.
        """
        shape = self._shape_of(desire, world)
        if shape is None:
            #  A obligation's goal state is a PATTERN over the record, not a distance (#255): this
            #  claim discharged, in whatever world is being judged — which is what lets a
            #  possible world where Apply ran count as satisfying, and the world in hand not.
            if desire.is_obligation:
                return (URIRef(desire.uri), _AG.dischargedAt, None) in world
            #  A want with no shape and no property — a CALL (#359) — is met exactly where
            #  whoever measures it says it is: zero urgency in the world being judged. Asked
            #  of the imaginarium at the node's graph, as `_urgency_in` asks.
            if graph is not None:
                answer = self.agent.desire_urgency(desire, self.imaginarium.query, graph)
                if answer is not None:
                    return answer <= 0.0
            return desire.is_met
        _, results, _ = shacl_validate(world, shacl_graph=shape, inference="none", advanced=True)
        return not list(results.subjects(RDF.type, _SH.ValidationResult))

    def _shape_of(self, desire: Desire, world):
        """The desire's shape, with everything hanging off it, or None if it has none.

        Asked of the DESIRE MODALITY, not of the world being judged (#298): what is pursued
        and what is are different stores now, and validation was always two graphs — the
        world is the data, the shape is the question. `world` stays a parameter because the
        met-check is about it, and the shapes snapshot is per pass (`_begin`), so a rebuild
        mid-search cannot hand two depths two different wants.
        """
        node = URIRef(desire.uri)
        #  The met-test hangs OFF the desire node since the reification — a desire is a node
        #  carrying its shape, not the shape itself — so the walk is one hop of `ag:metWhen`.
        #  A node that IS a shape stays legal: an asserted root desire is a bare NodeShape a
        #  world's TriG may state, and it never grew a desire node around it.
        met = self._shapes.value(node, _AG.metWhen)
        if met is not None and (met, RDF.type, _SH.NodeShape) in self._shapes:
            return self._shapes.cbd(met)
        if (node, RDF.type, _SH.NodeShape) not in self._shapes:
            return None
        return self._shapes.cbd(node)

    # --- the search --------------------------------------------------------------------------

    def plan(self, desire: Desire) -> Plan:
        """The best bounded sequence of levers for one desire, or the reason there is none.

        Every candidate weighed is remembered as it is weighed, and the pass is written down
        when it ends (#256) — otherwise all of this dies in-process as a single log line, and
        nothing outside can reconstruct it, because the belief base is locked by the process
        holding it. `trace` explains why that is the record's one sanctioned exception.

        THE IMAGINARIUM IS DISCARDED WHOLE when the pass ends, which is the property that makes
        a possible world safe to materialise at all: an intention must survive a restart and a
        hypothesis must survive nothing, and these are opposites on the axis that matters. In a
        `finally`, so it holds for the pass that raises as well as the one that answers — and no
        node's graph has a lifecycle of its own, because there is nothing left to have one in.
        """
        try:
            return self._search(desire)
        finally:
            self.imaginarium = None

    def _search(self, desire: Desire) -> Plan:
        """The pass itself. Separate only so `plan` can guarantee the discard above."""
        #  Timed from HERE, which is inside the pass and outside the trace write below: a
        #  caller timing `plan()` would be timing the recording as well, and reporting the
        #  observer's cost as the observed's.
        self._started = time.monotonic()
        here = self._begin(desire)
        base = here.world
        #  CLEARED AT THE START, which is the difference between a graph that holds one pass
        #  and one that holds two. It also means a pass that raises leaves no trace claiming
        #  to describe a decision nobody reached.
        trace.clear(self.agent.beliefs, self.agent.id, desire.uri)
        #  MET NO LONGER ENDS THE PASS — a-desire-states-its-own-measure removed the root
        #  short-circuit that returned SATISFIED without searching whenever the shape held.
        #  The shape governs the outcome LABEL; the measure governs whether a step is worth
        #  taking, and since the measure is anchored at the AIM a met desire may still carry
        #  urgency: inside the region and off the pick is a true situation. Only a desire
        #  whose measure reads zero has nothing a step could improve, so only that one skips
        #  the search — which also keeps the per-tick cost of a calm society what it was.
        met_now = self._met_in(base, desire, STATE_GRAPH)
        if met_now and here.urgency <= 0.0:
            return self._record(desire, Plan(SATISFIED, (), here.urgency, here.urgency),
                                here.urgency)

        best, saw_candidate = here, False
        self._skipped = False
        self._weighed = []
        seen = {here.diff}
        frontier = [here]
        for depth in range(self.MAX_DEPTH):
            nxt = []
            for node in frontier:
                for row in self._candidates(node, desire):
                    saw_candidate = True
                    #  Steps are ROWS, not means: a plan is a path through the affordance
                    #  graph, and which lever a step goes through is half of what it says.
                    step = self._step_from(node, row, desire)
                    if step is None:
                        self._weighed.append((depth, row, None, trace.UNSIMULATED))
                        continue
                    #  CYCLE DETECTION, and it compares WORLDS rather than action. The first
                    #  draft refused to apply the same means twice, which is not what a cycle
                    #  is: two doses in a row reach somewhere new, and forbidding them would
                    #  have made every dose too small to finish the job unplannable. What must
                    #  not be explored twice is a world already seen — +3 then −3 lands back
                    #  where it started, and expanding it again would spend the depth budget
                    #  going nowhere.
                    #
                    #  KEYED ON THE WORLD AND NEVER ON THE GRAPH NAME, which is the one thing
                    #  naming a graph per node could quietly have broken. `seen` is global
                    #  across the search, so two paths arriving at the same world collide and
                    #  the second is pruned — two names, one world, still one entry.
                    where = step.diff
                    novel = where not in seen
                    if novel:
                        seen.add(where)
                        if step.urgency < best.urgency:
                            best = step
                    #  MET IS ASKED BEFORE THE PRUNE, and only for a want that is not met
                    #  ALREADY. Cycle detection is about EXPANSION — do not spend the depth
                    #  budget on a world you have stood in — and a step that repairs the want
                    #  is not a place to expand from, it is the answer. Pruning it first
                    #  answered a question nobody asked.
                    #
                    #  It matters because of what the signature deliberately leaves out. An
                    #  observation canonicalises to its upsert key and its VALUE, never its
                    #  `sosa:resultTime`, so a look nets to nothing and the world it reaches
                    #  carries its parent's signature — which is exactly right for "look, then
                    #  water" and exactly wrong for a want whose whole content is that
                    #  something was read RECENTLY. The one lever that repairs freshness was
                    #  being discarded as somewhere already reached before anything asked
                    #  whether it repaired anything. The record that built the signature named
                    #  this as the day the question comes back; it came back from the other
                    #  side, and the fix is here rather than in the canonical form, because
                    #  putting the timestamp in would make every look a new world and "look,
                    #  then look, then look" a three-step plan.
                    #
                    #  `met_now` guards it, and the guard is not caution: with the want
                    #  already met, a look leaves it met, so without this every calm agent
                    #  would answer "look" on every tick — a step that changes nothing
                    #  reported as achieving something. Met and still urgent is steering
                    #  toward the pick, and steering is what `best` below is for.
                    if (novel or not met_now) and self._met_in(step.world, desire, step.graph):
                        self._weighed.append((depth, row, step.urgency, trace.MET))
                        return self._record(
                            desire,
                            self._offer(Plan(SATISFIED, step.taken, here.urgency, step.urgency),
                                        desire, step.world),
                            here.urgency)
                    if not novel:
                        self._weighed.append((depth, row, step.urgency, trace.SEEN))
                        continue
                    self._weighed.append(
                        (depth, row, step.urgency,
                         trace.BETTER if step.urgency < here.urgency else trace.WORSE))
                    #  EVERY step that survived the cycle check extends the frontier, and a
                    #  SENSING action still ends a plan — by the same road every other "this
                    #  does not help" arrives by, rather than by a rule of its own.
                    #
                    #  There WAS a rule of its own, and it is the reason depth was 1. It asked
                    #  `ag:confirmedBy ag:ByObservation`, which every effect here answers — a
                    #  dose and a bid included, since only a later reading says either arrived
                    #  — so the guard matched every lever, `nxt` came back empty at every
                    #  depth, and the search never took a second step whatever MAX_DEPTH said.
                    #  Replacing it with a truer term was the first fix and the wrong one: what
                    #  a look does is already stated by its EFFECT, which predicts the value it
                    #  found, so the world it reaches has the parent's signature and `seen`
                    #  discards it. Measured with no guard at all, on three worlds including a
                    #  first look with nothing sensed: Observe is pruned as a world already
                    #  reached, every time. A second statement of a fact the effect settles is
                    #  a fact that can disagree with it.
                    #
                    #  WHAT THIS RESTS ON, so the next person can see it break: the signature
                    #  is the world's net diff in CANONICAL facts (#258), and in canonical form
                    #  a look nets to nothing — an observation is its upsert key and its value,
                    #  never its `sosa:resultTime`, so predicting the value you already hold is
                    #  standing still, and a first look's valueless reading states no fact at
                    #  all. The day a fresher timestamp counts as somewhere new, "look, then
                    #  look" becomes a new world every time; chaining past a look becomes a
                    #  real question again exactly there, and nowhere earlier. See
                    #  `signature.py`.
                    nxt.append(step)
            frontier = nxt
            if not frontier:
                break

        #  A pass that ends with no step worth taking is labelled by the SHAPE, not by the
        #  search: a met desire that weighed its levers and found none worth pulling is
        #  SATISFIED — it is met, and near the pick every dose sizes to nothing, which is the
        #  deadband satisficing gives for free — where an unmet one in the same position is
        #  NOT_BETTER (my doses are too coarse) or NOTHING (equip me), and those must not blur.
        if not saw_candidate:
            return self._record(desire, Plan(SATISFIED if met_now else NOTHING,
                                           (), here.urgency, here.urgency,
                                           self._skipped), here.urgency)
        if best is here or best.urgency >= here.urgency:
            after = here.urgency if best is here else best.urgency
            return self._record(desire, Plan(SATISFIED if met_now else NOT_BETTER,
                                           (), here.urgency, after,
                                           self._skipped), here.urgency)
        return self._record(desire, self._offer(
            Plan(EXHAUSTED if not self._met_in(best.world, desire, best.graph) else SATISFIED,
                 best.taken, here.urgency, best.urgency), desire, best.world), here.urgency)

    def _record(self, desire, plan, stands_at):
        """Write the pass down and hand back the plan unchanged.

        Threaded through the returns rather than wrapped around `plan()` so that the EARLY ones
        are recorded too — a desire already satisfied and a desire nothing points at are the two
        answers a reader most wants and the two a wrapper would have missed. The same threading
        is why the clock is read here: every return passes through, so no exit is untimed.
        """
        trace.write(self.agent.beliefs, self.agent.id, desire, plan,
                    getattr(self, "_weighed", []), stands_at,
                    time.monotonic() - self._started)
        return plan

    def _offer(self, plan: Plan, desire: Desire, world) -> Plan:
        """A plan, once it has been checked for legality — and only the winner is checked.

        Validating every candidate against the whole rulebook was the obvious reading and costs
        twenty times what the desire check does: measured on the bench, 1.73s against 0.083s, so a
        pass at depth 2 would take twenty-two seconds instead of under two. The guarantee does
        not need it. What must be true is that the agent never COMMITS to reaching an
        illegitimate world, and the plan it commits to is one — so the expensive question is
        asked once, of the world it actually intends.

        **The world is PASSED, and it used to be replayed.** `_world_of` rebuilt it by re-running
        each step's rule from the root, which is the same defect the search loop had and in the
        same place: a rule re-run has to be re-run against something, and that something was the
        store — so past step one the society's refusal was judged on a world the plan would not
        reach. The node that won already holds the world it would reach, so nothing has to be
        rebuilt at all. It arrives as an ARGUMENT rather than on the `Plan`, which is the
        distinction the old docstring was really drawing: a `Plan` crosses a module boundary and
        goes out to the ask channel, and a possible world must not ride along into somewhere
        that keeps things.
        """
        if not plan.steps:
            return plan
        ok, _ = conforms(world, focus=self.me.uri)
        if ok:
            return plan
        log.warning("the world this plan would reach is one the society refuses — not taken")
        return Plan(REFUSED, (), plan.urgency_now, plan.urgency_after)

    def _candidates(self, node, desire: Desire):
        """The levers worth simulating from here — the menu, re-run in the world reached.

        THE MENU IS THE PRECONDITION LANGUAGE, which is why chaining needs none of its own: a
        row whose premises cannot hold does not exist, so an effect that makes a missing row
        appear is the step before it. At depth 0 this is the ordinary menu; deeper, it is the
        menu of a world nobody is in yet.

        Asked of the NODE's world since #359, because a premise may now be something an
        earlier step made true: Offering reads the stock a refill would leave, and reads the
        round an Offer in this very plan would have opened. Before that every row was a
        conclusion from wiring alone and the agent's store answered for every depth.

        No `which violations do I repair` declaration is consulted. The record proposes one and
        it is an OPTIMISATION — a way to skip simulating a lever that obviously cannot help —
        and simulation is the authority either way. Trying a lever that turns out not to help
        costs one validation; trusting a declaration that turns out to be wrong costs a plant.
        """
        from .afforder import affordances_of

        #  ASKED OF THE IMAGINARIUM, at the node's own graph (#359): a premise may be a fact
        #  an earlier step made true — Offering needs stock, Acquiring's effect raises it, and
        #  "acquire, then offer" is a plan only if the menu of the world after the first step
        #  shows the second. The root node's graph is the agent's own readings, so at depth 0
        #  this is the ordinary menu, exactly as before.
        for row in affordances_of(self.imaginarium.query, self.me.uri, self.agent.desires.query_union,
                           beliefs_graph(self.agent.id), node.graph):
            if desire.is_obligation:
                #  A obligation may be served by its counterparty's honoured row, or approached
                #  through this agent's own levers — refilling the vessel is an Acquire on its
                #  own stake, and that is the whole of why an obligation is in the search (#255).
                if not (row.is_own or row.for_agent == desire.owed_to):
                    continue
            else:
                if not row.is_own:
                    continue
                #  A row that names a want serves that want. A want ABOUT NOTHING — a call —
                #  ranges over every row of the agent's own, because what would raise the
                #  stock a round needs is a row the stake names (the dealer's two-step).
                if (row.want is not None and row.want != desire.uri
                        and desire.uri in self._about_of):
                    continue
            if effects.rule_for(self.agent.beliefs, row.action) is None:
                #  A lever whose package never said what it does. It still works — the reflex
                #  can take it — but nothing can simulate it, and a planner that guessed would
                #  be inventing the consequence it is supposed to be checking. Remembered
                #  rather than merely skipped, because a conclusion drawn without it is a
                #  conclusion about part of the menu.
                self._skipped = True
                continue
            yield row

    def _begin(self, desire: Desire) -> _Node:
        """This plan's imaginarium, and the root node standing in the world the agent is in.

        The imaginarium is built per PLAN and dropped with it — see `plan`, which does that in a
        `finally` so a pass that raises leaves nothing imagined behind either. What it holds is
        public knowledge, this agent's beliefs and this agent's readings, all copied: the
        readings are the root node's own graph, which is why `$state` at depth 0 still names
        exactly what it always did, and every deeper node forks from it.
        """
        self.imaginarium = Imaginarium(
            self.agent.beliefs,
            #  EVERY GRAPH THIS AGENT OWNS, asked rather than named (#444): its picks, its
            #  debts, and whatever a package records — sensing's instruments among them, and
            #  the kernel does not know that name. It used to spell three of them here and
            #  ask for the rest in the same call.
            #
            #  THE INSTRUMENTS matter and are the reason the asking has to be complete: a want
            #  may be about the reading rather than about
            #  the number in it, and the horizon that decides whether a reading is still
            #  evidence is written here and nowhere else. Without it the freshness measure
            #  found no horizon in any candidate world and answered maximal for all of
            #  them, so no look could ever look better than standing still — the silent
            #  empty-result failure this file's own docstring warns about, arriving through
            #  a graph nobody had copied. Read-only like everything else copied in: no
            #  effect touches it, and a plan cannot re-command a cadence.
            *self.agent.beliefs.recorded_graphs())
        #  What this agent PURSUES, snapshotted for the pass: the desire modality's triples as
        #  one rdflib graph, because pySHACL wants rdflib and a cbd walks blank nodes. Small —
        #  a few hundred triples — and per pass for the same reason the imaginarium is.
        #  The WANT graphs alone — derived and asserted — never the record projections: the
        #  flat world below already carries the pick record through the belief flatten, and a
        #  second copy with fresh blank nodes splits every aim in two, which AimShape rightly
        #  refuses as not steering.
        self._shapes = effects.applied((), self.agent.desires.construct(
            f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ "
            f"VALUES ?g {{ <{DESIRE_DERIVED_GRAPH}> <{DESIRE_ASSERTED_GRAPH}> }} "
            f"GRAPH ?g {{ ?s ?p ?o }} }}"), ())
        base = self._beliefs()
        #  The wants ride in the flat world too, exactly as they did when the constraint graph
        #  was public: `_offer`'s legality check validates the world the plan would reach, and
        #  the capability shapes demand the regions — a world without them is refused for a
        #  reason no lever caused (#312).
        for triple in self._shapes:
            base.add(triple)
        #  The base's canonical facts, once per pass: `advance` needs them to tell a fact
        #  restored from a fact introduced, which is what lets a path that returns to the base
        #  world return to the EMPTY diff instead of accumulating noise. Read as the store's
        #  own quads — the same graphs `_beliefs` flattens — because the signature works in
        #  pyoxigraph terms and the rdflib copy exists only for pySHACL.
        store = self.agent.beliefs
        #  Which beliefs are UPSERTED, and by what — declared by the package that writes them
        #  (`ag:keyedBy`, `ag:carries` on the node's class), read once per pass so the signature
        #  canonicalises a reading without this file knowing what one looks like.
        self._about_of = wants_of(self.agent.desires.query_union, self.me.uri)
        self._keys = signature.keys_of(store.query)
        self._base_facts = signature.facts((
            quad for iri in [*store.public_graphs(), *store.recorded_graphs()]
            for quad in store.quads(iri)), self._keys)
        return _Node(world=base, graph=STATE_GRAPH,
                     urgency=self._urgency_in(base, STATE_GRAPH, desire))

    def _step_from(self, node, row, desire: Desire):
        """The node one step on from here, or None where the rule would not run.

        The diff is computed ONCE and lands in both halves of what a node is: the imaginarium
        graph the next step's rule will read, and the flat rdflib world validation reads. Asked
        of the IMAGINARIUM and not of the belief base, which is the whole of #254 — a retraction
        asked of the store finds the observation still on disk, so the second dose lands beside
        the first instead of replacing it and is then discarded as a world already seen.
        """
        bind = self._bind(desire, node, row)
        try:
            added, retracted = effects.apply(self.imaginarium, row.action, **bind)
        except Exception as exc:                 # a package's rule is not an agent's problem
            log.error("could not simulate %s: %s", row.action, exc)
            return None
        world = effects.applied(node.world, added, retracted)
        #  THE ROW BECOMES AN ACT here, where it is sized — the quantity the taker answered is
        #  what the rule just simulated — and the act becomes a STEP once the world it reaches
        #  is scored. An act carries no window yet: nothing in a search knows when.
        act = Act.from_row(row, quantity=bind["litres"] or None)
        path = node.taken + (Step(act),)
        diff = signature.advance(node.diff, signature.facts(added, self._keys),
                                 signature.facts(retracted, self._keys), self._base_facts)
        graph = self.imaginarium.reached(node.graph, path, added, retracted)
        urgency = self._urgency_in(world, graph, desire)
        taken = node.taken + (Step(act, urgency_after=urgency),)
        return _Node(world=world, graph=graph, taken=taken, urgency=urgency, diff=diff)

    def _bind(self, desire: Desire | None, node=None, row=None) -> dict:
        """What a rule needs filled in to answer about THIS agent and THIS want, HERE.

        `node` is where the step is being taken FROM, and passing it is what makes depth 2
        more than a number. It carries BOTH halves of that, and the second is #254: the value
        the rule predicts from, read out of the node's flat world, and `$state` — the graph in
        the imaginarium holding the readings this node's path reached, which is what the
        retraction half of the rule asks about. Bound to the agent's own sensed graph, as it was
        before, the retraction found the observation still on disk and predicted a reading that
        landed BESIDE the previous step's instead of replacing it.

        Bound from the desire alone — which is how this was first written —
        every step is predicted from the reading the agent actually holds, so a second dose
        computes `0.04 + 0.21/conversion` exactly as the first did, lands on the world the
        first one reached, and is discarded by cycle detection as somewhere already seen.
        The loop iterated twice and the search was depth 1, silently, for every means that
        moves a measured property. Measured before it was fixed: value 0.04 at depth 0, the
        world at 0.18 after one step, and `_bind` still saying 0.04.

        The DOSE moves with it for the same reason and by the same road: `dose_for` sizes an
        act from where the property stands, so a second dose asked about the world the first
        one reached is the act the actor would actually take next — which is the whole of what
        makes "too small to finish in one" a plannable situation rather than an unreachable one.
        """
        graph = node.graph if node is not None else STATE_GRAPH
        return {
            "me": f"<{self.me.uri}>",
            "claim": f'"{desire.claim}"' if desire and desire.claim else '"urn:nobody"',
            "subject": f"<{self.me.acts_for}>" if self.me.acts_for else "<urn:nobody>",
            #  THE WANT AND WHAT IT IS ABOUT, carried from the row to the rule and never read
            #  here: `$about` is whatever the want's deriver said (`ag:about`) — a property,
            #  for a region want — and the rule joins on it in its own words.
            "want": f"<{desire.uri}>" if desire else "<urn:nothing>",
            "about": f"<{row.about}>" if row is not None and row.about else "<urn:nothing>",
            "beliefs": f"<{beliefs_graph(self.agent.id)}>",
            "state": f"<{graph}>",
            "litres": self._dose(row, graph) if desire and row is not None else 0.0,
        }

    def _dose(self, row, graph: str) -> float:
        """How much this act would move — ASKED OF WHOEVER WOULD TAKE IT, never computed here.

        Each lever's owner sizes its own act, and the two owners size differently: an actuator
        pours what closes the deficit capped by what its vessel holds, a bidder asks for what
        closes the deficit capped by what its WALLET can pay for. A planner that computed either
        for itself would simulate an act nobody was going to take, predict a world nobody would
        reach, and be wrong in the direction that looks like a device lying — the single-source
        argument #238 made for an effect's magnitude and #247 for its timing.

        ASKED OF THE TAKER, found the way execution finds it — the action's `ag:takenBy` family
        — and asked ABOUT A WORLD: the imaginarium at this node's graph, so a second dose is
        sized from where the first one left the property (#254). The taker reads the value
        there through sensing; nothing here knows what a reading looks like.

        Zero for a means nobody sizes. A zero dose predicts the value it started from, and a
        world no better than the one you are in is refused by the satisficing test one line
        later — so an unsized lever arrives at "this does not help" by the same road as every
        other, rather than by an exception.
        """
        if row is None or row.about is None:
            return 0.0
        from orexis_progression_patience.execution import taken_by

        family = taken_by(self.agent.beliefs.query, row.action)
        litres = None
        for actor in (self.agent.providers(family) if family else []):
            litres = actor.size(self.imaginarium.query, graph, row)
            if litres is not None:
                break
        #  NEVER NEGATIVE, and this is the guard that matters most in the whole file. Sizing is
        #  `(aim - value) * conversion`, so a property ABOVE its aim asks for a negative pour —
        #  and the effect rule, asked politely, predicts exactly what a negative dose would do:
        #  it reports the plant arriving neatly back at its aim. The planner then proposes
        #  watering a drowning plant, with a simulation agreeing.
        #
        #  The actor has always refused this (`litres <= EPS`), and the refusal has to live on
        #  both sides: a planner that simulates an act the actor would decline is not planning.
        return float(litres) if litres and litres > 0 else 0.0

    def _beliefs(self):
        #  Everything this agent owns, asked (#444). The instruments are why completeness
        #  matters: a freshness want's met-test reads the horizon this agent published, and a
        #  shape whose pattern reaches a graph nobody copied does not fail — it finds nothing,
        #  reports nothing, and the want reads as met for ever. The debts are why it must
        #  include the received ones (#255): an obligation's met-test is a pattern over the record,
        #  and the world Apply's effect discharges an obligation in must hold it to discharge.
        return graph_from(self.agent.beliefs, *self.agent.beliefs.public_graphs(),
                          *self.agent.beliefs.recorded_graphs())


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_AG = rdflib.Namespace("http://example.org/orexis#")
#  No means or family is named here any more: sizing is `Module.size`, asked of the row's
#  taker through `ag:takenBy` exactly as execution finds it.
