"""Plan by simulating: build the world each lever would make, and keep the one worth reaching.

The reflex asks whether a lever points the right way. This asks whether taking it would leave
the agent BETTER OFF, which is a different question and the one worth asking — a society floods
a plant while every module behaves as written, because "the direction matches" was never a claim
that the outcome improves anything.

The loop is short because the pieces existed before it. `agent.effects` runs a means' rule and
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
from .desire import Desire
from .imaginarium import Imaginarium
from .ontology import (DESIRE_ASSERTED_GRAPH, DESIRE_DERIVED_GRAPH,
                            INSTRUMENTS_GRAPH, SENSED_GRAPH, beliefs_graph,
                            obligations_graph)
from .validate import conforms, graph_from

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
    steps: tuple = ()
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
        return self.steps[0].means if self.steps else None


@dataclass
class _Node:
    """One point in the search: a world, how it was reached, and what it is worth.

    The world is held TWICE, and the pair is what makes depth 2 mean what it says. `graph` names
    this node's readings inside the plan's imaginarium, which is what the next step's rule reads
    and where its `$sensed` points; `world` is the same readings flattened over public knowledge
    into the one rdflib graph pySHACL and `_value_in` want. Two engines want different shapes of
    the same fact, and materialising the second from the first is the piece of work the design
    does not remove — see the seams in
    knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.
    """

    world: object
    graph: str = SENSED_GRAPH                     # this node's readings, in the imaginarium
    taken: tuple = field(default_factory=tuple)   # the means applied to get here, in order
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

    def __init__(self, agent, deducer, me):
        self.agent = agent
        #  The DESIRE CAPABILITY's provider, named for what it does rather than for what it
        #  produces — `self.desire` collided with the Desire objects this class ranges over the
        #  moment the noun was ruled on, which is the ambiguity the ruling exists to remove.
        self.deducer = deducer
        self.me = me
        #  Alive only during a pass. Between passes there is no imaginarium, which is the point:
        #  a hypothesis explored against a world that has moved is not a hypothesis, so the
        #  snapshot is per plan and nothing carries over.
        self.imaginarium = None

    # --- what a world is worth ---------------------------------------------------------------

    def _urgency_in(self, world, graph: str, desire: Desire) -> float:
        """How bad this desire is, in the world given. Lower is better; 1.0 is the worst there is.

        A CAPABILITY'S ANSWER, never this file's arithmetic: the choir is asked
        (`Agent.desire_urgency`) with the imaginarium as the world and `$sensed`-equivalent
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

        `world` (the flat copy) stays a parameter for the wants that state no measure: a duty
        is met-or-not over the record, and anything else unmeasured scores 1.0, the not-knowing
        answer.
        """
        answer = self.agent.desire_urgency(desire, self.imaginarium.query, graph)
        if answer is not None:
            return answer
        if desire.observed_property is None:      # a duty: met-or-not over the record
            return 0.0 if self._met_in(world, desire) else 1.0
        #  A want whose kind nothing loaded answers for, scoring the defined fallback:
        #  maximal, because not knowing how bad IS how bad. It used to serve the freshness
        #  want too — epistemic wants had no declared measure, so every candidate world
        #  scored 1.0 and no look could be preferred to standing still. Sensing declares one
        #  now, so what is left here is a want in a society composed without whoever measures
        #  it, which `orexis-validate` refuses for a stake and cannot for anything else.
        return 1.0

    def _value_in(self, world, desire: Desire) -> float | None:
        """What this desire's property reads in the world given."""
        if desire.observed_property is None:
            return None
        return self._value_of(world, desire.observed_property)

    def _value_of(self, world, observed_property: str) -> float | None:
        """What one property reads in the world given — the predicted one, in a simulation."""
        sosa = _SOSA
        subject = rdflib.URIRef(self.me.acts_for) if self.me.acts_for else None
        for obs in world.subjects(sosa.observedProperty,
                                  rdflib.URIRef(observed_property)):
            if subject is not None and (obs, sosa.hasFeatureOfInterest, subject) not in world:
                continue
            for value in world.objects(obs, sosa.hasSimpleResult):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

    def _met_in(self, world, desire: Desire) -> bool:
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
            #  A duty's goal state is a PATTERN over the record, not a distance (#255): this
            #  claim discharged, in whatever world is being judged — which is what lets a
            #  possible world where Apply ran count as satisfying, and the world in hand not.
            if desire.is_duty:
                return (URIRef(desire.uri), _AG.dischargedAt, None) in world
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
        met_now = self._met_in(base, desire)
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
                    #  CYCLE DETECTION, and it compares WORLDS rather than means. The first
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
                    if (novel or not met_now) and self._met_in(step.world, desire):
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
            Plan(EXHAUSTED if not self._met_in(best.world, desire) else SATISFIED,
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

        Asked of the agent's store rather than of the node's, and that is not the defect #254
        closed arriving a third time: no shipped effect moves anything a row's premises walk —
        a reading is not a premise, and the one own-graph premise there is, an open round
        (#358), is written by the wire and not by any effect. The day an effect opens a round
        (Offering, #359) this takes the imaginarium too, and "acquire after offer" becomes a
        two-step a search can see.

        No `which violations do I repair` declaration is consulted. The record proposes one and
        it is an OPTIMISATION — a way to skip simulating a lever that obviously cannot help —
        and simulation is the authority either way. Trying a lever that turns out not to help
        costs one validation; trusting a declaration that turns out to be wrong costs a plant.
        """
        from .menu import menu_of

        for row in menu_of(self.agent.beliefs.query, self.me.uri, self.agent.desires.query_union,
                           beliefs_graph(self.agent.id)):
            if desire.is_duty:
                #  A duty may be served by its counterparty's honoured row, or approached
                #  through this agent's own levers — refilling the vessel is an Acquire on its
                #  own stake, and that is the whole of why a duty is in the search (#255).
                if not (row.is_own or row.for_agent == desire.owed_to):
                    continue
            else:
                if not row.is_own:
                    continue
                if desire.observed_property and row.observed_property != desire.observed_property:
                    continue
            if effects.rule_for(self.agent.beliefs, row.means) is None:
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
        readings are the root node's own graph, which is why `$sensed` at depth 0 still names
        exactly what it always did, and every deeper node forks from it.
        """
        self.imaginarium = Imaginarium(
            self.agent.beliefs, beliefs_graph(self.agent.id), SENSED_GRAPH,
            #  THE INSTRUMENTS, because a want may be about the reading rather than about
            #  the number in it, and the horizon that decides whether a reading is still
            #  evidence is written here and nowhere else. Without it the freshness measure
            #  found no horizon in any candidate world and answered maximal for all of
            #  them, so no look could ever look better than standing still — the silent
            #  empty-result failure this file's own docstring warns about, arriving through
            #  a graph nobody had copied. Read-only like everything else copied in: no
            #  effect touches it, and a plan cannot re-command a cadence.
            INSTRUMENTS_GRAPH,
            obligations_graph(self.agent.id))
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
        self._base_facts = signature.facts(
            quad for iri in [*store.public_graphs(), beliefs_graph(self.agent.id),
                             SENSED_GRAPH, INSTRUMENTS_GRAPH]
            for quad in store.quads(iri))
        return _Node(world=base, graph=SENSED_GRAPH,
                     urgency=self._urgency_in(base, SENSED_GRAPH, desire))

    def _step_from(self, node, row, desire: Desire):
        """The node one step on from here, or None where the rule would not run.

        The diff is computed ONCE and lands in both halves of what a node is: the imaginarium
        graph the next step's rule will read, and the flat rdflib world validation reads. Asked
        of the IMAGINARIUM and not of the belief base, which is the whole of #254 — a retraction
        asked of the store finds the observation still on disk, so the second dose lands beside
        the first instead of replacing it and is then discarded as a world already seen.
        """
        try:
            added, retracted = effects.apply(self.imaginarium, row.means,
                                             **self._bind(desire, node, row))
        except Exception as exc:                 # a package's rule is not an agent's problem
            log.error("could not simulate %s: %s", row.means, exc)
            return None
        taken = node.taken + (row,)
        world = effects.applied(node.world, added, retracted)
        #  Where this node stands, advanced by the same diff that built the world above. The
        #  step's triples go in as they arrived — pyoxigraph terms, no conversion.
        diff = signature.advance(node.diff, signature.facts(added),
                                 signature.facts(retracted), self._base_facts)
        #  The graph BEFORE the urgency, because the urgency is the measure asked of it: the
        #  candidate's readings must exist in the imaginarium for `$sensed` to name them.
        graph = self.imaginarium.reached(node.graph, taken, added, retracted)
        return _Node(world=world, graph=graph, taken=taken,
                     urgency=self._urgency_in(world, graph, desire), diff=diff)

    def _bind(self, desire: Desire | None, node=None, row=None) -> dict:
        """What a rule needs filled in to answer about THIS agent and THIS want, HERE.

        `node` is where the step is being taken FROM, and passing it is what makes depth 2
        more than a number. It carries BOTH halves of that, and the second is #254: the value
        the rule predicts from, read out of the node's flat world, and `$sensed` — the graph in
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
        means = row.means if row is not None else None
        prop = desire.observed_property if desire else None
        value = desire.value if desire else None
        if prop is None and desire is not None and desire.is_duty and row is not None:
            #  A duty names no property, but the LEVER does (#255): the refill is an Acquire
            #  on this agent's own stake, and its rule binds the row's property and predicts
            #  from where that property stands in the node's world.
            prop = row.observed_property
        if node is not None and prop is not None:
            here = self._value_of(node.world, prop)
            if here is not None:
                value = here
        return {
            "me": f"<{self.me.uri}>",
            #  A duty's rules read the record: WHICH claim, and WHERE the debts are kept —
            #  the one graph name built from the one id the rules allow building from.
            "claim": f'"{desire.claim}"' if desire and desire.claim else '"urn:nobody"',
            "owed": f"<{obligations_graph(self.agent.id)}>",
            "subject": f"<{self.me.acts_for}>" if self.me.acts_for else "<urn:nobody>",
            "property": f"<{prop}>" if prop else "<urn:nothing>",
            "beliefs": f"<{beliefs_graph(self.agent.id)}>",
            "sensed": f"<{node.graph if node is not None else SENSED_GRAPH}>",
            "value": value if value is not None else 0,
            "litres": self._dose(desire, value, means, prop) if desire else 0.0,
        }

    def _dose(self, desire: Desire, value: float | None = None,
              means: str | None = None, observed_property: str | None = None) -> float:
        """How much this act would move — ASKED OF WHOEVER WOULD TAKE IT, never computed here.

        Each lever's owner sizes its own act, and the two owners size differently: an actuator
        pours what closes the deficit capped by what its vessel holds, a bidder asks for what
        closes the deficit capped by what its WALLET can pay for. A planner that computed either
        for itself would simulate an act nobody was going to take, predict a world nobody would
        reach, and be wrong in the direction that looks like a device lying — the single-source
        argument #238 made for an effect's magnitude and #247 for its timing.

        DISPATCHED ON THE MEANS, and getting that wrong is what #268 was underneath. Asking the
        actuator about everything returned 0.0 for every Acquire, because a plant that BUYS its
        water holds no actuator — so the effect rule predicted a world identical to the one the
        agent was in, and the search concluded that buying does not help. That is worse than the
        blindness it replaced: a partial plan defers to the reflex, but a plan that confidently
        finds nothing better STOPS the agent bidding.

        Zero for a means nobody sizes. A zero dose predicts the value it started from, and a
        world no better than the one you are in is refused by the satisficing test one line
        later — so an unsized lever arrives at "this does not help" by the same road as every
        other, rather than by an exception.
        """
        value = desire.value if value is None else value
        observed_property = observed_property or desire.observed_property
        if observed_property is None or value is None:
            return 0.0
        if means == _ACQUIRE:
            bidding = self.agent.provider(_BIDDING)
            litres = (bidding.qty_for(observed_property, value)
                      if bidding is not None else None)
        elif means == _ACTUATE:
            actuation = self.agent.provider(_ACTUATION)
            litres = (actuation.dose_for(observed_property, value)
                      if actuation is not None else None)
        else:
            return 0.0
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
        return graph_from(self.agent.beliefs, *self.agent.beliefs.public_graphs(),
                          beliefs_graph(self.agent.id), SENSED_GRAPH,
                          #  The instruments, for the same reason `validate_agent` flattens
                          #  them: the freshness want's met-test reads the horizon this agent
                          #  published, and a shape whose pattern reaches a graph nobody
                          #  copied does not fail — it finds nothing, reports nothing, and
                          #  the want reads as met for ever.
                          INSTRUMENTS_GRAPH,
                          #  The debts too (#255): a duty's met-test is a pattern over the
                          #  record, and the world Apply's effect discharges an obligation in
                          #  must hold the obligation to discharge.
                          obligations_graph(self.agent.id))


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")
_AG = rdflib.Namespace("http://example.org/orexis#")
_ACTUATION = "http://example.org/orexis/actuation#Actuation"
#  Sizing is asked of whichever module OWNS the lever, so the means and the family that carries
#  it are both named here. Spelled out rather than imported: `intention/terms.py` and
#  `market/terms.py` hold the same strings, and a package may not import another's Python.
_ACTUATE = "http://example.org/orexis#Actuate"
_ACQUIRE = "http://example.org/orexis#Acquire"
_BIDDING = "http://example.org/orexis/market#Bidding"
