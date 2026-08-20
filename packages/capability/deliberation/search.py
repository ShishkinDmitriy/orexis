"""Plan by simulating: build the world each lever would make, and keep the one worth reaching.

The reflex asks whether a lever points the right way. This asks whether taking it would leave
the agent BETTER OFF, which is a different question and the one worth asking — a society floods
a plant while every module behaves as written, because "the direction matches" was never a claim
that the outcome improves anything.

The loop is short because the pieces existed before it. `agent.effects` runs a means' rule and
hands back what it would add and retract, so a possible world is `(beliefs − retracts) + adds`
and nothing is written. The goal is a shape, so "would this work" is a validation. The menu is a
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
from dataclasses import dataclass, field

import rdflib
from pyshacl import validate as shacl_validate
from rdflib import RDF, URIRef

from agent import effects
from agent.goal import Goal
from agent.ontology import SENSED_GRAPH, beliefs_graph
from agent.validate import conforms, graph_from

log = logging.getLogger("search")

#  Why a pass ended, and they are not interchangeable. The two failures in particular: NOTHING
#  proposed anything (equip me), against EXHAUSTED, where levers exist and no bounded sequence
#  of them lands inside the region (my doses are too coarse, or my region is too tight for them).
SATISFIED = "satisfied"      # a world where the goal is met
IMPROVED = "improved"        # not met, but nearer than doing nothing
NOTHING = "no candidate"     # no lever this agent holds points at this want
EXHAUSTED = "exhausted"      # levers exist; none reaches the goal within the depth allowed
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
    """One point in the search: a world, how it was reached, and what it is worth."""

    world: object
    taken: tuple = field(default_factory=tuple)   # the means applied to get here, in order
    urgency: float = 1.0


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

    def __init__(self, agent, desire, me):
        self.agent = agent
        self.desire = desire
        self.me = me

    # --- what a world is worth ---------------------------------------------------------------

    def _urgency_in(self, world, goal: Goal) -> float:
        """How bad this goal is, in the world given. Lower is better; 1.0 is the worst there is.

        The number is the REGION's own, asked of the same `Region.urgency` every consumer uses,
        so a plan is scored by the measure the agent already steers by. Counting violations
        instead would have been simpler and wrong in a way that matters: a dose that moves a
        fern from 0.30 to 0.44 leaves the same single violation it started with, so a planner
        scoring by count would refuse every dose too small to finish the job — and refuse the
        second one for the same reason, having never taken the first.
        """
        if goal.observed_property is None:      # a duty, or any want with no measure
            return 0.0 if self._met_in(world, goal) else 1.0
        region = self.desire.regions.get(goal.observed_property)
        value = self._value_in(world, goal)
        if region is None:
            return 1.0
        if value is None:
            return 1.0                          # not knowing is maximal, as it is everywhere
        return region.urgency(value)

    def _value_in(self, world, goal: Goal) -> float | None:
        """What this property reads in the world given — the predicted one, in a simulation."""
        sosa = _SOSA
        subject = rdflib.URIRef(self.me.acts_for) if self.me.acts_for else None
        for obs in world.subjects(sosa.observedProperty,
                                  rdflib.URIRef(goal.observed_property)):
            if subject is not None and (obs, sosa.hasFeatureOfInterest, subject) not in world:
                continue
            for value in world.objects(obs, sosa.hasSimpleResult):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

    def _met_in(self, world, goal: Goal) -> bool:
        """Whether the goal's OWN shape is satisfied in this world.

        Its own and no others, which is what makes a pass affordable. Measured on the bench:
        validating one goal's shape costs 0.083s, and validating everything the packages ship
        costs 1.73s — twenty times more, for an answer about rules no effect here can have
        broken. A depth-2 pass would have taken twenty-two seconds instead of under two.
        Legality is asked once, of the winner, in `_offer`.

        UNFOCUSED, and that is not a detail either: pySHACL answers qualified value shapes
        wrong under `focus_nodes` — measured both ways round — and every goal shape here is
        qualified. A candidate judged with a focus would be judged by the wrong answer, with
        nothing to show that it had been.
        """
        shape = self._shape_of(goal, world)
        if shape is None:
            #  A want with no shape to check — a duty, whose state is a fact in a ledger rather
            #  than a pattern over readings. Its own state says whether it stands.
            return goal.is_met
        _, results, _ = shacl_validate(world, shacl_graph=shape, inference="none", advanced=True)
        return not list(results.subjects(RDF.type, _SH.ValidationResult))

    def _shape_of(self, goal: Goal, world):
        """The goal's shape, with everything hanging off it, or None if it has none."""
        node = URIRef(goal.uri)
        if (node, RDF.type, _SH.NodeShape) not in world:
            return None
        return world.cbd(node)

    # --- the search --------------------------------------------------------------------------

    def plan(self, goal: Goal) -> Plan:
        """The best bounded sequence of levers for one goal, or the reason there is none."""
        base = self._beliefs()
        here = _Node(world=base, urgency=self._urgency_in(base, goal))
        if self._met_in(base, goal):
            return Plan(SATISFIED, (), here.urgency, here.urgency)

        best, saw_candidate = here, False
        self._skipped = False
        seen = {self._signature(base, goal)}
        frontier = [here]
        for _ in range(self.MAX_DEPTH):
            nxt = []
            for node in frontier:
                for row in self._candidates(node, goal):
                    saw_candidate = True
                    #  A world is identified by the means that reached it, in order. Comparing
                    #  graphs would be the thorough answer and an unaffordable one; comparing
                    #  the path is enough to stop +3 then −3 from being explored as though it
                    #  were somewhere new, which is all cycle detection is for here.
                    #  Steps are ROWS, not means: a plan is a path through the affordance
                    #  graph, and which lever a step goes through is half of what it says.
                    taken = node.taken + (row,)
                    world = self._world_after(node, row, goal)
                    if world is None:
                        continue
                    #  CYCLE DETECTION, and it compares WORLDS rather than means. The first
                    #  draft refused to apply the same means twice, which is not what a cycle
                    #  is: two doses in a row reach somewhere new, and forbidding them would
                    #  have made every dose too small to finish the job unplannable. What must
                    #  not be explored twice is a world already seen — +3 then −3 lands back
                    #  where it started, and expanding it again would spend the depth budget
                    #  going nowhere.
                    where = self._signature(world, goal)
                    if where in seen:
                        continue
                    seen.add(where)
                    step = _Node(world, taken, self._urgency_in(world, goal))
                    if step.urgency < best.urgency:
                        best = step
                    if self._met_in(world, goal):
                        return self._offer(Plan(SATISFIED, taken, here.urgency, step.urgency), goal)
                    #  A SENSING action ends a plan. Looking tells you what is true; it does
                    #  not make anything true, so a step chosen to follow it would be chosen
                    #  against a reading nobody has taken.
                    if effects.confirmed_by(self.agent.store, row.means) != _BY_OBSERVATION:
                        nxt.append(step)
            frontier = nxt
            if not frontier:
                break

        if not saw_candidate:
            return Plan(NOTHING, (), here.urgency, here.urgency, self._skipped)
        if best is here:
            return Plan(NOT_BETTER, (), here.urgency, here.urgency, self._skipped)
        if best.urgency >= here.urgency:
            return Plan(NOT_BETTER, (), here.urgency, best.urgency, self._skipped)
        return self._offer(
            Plan(EXHAUSTED if not self._met_in(best.world, goal) else SATISFIED,
                 best.taken, here.urgency, best.urgency), goal)

    def _offer(self, plan: Plan, goal: Goal) -> Plan:
        """A plan, once it has been checked for legality — and only the winner is checked.

        Validating every candidate against the whole rulebook was the obvious reading and costs
        twenty times what the goal check does: measured on the bench, 1.73s against 0.083s, so a
        pass at depth 2 would take twenty-two seconds instead of under two. The guarantee does
        not need it. What must be true is that the agent never COMMITS to reaching an
        illegitimate world, and the plan it commits to is one — so the expensive question is
        asked once, of the world it actually intends.
        """
        if not plan.steps:
            return plan
        ok, _ = conforms(self._world_of(plan, goal), focus=self.me.uri)
        if ok:
            return plan
        log.warning("the world this plan would reach is one the society refuses — not taken")
        return Plan(REFUSED, (), plan.urgency_now, plan.urgency_after)

    def _world_of(self, plan: Plan, goal: Goal):
        """The world the whole plan would reach — replayed, because only its steps were kept.

        Rebuilt rather than carried on the node: a `Plan` crosses a module boundary and out to
        the ask channel, and a graph riding along with it would be a possible world escaping
        into somewhere that keeps things.
        """
        world = self._beliefs()
        for step in plan.steps:
            world = effects.world_after(world, self.agent.store, step.means, **self._bind(goal))
        return world

    def _candidates(self, node, goal: Goal):
        """The levers worth simulating from here — the menu, re-run in the world reached.

        THE MENU IS THE PRECONDITION LANGUAGE, which is why chaining needs none of its own: a
        row whose premises cannot hold does not exist, so an effect that makes a missing row
        appear is the step before it. At depth 0 this is the ordinary menu; deeper, it is the
        menu of a world nobody is in yet.

        No `which violations do I repair` declaration is consulted. The record proposes one and
        it is an OPTIMISATION — a way to skip simulating a lever that obviously cannot help —
        and simulation is the authority either way. Trying a lever that turns out not to help
        costs one validation; trusting a declaration that turns out to be wrong costs a plant.
        """
        from .module import menu_of

        for row in menu_of(self.agent.store.query, self.me.uri):
            if not row.is_chosen:
                continue
            if goal.observed_property and row.observed_property != goal.observed_property:
                continue
            if effects.rule_for(self.agent.store, row.means) is None:
                #  A lever whose package never said what it does. It still works — the reflex
                #  can take it — but nothing can simulate it, and a planner that guessed would
                #  be inventing the consequence it is supposed to be checking. Remembered
                #  rather than merely skipped, because a conclusion drawn without it is a
                #  conclusion about part of the menu.
                self._skipped = True
                continue
            yield row

    def _world_after(self, node, row, goal: Goal):
        try:
            return effects.world_after(node.world, self.agent.store, row.means,
                                       **self._bind(goal))
        except Exception as exc:                 # a package's rule is not an agent's problem
            log.error("could not simulate %s: %s", row.means, exc)
            return None

    def _bind(self, goal: Goal | None) -> dict:
        """What a rule needs filled in to answer about THIS agent and THIS want."""
        prop = goal.observed_property if goal else None
        value = goal.value if goal else None
        return {
            "me": f"<{self.me.uri}>",
            "subject": f"<{self.me.acts_for}>" if self.me.acts_for else "<urn:nobody>",
            "property": f"<{prop}>" if prop else "<urn:nothing>",
            "beliefs": f"<{beliefs_graph(self.agent.id)}>",
            "sensed": f"<{SENSED_GRAPH}>",
            "value": value if value is not None else 0,
            "litres": self._dose(goal) if goal else 0.0,
        }

    def _signature(self, world, goal: Goal):
        """What makes this world different from another, for planning purposes.

        The value the goal is about, rounded — cheap, and enough. Graph isomorphism would be
        the thorough answer and is not affordable here; comparing the number the plan is trying
        to move catches the oscillation this exists to stop, and two worlds that agree on it
        are worth the same to a search that scores by urgency.
        """
        value = self._value_in(world, goal)
        return None if value is None else round(value, 6)

    def _dose(self, goal: Goal) -> float:
        """How much this act would pour — ASKED of the actuator, never computed here.

        `dose_for` is the sizing the actor would actually use: enough to reach the aim, capped
        by what the vessel holds. A planner that sized its own dose would simulate an act
        nobody was going to take, predict a world nobody would reach, and be wrong in the
        direction that looks like a device lying — the single-source argument #238 made for an
        effect's magnitude and #247 for its timing, arriving a third time at the quantity.

        The first draft invented 0.5 litres because the sizing was buried in `act_on`, and it
        manufactured a finding: every dose overshot zz's region and the planner reported a rig
        too coarse to settle. The rig is fine. The invented number was not.
        """
        actuation = self.agent.provider(_ACTUATION)
        if actuation is None or goal.observed_property is None or goal.value is None:
            return 0.0
        litres = actuation.dose_for(goal.observed_property, goal.value)
        #  NEVER NEGATIVE, and this is the guard that matters most in the whole file. Sizing a
        #  dose is `(aim - value) * conversion`, so a property ABOVE its aim asks for a
        #  negative pour — and the effect rule, asked politely, predicts exactly what a
        #  negative dose would do: it reports the plant arriving neatly back at its aim. The
        #  planner then proposes watering a drowning plant, with a simulation agreeing.
        #
        #  The actor has always refused this (`litres <= EPS`), and the refusal has to live on
        #  both sides: a planner that simulates an act the actor would decline is not planning.
        #  Clamped to zero rather than skipped, because a zero dose predicts the value it
        #  started from, and a world no better than the one you are in is refused by the
        #  satisficing test one line later — the answer arrives by the same road as every
        #  other "this does not help".
        return float(litres) if litres and litres > 0 else 0.0

    def _beliefs(self):
        return graph_from(self.agent.store, *self.agent.store.public_graphs(),
                          beliefs_graph(self.agent.id), SENSED_GRAPH)


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")
_BY_OBSERVATION = "http://example.org/agora#ByObservation"
_ACTUATION = "http://example.org/agora/actuation#Actuation"
