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

import hashlib

import pyoxigraph as ox

from functools import partial

from datetime import datetime, timedelta, timezone

import logging
import time
from dataclasses import dataclass, field, replace

import rdflib
from rdflib import RDF, URIRef

from . import effects, relevance, signature, trace
from .beliefs import Picks
from orexis_agent_progression.act import Step
from orexis_agent_deliberation.want import Want


from .affordances import Affordances
from . import imaginarium
from .imaginarium import Imaginarium
from orexis_agent_progression import violation
from orexis_agent_progression.store import NAMESPACES, Raw, bind, bindings
from .ontology import DELIBERATION
from orexis_agent_progression.ontology import DELIBERATION_GRAPH, GRAPH_PREFIX, OREXIS, PROGRESSION, STATE_GRAPH
from orexis_agent_deliberation.conformance import graph_from, held_shapes, legality_selects
from orexis_agent_deliberation.judge import crossed_text
from orexis_agent_progression import clock
from .cone import _Compiled, _Node
from .plan import (EXHAUSTED, IMPROVED, NOTHING, NOT_BETTER, Plan, REFUSED,
                   REMEMBERED, SATISFIED)
from .trace import SURPRISE_EXOGENOUS, SURPRISE_WITHHELD
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import DESIRE, KNOWN, PREDICTION, RECORD, STATE, WANT

log = logging.getLogger("search")


@dataclass(frozen=True)
class _Remembered:
    """A remembered plan as a ROW of the menu (#469, second form): what the trace names it
    by, and what the walk below fills. `via` is its first step's lever, so a reader joining
    `progression:through` still lands on a real lever; its own node is what would be taken."""

    action: str                 # the remembered plan's node
    via: str
    want: str
    steps: tuple
    about: str | None = None
    direction: str | None = None
    for_agent: str | None = None
    is_own: bool = True


#  WHERE A PASS SAYS WHAT IT KNOWS about the worlds it made — in the imaginarium, beside them,
#  and gone when the pass is. Named once here because this is what creates it.
PASS_GRAPH = GRAPH_PREFIX + "pass"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
XSD = "http://www.w3.org/2001/XMLSchema#"


def _signature_of(node) -> str:
    """What makes two worlds the same world, as a name: the canonical facts this world differs
    by, sorted and hashed. The facts ARE the world; this is only its name, and a query asking
    whether a fork lands somewhere already seen compares names."""
    adds, retracts = node.diff
    text = "|".join(sorted(str(f) for f in adds)) + "!" + "|".join(sorted(str(f) for f in retracts))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def write_plan(engine, want: str, plan) -> str | None:
    """Write down what a pass found, and hand back the plan's node — or None where it found
    no steps, which is a pass that decided nothing and has nothing to record.

    THE PLANNER DECIDES A PLAN, SO THE PLANNER WRITES IT, as `derive_wants` writes the wants
    it decides. What a plan IS — its steps, their order, how long it comes to — is settled
    here; where it is kept is the deliberation graph, which is cleared at boot because a plan
    about a world that has moved is stale.

    ITS STEPS ARE THE LEDGER'S OWN WORDS. `progression:Step`, `progression:fills`,
    `progression:through`, chained by `progression:by` and `progression:then` — exactly the
    shape `keeper.adopt` writes and `keeper.standing` reads. That is the point: a plan crossing
    from deliberation to progression is then triples rather than a `tuple[Step]` handed over in
    Python, and a sovereign asking what was decided reads it with one query. Read DOWNWARD, as
    a layer may.

    ONE PLAN PER WANT, named for it and replaced whole, so a second pass over the same want
    leaves one plan and never two — the same rule a want's own graph follows.

    `takes` is the number the search computes and nothing else can recover: an action's
    `orexis:landsAfter` is a SPARQL expression about the world the act is taken in, so the
    summed landing of a path exists only inside the pass that walked it. It was discarded
    here, which is why a plan could not be placed from its deadline.
    """
    if not plan.steps:
        return None
    node = f"{want}.plan"
    steps = [f"{node}.{n}" for n in range(len(plan.steps))]
    blocks = [f'  <{node}> a deliberation:Plan ; deliberation:forWant <{want}> ;\n'
              f'      deliberation:verdict "{plan.outcome}" ;\n'
              + (f'      deliberation:takes {plan.landing:.6f} ;\n' if plan.landing is not None else "")
              + f'      <{PROGRESSION}by> <{steps[0]}> .']
    for n, (uri, step) in enumerate(zip(steps, plan.steps)):
        facts = [f'a <{PROGRESSION}Step>', f'<{PROGRESSION}fills> <{step.action}>']
        if step.via:
            facts.append(f'<{PROGRESSION}through> <{step.via}>')
        if step.about:
            facts.append(f'<{OREXIS}about> <{step.about}>')
        if step.quantity is not None:
            facts.append(f'<{PROGRESSION}quantity> {step.quantity}')
        if n + 1 < len(steps):
            facts.append(f'<{PROGRESSION}then> <{steps[n + 1]}>')
        blocks.append(f'  <{uri}> ' + " ; ".join(facts) + " .")
    engine.update(f"""
DELETE {{ GRAPH <{DELIBERATION_GRAPH}> {{ <{node}> ?p ?o . ?s <{PROGRESSION}then> ?t . ?s ?sp ?so }} }}
WHERE  {{ GRAPH <{DELIBERATION_GRAPH}> {{ <{node}> ?p ?o .
          OPTIONAL {{ <{node}> <{PROGRESSION}by>/<{PROGRESSION}then>* ?s . ?s ?sp ?so
                      OPTIONAL {{ ?s <{PROGRESSION}then> ?t }} }} }} }} ;
INSERT DATA {{ GRAPH <{DELIBERATION_GRAPH}> {{
{chr(10).join(blocks)} }} }}""", prefixes=NAMESPACES)
    return node


class Planner:
    """Bounded search over the levers an agent holds, scored by simulation.

    Held by the module rather than free-standing because every question it asks — what do I
    want, what could I do, what would that do — is asked of the agent's own providers, and the
    answers are its own.
    """

    #  THE CEILING ON WHAT A PASS MAY SPEND, in the unit it spends: worlds forked in the
    #  imaginarium (#494). It WAS a depth, 2, a constant here and not a belief, on the argument
    #  that a ceiling on compute is not a preference an agent may revise — and that argument
    #  still holds, so the agent still may not move it. What changed is the unit. Under a
    #  breadth-first search depth WAS the ceiling on compute; best-first (#492) it bounds only
    #  how far ahead a plan reaches, which nothing needs, since a plan is re-derived every pass
    #  and only its head is acted on. A world costs what its mutable slice makes it, measured
    #  in the runbook, so a sovereign can state this in seconds' worth of worlds for the world
    #  it actually has. Where a sovereign states none, this is the ceiling: sized for a plant,
    #  whose pass forks a handful, and enough to solve two disks (14) but not three (50).
    BUDGET = 32

    def __init__(self, agent, me):
        self.agent = agent
        self.me = me
        #  THE PASS'S CLOCK, read once at the root of each pass and never inside the search
        #  (#588). Here so a caller asking a planner for a rule's bindings before any pass has
        #  a clock to be answered with.
        self._clock = clock.now()
        #  The sovereign's pick, read the way every pick is — from the desire modality's copy,
        #  since the search is what reads a belief and nothing beneath it does — or the engine's
        #  own ceiling where the agent's beliefs say nothing. Optional on purpose, unlike the
        #  patience: `orexis:BudgetShape` bounds a stated one and demands none.
        picks = self.agent.desires.read_optional(PLANNING_PICKS)
        self.budget = picks.budget_worlds if picks is not None else self.BUDGET
        #  Alive only during a pass. Between passes there is no imaginarium, which is the point:
        #  a hypothesis explored against a world that has moved is not a hypothesis, so the
        #  snapshot is per plan and nothing carries over.
        self.reset()                     # no cone yet (#553)

    # --- what a world is worth ---------------------------------------------------------------

    def _urgency_in(self, node, judgment: Want) -> float:
        """How bad this judgment is, in the world given. Lower is better; 1.0 is the worst there is.

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

        The NODE is what arrives, and its graph is the whole of what a measure needs: the flat
        rdflib copy this took alongside was only ever read by the wants that state no measure —
        an obligation, once met-or-not over the record — and those ask the imaginarium now too (#481).
        Anything else unmeasured scores 1.0, the not-knowing answer.
        """
        answer = self.agent.desire_urgency(
            judgment, partial(self.imaginarium.query,
                                graphs=self._dataset(self._at(node), self._judged_at(node, judgment))),
            self._judged_at(node, judgment))
        if answer is not None:
            return answer
        #  An avoided-pattern want is binary by its own contract — met 0, unmet 1 — and the
        #  kernel judges it (#468): no capability answers for pure ratified data, and the
        #  flat not-knowing fallback below would send the search shopping for a want that
        #  wants nothing whenever the pattern is held.
        pattern = self._avoided_pattern(judgment)
        if pattern is not None:
            return 1.0 if self._pattern_binds(pattern, self._judged_at(node, judgment)) else 0.0
        if self._compiled.unmet is not None:
            #  A compiled want nobody measures — the puzzles', an aversion authored as a
            #  shape — is binary by the same contract as a pattern want: unmet 1, met 0.
            #  Without this the not-knowing fallback below scored the delivered world 1.0
            #  beside the undelivered one, and only the met-test could tell them apart.
            return 0.0 if self._met_in(node, judgment) else 1.0
        #  A want whose kind nothing loaded answers for, scoring the defined fallback:
        #  maximal, because not knowing how bad IS how bad. It used to serve the freshness
        #  want too — epistemic wants had no declared measure, so every candidate world
        #  scored 1.0 and no look could be preferred to standing still. Sensing declares one
        #  now, so what is left here is a want in a society composed without whoever measures
        #  it, which `orexis-validate` refuses for a stake and cannot for anything else.
        return 1.0

    def _judged_at(self, node, judgment: Want) -> str:
        """The world this node is JUDGED in: its own, or — for a want met AT an instant
        (#619) — its own drifted to that instant, forked once per node and dropped with the
        pass. A dose that lands in the region and is dried out of it again by the instant
        has not kept the want; the root's own reading, drifted, is what makes acting early
        visible at all, since compared against the present an early dose changes nothing."""
        if judgment.holds_at is None:
            return self._graph(node)
        if node.judged is not None:
            return node.judged
        graph = self._graph(node)
        #  THE INSTANT, AND THE INSTANT AFTER IT — hold-after, in PDDL3's word. A crossing is
        #  the last instant a reading is inside its band (the floor is inclusive), and what
        #  the want prevents is the first instant outside, so the world is judged one second
        #  past the instant: a reading that reaches the floor exactly then has not held.
        instant = judgment.holds_at + timedelta(seconds=1.0)
        if instant <= self._at(node):
            node.judged = graph
            return graph
        added, retracted = self._predicted(graph, node, instant)
        if not added and not retracted:
            node.judged = graph
            return graph
        #  NAMED BY THIS NODE'S OWN GRAPH, not its path: a step is scored before its path is
        #  set, and two judged worlds under one name would be written into each other.
        fork = self.imaginarium.reached(graph, (Step(action="urn:orexis:at-instant", via=graph),),
                                        added, retracted)
        self.imaginarium.entailed(fork, added, self._compiled.keys)
        node.judged = fork
        return fork

    def _met_in(self, node, judgment: Want) -> bool:
        """Whether the desire's OWN shape is satisfied in this world.

        Its own and no others, which is what makes a pass affordable. Measured on the bench:
        validating one desire's shape costs 0.083s, and validating everything the packages ship
        costs 1.73s — twenty times more, for an answer about rules no effect here can have
        broken. A depth-2 pass would have taken twenty-two seconds instead of under two.
        Legality is asked once, of the winner, in `_offer`.

        UNFOCUSED, and that is not a detail either: pySHACL answers qualified value shapes
        wrong under `focus_nodes` — measured both ways round — and every judgment shape here is
        qualified. A candidate judged with a focus would be judged by the wrong answer, with
        nothing to show that it had been.
        """
        #  A WANT MET BY ABSENCE (#468): `orexis:unmetWhen` points at the avoided pattern,
        #  and met is the pattern binding nothing — one text, the store's own engine, judged
        #  against this node's own readings, so the flat/named-graph split a met-shape would
        #  force never opens.
        pattern = self._avoided_pattern(judgment)
        if pattern is not None:
            return not self._pattern_binds(pattern, self._judged_at(node, judgment))
        if self._compiled.unmet is not None:
            #  A SHAPE-AUTHORED WANT, judged by its compiled violation select (#497): the
            #  shape is positive and universal, the select is its negation as rows, the
            #  kernel compiled it once in `_begin`, and the store's own engine runs it at
            #  this node's world — public knowledge, the records, and this node's readings
            #  as the default graph, the same view the judge was handed as one flat text.
            #  About a millisecond where the judge's reader floors at tens; held to the judge
            #  by parity in tests/test_violation.py.
            return not bindings(self.imaginarium.query_over(
                self._compiled.unmet, *self._compiled.invariant_graphs, self._judged_at(node, judgment)))
        shape = self._shape_of(judgment)
        if shape is None:
            #  An obligation's goal state used to be read HERE, by naming the ledger's discharge
            #  (#255); since #635 the debt carries that as its own `unmetWhen`, judged above
            #  with every authored pattern, and the kernel names no word of the ledger.
            #  A want with no shape and no property — a CALL (#359) — is met exactly where
            #  whoever measures it says it is: zero urgency in the world being judged. Asked
            #  of the imaginarium at the node's graph, as `_urgency_in` asks.
            answer = self.agent.desire_urgency(
                judgment, partial(self.imaginarium.query,
                                graphs=self._dataset(self._at(node), self._judged_at(node, judgment))),
                self._judged_at(node, judgment))
            if answer is not None:
                return answer <= 0.0
            return judgment.is_met
        #  A shape want the pass did not compile in `_begin` — another judgment than the
        #  pass's — is compiled here, by the same compiler and to the same select (#548);
        #  the judge is not asked inside the search any more.
        select = violation.unmet_select(shape, self._shape_root(judgment))
        return not bindings(self.imaginarium.query_over(
            select, *self._compiled.invariant_graphs, self._judged_at(node, judgment)))

    def _estimate_in(self, node, judgment: Want) -> float | None:
        """How far this world still is from meeting the want, by the want's own declaration.

        The desire's term and the action's twin: `orexis:costs` says what a step spends,
        `orexis:estimates` says what is left to spend. Both are SELECTs the domain writes and
        the kernel runs, so a knowledge-only package can state one — which is the whole point,
        since the two domains that need this most carry no Python at all.

        None where the want declares none, and None where the select refuses to run: a want
        with no estimate is not a want that is zero away, and treating a broken declaration as
        "arrived" would crown a plan that achieved nothing.
        """
        node_uri = self._compiled.shapes.value(URIRef(judgment.uri), _AG.estimates)
        if node_uri is None:
            return None
        text = self._select_of(node_uri)
        if text is None:
            return None
        try:
            rows = bindings(self.imaginarium.query(
                bind(str(text), this=self.me.uri), self._dataset(self._at(node), self._graph(node))))
        except Exception as exc:
            log.error("estimate failed to run for %s: %s", judgment.uri, exc)
            return None
        return float(rows[0]["estimate"]) if rows and "estimate" in rows[0] else None

    def _avoided_pattern(self, judgment: Want) -> str | None:
        """The `orexis:unmetWhen` select this want carries, or None — the negative twin."""
        node = self._compiled.shapes.value(URIRef(judgment.uri), _AG.unmetWhen)
        if node is None:
            return None
        #  A node that is a SHAPE carries no select of its own: it was compiled in `_begin`
        #  (#499) and `self._compiled.unmet` answers for it.
        if (node, RDF.type, _SH.NodeShape) in self._compiled.shapes or \
                (node, RDF.type, _SH.NodeShape) in self._compiled.base:
            return None
        return self._select_of(node)

    def _select_of(self, node) -> str | None:
        """The one `sh:select` the node carries, wherever it was declared.

        THE DESIRE OWNS THE TERM AND THE PACKAGE OWNS THE MEASURE: a want says `unmetWhen` and
        `estimates` and points at a node, and that node is the DOMAIN's — declared in the
        package's ontology beside the actions it is a promise about, since "never overstates"
        is a claim about those actions' costs that only their declarer can keep. So the text
        is looked for in the wants snapshot first (a world may still write it inline beside an
        asserted want, and the avoidance tests do) and then in the belief base, whose default
        graph merges public knowledge — the desire modality drops the public graphs after its
        rebuild, so it cannot answer for a package's node. One text, both paths, and the
        same substitution after.
        """
        text = self._compiled.shapes.value(node, _SH.select)
        if text is not None:
            return str(text)
        rows = bindings(self.agent.beliefs.query(
            f"SELECT ?text WHERE {{ <{node}> sh:select ?text }} LIMIT 1", self.agent.beliefs.graphs_of(PUBLIC)))
        return str(rows[0]["text"]) if rows and rows[0].get("text") else None

    def _pattern_binds(self, text: str, graph: str) -> bool:
        """Whether the avoided pattern binds in the world at `graph` — rows mean entered.

        The same substitution a measure gets, run on the imaginarium so a candidate world
        answers exactly as the live one does. A pattern that fails to run reads as ENTERED:
        a select the gates admitted and the engine refuses is a defect someone must see,
        and a want stuck hot is how this architecture says so.

        OVER THE INVARIANT GRAPHS (#635): public knowledge AND this agent's own records as
        the default graph, which is what a rule's CONSTRUCT sees — the plain door reads
        public alone, and a debt's own met-test, written on the ledger's record, read every
        world as met because the record it named was not there to bind. `$state` still
        names the world being judged.
        """
        try:
            text = bind(text, this=self.me.uri)
            return bool(bindings(self.imaginarium.query(text, self._dataset(self._clock, graph))))
        except Exception as exc:
            log.error("avoided-state pattern failed to run: %s", exc)
            return True

    def _shape_of(self, judgment: Want):
        """The desire's shape, with everything hanging off it, or None if it has none.

        Asked of the DESIRE MODALITY, not of the world being judged (#298): what is pursued
        and what is are different stores now, and validation was always two graphs — the
        world is the data, the shape is the question. It took a `world` argument it never
        read, for years, as a note that the met-check is about one; the shapes snapshot is per
        pass (`_begin`), so a rebuild mid-search cannot hand two depths two different wants.
        """
        root = self._shape_root(judgment)
        if root is None:
            return None
        #  THE PACKAGE OWNS THE MEASURE: a world's asserted want may point at a shape the
        #  domain package declares — public knowledge, in the flat base this pass built,
        #  and not in the wants snapshot — so the carve is asked of whichever holds it.
        shapes = self._compiled.shapes
        source = shapes if (root, RDF.type, _SH.NodeShape) in shapes else self._compiled.base
        return source.cbd(root)

    def _relevant_actions(self, judgment: Want, shape) -> frozenset | None:
        """The actions relevant to this want, or None for all of them — see `relevance.py`."""
        if shape is not None:
            reads = relevance.reads_of_shape(shape, self._shape_root(judgment))
        else:
            avoided = self._compiled.shapes.value(URIRef(judgment.uri), _AG.unmetWhen)
            pattern = self._avoided_pattern(judgment) if avoided is not None else None
            if pattern is not None:
                reads = relevance.reads_of_select(pattern)
            elif avoided is not None and self._compiled.unmet is not None:
                shapes = self._compiled.shapes
                source = (shapes if (avoided, RDF.type, _SH.NodeShape) in shapes
                          else self._compiled.base)
                reads = relevance.reads_of_shape(source.cbd(avoided), avoided)
            else:
                reads = relevance.ANYTHING          # an obligation, a call: anything
        self._reads = reads
        if reads is relevance.ANYTHING:
            return None
        return relevance.relevant(reads, relevance.actions_of(self.agent.beliefs.reader(PUBLIC)),
                                  relevance.rule_edges(),
                                  relevance.subproperties_of(self.agent.beliefs.reader(PUBLIC)))

    def _shape_root(self, judgment: Want):
        """The node the desire's shape hangs from, or None where it has none."""
        node = URIRef(judgment.uri)
        #  The met-test hangs OFF the judgment node since the reification — a judgment is a node
        #  carrying its shape, not the shape itself — so the walk is one hop of `orexis:metWhen`.
        #  A node that IS a shape stays legal: an asserted root judgment is a bare NodeShape a
        #  world's TriG may state, and it never grew a judgment node around it.
        met = self._compiled.shapes.value(node, _AG.metWhen)
        if met is not None and ((met, RDF.type, _SH.NodeShape) in self._compiled.shapes
                                or (met, RDF.type, _SH.NodeShape) in self._compiled.base):
            return met
        if (node, RDF.type, _SH.NodeShape) in self._compiled.shapes:
            return node
        return None

    # --- the search --------------------------------------------------------------------------

    def plan(self, judgment: Want, surprise: tuple | None = None) -> Plan:
        """The best bounded sequence of levers for one judgment, or the reason there is none.

        Every candidate weighed is remembered as it is weighed, and the pass is written down
        when it ends (#256) — otherwise all of this dies in-process as a single log line, and
        nothing outside can reconstruct it, because the belief base is locked by the process
        holding it. `trace` explains why that is the record's one sanctioned exception.

        THE CONE IS KEPT (#553). The imaginarium and every node of the search outlive the
        pass, as diffs: each node is its parent plus the two lists its step's rules answered,
        and its graph is dropped once the node is expanded and again when the pass ends, to
        be re-made from the nearest kept graph when a rule next runs against it. The next
        pass looks for the present among the kept worlds — the invariant half unchanged, and
        a node whose world IS the present — and re-roots there, its siblings dropped, the
        search resumed with the remaining frontier; where no node matches, the cone is dead
        and the pass starts from nothing, as every pass used to. What is never kept is a
        world in the belief base: the imaginarium is still a store of its own, and a pass
        that raises forgets it whole.
        """
        try:
            plan = self._search(judgment, surprise)
            #  FROM THE LATEST START, THEN FROM NOW (#625): a want met at an instant is searched
            #  first where the present's drift stands at the instant less the longest landing;
            #  where that finds nothing — the lever it needs is on the menu now and not then, a
            #  round open now — the pass is run again from the present, and a plan found there
            #  is taken now. Two passes at most, and the second only where the first failed.
            if (judgment.holds_at is not None and not plan.steps and not self._from_now
                    and self._root is not None and self._root.landing > 0):
                self.reset()
                self._from_now = True
                try:
                    plan = self._search(judgment, surprise)
                finally:
                    self._from_now = False
            return plan
        except BaseException:
            self.reset()
            raise

    def reset(self) -> None:
        """Forget the cone: the imaginarium, every node, and what the cone was computed
        against. A raising pass does this, a changed invariant half does, and so does a
        caller done with the planner.

        AN EMPTY `_Compiled`, never None: a planner is legitimately asked for a rule's
        bindings before any pass — `_bind` reads what the want is about — and its fields
        default to the same nothing they answered with before they were gathered into one
        object (no law, no view, every row relevant).
        """
        self.imaginarium = None
        #  The rows an IMAGINED world affords, over the store those worlds live in. One per
        #  pass, beside the imaginarium it reads — not one per node, which is what it was
        #  while the world sat in this collection's constructor.
        self._imagined = None
        self._compiled = _Compiled()
        self._root = None
        self._nodes = []
        self._by_name = {}
        self._minted = 0
        self._by_diff = {}
        self._kept_worlds = 0
        self._from_now = False

    def _search(self, judgment: Want, surprise: tuple | None = None) -> Plan:
        """The pass itself. Separate only so `plan` can guarantee the forgetting above.
        `surprise` is why the mind woke, where the mark said (#632) — written on the pass
        unless the cone finds a sharper one of its own below."""
        #  Timed from HERE, which is inside the pass and outside the trace write below: a
        #  caller timing `plan()` would be timing the recording as well, and reporting the
        #  cost of reporting is the kind of number a runbook should not carry.
        self._started = time.monotonic()
        self._kept = None
        self._desire_uri = judgment.uri
        self._surprise = surprise
        #  THE PRESENT AMONG THE KEPT WORLDS (#553), else from nothing.
        #  A WANT MET AT AN INSTANT RESUMES NOTHING (#619): its root is the present projected
        #  to that instant less the plan's duration, a world that moves with the clock.
        resumed = judgment.holds_at is None and self._resume(judgment)
        if not resumed:
            #  THE CLOCK IS NOW, for every want. A pass for a want met at an instant was clocked
            #  from the reading's own instant for a day (#619), so the drift would count the
            #  reading's age — and a round opened after the reading did not hold at that
            #  instant, so the door hid it (#625). The age is drifted at the root instead
            #  (`_projected`), and the door is asked about the instants the pass stands at.
            self._clock = clock.now()
            here = self._begin(judgment)
            root_at = signature.where(here.diff, here.ground)
            self._root, self._nodes, self._by_diff = here, [here], {root_at: here}
            self._seen, self._achieved, self._best, self._bound = {root_at: here.cost}, [], here, None
            self._pending, self._kept_worlds = [], 0
            self._signature = self._invariant_signature()
        here = self._root
        trace.clear(self.agent.beliefs, self.agent.id, judgment.uri)
        met_now = self._met_in(here, judgment)
        if met_now and here.urgency <= 0.0:
            return self._record(judgment, Plan(SATISFIED, (), here.urgency, here.urgency),
                                here.urgency)
        #  Within-binding wants have ROOM: seconds until the want expires (#472). A candidate
        #  whose last change lands past it is LATE, weighed and refused like a dear one.
        #  Or AT an instant (#619): a candidate landing past the instant cannot hold at it.
        #  THE TWO ARE NOT ONE FIELD: a deadline is a BY and an instant is an AT — a plan for
        #  an instant is placed to land at it, and a serve placed to land at the claim's
        #  lapse would be a host paying on the last second.
        deadline = judgment.expires if judgment.expires is not None else judgment.holds_at
        #  Measured from the PASS'S clock, which every landing in the pass is summed from: a
        #  fresh read here made a plan placed exactly at its instant a few milliseconds late.
        room = (max(0.0, (deadline - self._clock).total_seconds())
                if deadline is not None else None)
        saw_candidate = bool(self._pending)
        self._weighed = [(0, row, None, trace.IRRELEVANT) for row in self._passed_over]
        #  THE OPEN LIST: on a fresh pass the root alone; on a resumed one the kept frontier
        #  under the new root, re-keyed — a priority reads the want's state, so it is minted
        #  here rather than at the re-root.
        #  THE OPEN LIST IS IN THE STORE. On a fresh pass the root alone stands on it; on a
        #  resumed one the kept frontier, which `_renote` put there when it rewrote the
        #  account. A priority reads the want's state, which is why the ORDER BY is built per
        #  pass rather than a number written per world.
        if not resumed:
            self._open_row(here, True)
        forked = 0                       # worlds THIS pass has imagined, against `self.budget`
        self._forked = 0

        while (node := self._next_open(met_now)) is not None:
            if forked >= self.budget:
                #  Out of budget with the frontier open: the node stays on it for the next
                #  pass, which is now nothing to do rather than a push-back — it was never
                #  taken off anything.
                break
            self._open_row(node, False)
            if self._bound is not None and node.cost + _near(node) > self._bound:
                break
            depth = len(node.taken)
            if node is here:
                for kept in self._remembered_rows(judgment):
                    saw_candidate = True
                    #  ITS PRECONDITION FIRST (#551): the facts the chain read that it did not
                    #  produce, asked of the root world as one query. A fact absent is the plan
                    #  not applying here, said with the fact rather than found by forking the
                    #  steps before the one that would have fallen off the menu.
                    absent = self._absent(kept)
                    if absent:
                        self._weighed.append((0, kept, None, trace.INAPPLICABLE, absent[0]))
                        continue
                    step, spent = self._walk(here, kept, judgment, self._bound, self.budget - forked)
                    forked += spent
                    if isinstance(step, str):
                        self._weighed.append((0, kept, None, step))
                        continue
                    ended = self._settle(kept, step, 0, judgment, met_now, room)
                    if ended is not None:
                        return ended
            for row in self._candidates(node, judgment):
                keeper = getattr(self.agent, "keeper", None)
                if keeper is not None and keeper.refused_below(row.action, row.via, row.about):
                    #  REFUSED BELOW (#533): the level beneath found no way to keep this very
                    #  move's promise within the patience. Passed over, recorded, and tried
                    #  again when the patience has passed — the world may have changed.
                    self._weighed.append((depth, row, None, trace.REFUSED))
                    continue
                if self._compiled.relevant is not None and row.action not in self._compiled.relevant:
                    #  A lever that touches nothing this want reads, by its own effect and
                    #  by nothing it could enable (#488). Recorded, never simulated, and not
                    #  a candidate seen: a menu of such rows is NOTHING — equip me — which is
                    #  the honest finding when no lever points at the want.
                    self._weighed.append((depth, row, None, trace.IRRELEVANT))
                    continue
                saw_candidate = True
                if forked >= self.budget:
                    self._weighed.append((depth, row, None, trace.SPENT))
                    node.withheld.append((row, trace.SPENT))
                    continue
                step = self._step_from(node, row, judgment, self._bound)
                if step is TOO_DEAR:
                    self._weighed.append((depth, row, None, trace.COSTLY))
                    node.withheld.append((row, trace.COSTLY))
                    continue
                if step is None:
                    self._weighed.append((depth, row, None, trace.UNSIMULATED))
                    continue
                forked += 1              # a world exists now, whatever becomes of it below
                ended = self._settle(row, step, depth, judgment, met_now, room)
                if ended is not None:
                    return ended
            self._forked = forked
            #  EXPANDED: every row from here has been taken. The graph stays until the pass
            #  ends — a pass counts the worlds it imagines, and re-making one it already made
            #  would count twice — and `_record` drops every graph then (#487, #553); the next
            #  pass re-makes what it reads from the nearest kept graph.
            node.expanded = True
            self._opened(node)

        return self._ended(judgment, met_now, saw_candidate)

    def _ended(self, judgment, met_now: bool, saw_candidate: bool) -> Plan:
        """How the pass ends once the frontier is done with: the winner among the achievers,
        or which of the silences this was.

        Separated from the loop because it decides nothing about WHERE to search and
        everything about what to CALL what the search found — and the two were read as one
        block of thirty lines at the bottom of a two-hundred-line method."""
        if self._achieved:
            #  Achievement is absolute — the desire's demand — and cost orders the
            #  achievers; the desire's own measure breaks a cost tie (nearer the aim wins),
            #  so the answer is deterministic whatever order the menu yielded them in.
            won = min(self._achieved, key=lambda s: (s.cost, s.urgency))
            return self._record(
                judgment,
                self._offer(Plan(SATISFIED, won.taken, self._root.urgency, won.urgency, cost=won.cost, origin=won.origin,
                                 landing=won.landing - self._root.landing),
                            judgment, won),
                self._root.urgency)

        #  A pass that ends with no step worth taking is labelled by the SHAPE, not by the
        #  search: a met desire that weighed its levers and found none worth pulling is
        #  SATISFIED — it is met, and near the pick every dose sizes to nothing, which is the
        #  deadband satisficing gives for free — where an unmet one in the same position is
        #  NOT_BETTER (my doses are too coarse) or NOTHING (equip me), and those must not blur.
        best = self._best
        if not saw_candidate:
            return self._record(judgment, Plan(SATISFIED if met_now else NOTHING,
                                           (), self._root.urgency, self._root.urgency), self._root.urgency)
        if best is self._root or (best.urgency, _near(best)) >= (self._root.urgency, _near(self._root)):
            after = self._root.urgency if best is self._root else best.urgency
            return self._record(judgment, Plan(SATISFIED if met_now else NOT_BETTER,
                                           (), self._root.urgency, after), self._root.urgency)
        return self._record(judgment, self._offer(
            Plan(EXHAUSTED if not self._met_in(best, judgment) else SATISFIED,
                 best.taken, self._root.urgency, best.urgency, cost=best.cost, origin=best.origin,
                 landing=best.landing - self._root.landing), judgment, best), self._root.urgency)

    def _settle(self, row, step, depth, judgment, met_now, room):
        """One simulated world weighed: forbidden, dear, late, seen, met, or a place to
        search on from. The same for a primitive's world and for the world a remembered
        plan's walk reaches — which is what makes the remembered plan one candidate
        among the rest rather than a path of its own. Answers a Plan only where the
        pass ends here: a steering keeper on an already-met want."""
        if self._compiled.law is not None:
            newly = self._forbidden_keys(step) - self._base_forbidden
            if newly:
                return self._refused(step, row, depth, trace.FORBIDDEN)
        if self._bound is not None and step.cost + _near(step) > self._bound:
            return self._refused(step, row, depth, trace.COSTLY)
        if room is not None and step.landing > room:
            return self._refused(step, row, depth, trace.LATE)
        #  WORLD AND GROUND (#587): a world already reached, ON THE SAME PREDICTION.
        #  One ground until something predicts (#589), so this is the world it always was.
        where = signature.where(step.diff, step.ground)
        novel = where not in self._seen or step.cost < self._seen[where]
        #  KEPT WHETHER OR NOT NOVEL (#553): a world already reached is not searched on
        #  from, but it may be an achiever — a look that changes nothing canonical is one —
        #  and a resumed pass must find it among the kept nodes. `_by_diff` keeps the
        #  cheapest node per world; `_nodes` keeps every settled one.
        self._keep(step)
        if novel:
            self._seen[where] = step.cost
            self._by_diff[where] = step
            if (step.urgency, _near(step), step.cost) < (
                    self._best.urgency, _near(self._best), self._best.cost):
                self._best = step
        if (novel or not met_now) and self._met_in(step, judgment):
            step.met = True
            self._weighed.append((depth, row, step.urgency, trace.MET))
            if met_now:
                #  Already met and still steering: the first novel step that
                #  keeps it met stays the answer — re-picking among keepers by
                #  cost would be shopping for a want that is not shopping for
                #  anything.
                return self._record(
                    judgment,
                    self._offer(Plan(SATISFIED, step.taken, self._root.urgency, step.urgency, cost=step.cost, origin=step.origin,
                                     landing=step.landing - self._root.landing),
                                judgment, step),
                    self._root.urgency)
            self._achieved.append(step)
            self._bound = step.cost if self._bound is None else min(self._bound, step.cost)
            return None
        if not novel:
            self._weighed.append((depth, row, step.urgency, trace.SEEN))
            return None
        self._weighed.append(
            (depth, row, step.urgency,
             trace.BETTER if step.urgency < self._root.urgency else trace.WORSE))
        self._open_row(step, True)
        return None

    def _refused(self, step, row, depth, verdict):
        """A world the search will not plan THROUGH, kept with the verdict that stopped it.
        Still a world the present may land in (#570), and the plan from inside a forbidden
        state is exactly the recovery never-newly-enter keeps."""
        step.verdict = verdict
        self._keep(step)
        self._weighed.append((depth, row, step.urgency, verdict))
        return None

    # --- the cone across passes (#553) ---------------------------------------------------------

    def _resume(self, judgment: Want) -> bool:
        """Re-root the kept cone on the present, or say there is nothing to resume.

        Two questions, in the order that makes the second cheap. Has the INVARIANT half
        moved — public knowledge, the records, the wants, everything a node's world holds
        besides its readings? Then every kept diff was computed against a world that is gone,
        and the cone is forgotten whole. Is the present one of the kept worlds? The present's
        diff against the old base is looked up among the nodes; the one it names becomes the
        root, its siblings and their subtrees are dropped, and the frontier beneath it is the
        next pass's open list. Nothing matching is the cone dead: a fresh pass, as before.

        EXACT, for now: a kept world is the present when their canonical facts agree, a
        reading by its value. That is right for a world nothing moves but the agent, and it
        is why a plant, whose readings drift, resumes nothing yet — identification by
        interval (#554, #556) is what loosens it.

        BY FACTS ALONE, and deliberately, though a node is a world AND a ground inside a
        pass (#587): a kept world is matched by what it holds, never by what it was predicted
        on. What the ground separates is two worlds the SEARCH imagines; what identification
        asks is which imagined world the real one landed in — and the answer, once a pass has
        more than one ground, is also which of the world's own branches happened.
        """
        if self.imaginarium is None or self._root is None:
            return False
        if self._invariant_signature() != self._signature:
            self.reset()
            return False
        present = self._facts_now()
        base = self._base_facts
        #  WITHIN THE VIEW (#554, #565): the present is a kept world when they agree on what
        #  the want's closure reads; a fact outside it may have drifted. Keys stay whole —
        #  inside a pass two worlds differing in any fact a lever wrote are two worlds — so
        #  the kept nodes are scanned by their projected diff, a hundred at most.
        wanted = self._key((present - base, base - present))
        node = next((m for m in self._nodes if self._key(m.diff) == wanted), None)
        if node is None and any(m.withheld or not m.expanded for m in self._nodes):
            #  COMPLETE BEFORE GIVING UP (#570): what the last pass did not fork is forked
            #  now — the rows a node withheld for budget or cost, and every row of a node
            #  the budget stopped before it was expanded — at every kept node, since the
            #  present may be more than one step from the old root — and the present is
            #  looked for among the new worlds. A match here is a world we chose not to
            #  imagine. Bounded by the frontier and what was withheld, both by the budget.
            for m in list(self._nodes):
                if m.verdict is not None:
                    continue
                rows = [row for row, _ in m.withheld] if m.expanded else [
                    row for row in self._candidates(m, judgment)
                    if self._compiled.relevant is None or row.action in self._compiled.relevant]
                for row in rows:
                    step = self._step_from(m, row, judgment, None)
                    if step is not None and step is not TOO_DEAR:
                        self._keep(step)
                        at = signature.where(step.diff, step.ground)
                        if at not in self._seen:
                            self._seen[at] = step.cost
                            self._by_diff[at] = step
                m.withheld, m.expanded = [], True
            node = next((m for m in self._nodes if self._key(m.diff) == wanted), None)
            if node is not None:
                self._surprise = (SURPRISE_WITHHELD, _said((present - base, base - present)))
        if node is None:
            #  No lever of ours reaches this world: another agent acted, the environment
            #  moved, or our action has an outcome we do not declare (#522).
            self._surprise = (SURPRISE_EXOGENOUS, _said((present - base, base - present)))
            self.reset()
            return False
        #  BY BAND, AND THAT IS EXACT (#579). A kept world states its readings by what they
        #  ARE and never by a number; the present, observed, carries a number beside its band,
        #  and the number is nothing a kept world predicted. A match by band is therefore the
        #  whole of the identity, and the worlds beneath the node — computed from bands, each
        #  carrying its own — stand. The cell-only re-root of #573, which dropped a subtree
        #  computed from a number the present did not hold, has nothing left to drop.
        #  A LEVER ON THE MENU NOW AND NOT WHEN THE CONE WAS MADE — a round opened since — is
        #  a timed graph, which the invariant half leaves out on purpose (#589): the cone
        #  survives it, and a kept root already expanded would never offer the lever. So the
        #  present's menu is asked once more, over the graphs the present holds now, and a cone
        #  whose root gained a lever is forgotten — a fresh pass is what finds the chain
        #  through it, as it found the refill through a round nobody had opened before.
        beliefs = self.agent.beliefs
        self.imaginarium.refresh(beliefs, beliefs.catalogue, *beliefs.graphs_of(*KNOWN))
        if node.expanded:
            offered = frozenset((r.action, r.via, r.about, r.want) for r in self.agent.afforder.offered(
                self._imagined, graphs=self._dataset(clock.now(), STATE_GRAPH), only=self._compiled.asked))
            if offered - node.menu:
                self.reset()
                return False
        self._reroot(node, present, subtree=True, judgment=judgment)
        return True

    def _reroot(self, node, present: frozenset, subtree: bool = True, judgment=None) -> None:
        """`node` becomes the root: every node beneath it re-based on the present, everything
        else dropped. Diffs are re-based by set algebra on absolute worlds — a kept world is
        the old base less its minus set plus its plus set, and its new diff is what that
        world holds beyond the present and what the present holds beyond it — so a path
        that returns to the new root returns to the empty diff, as `advance` promises."""
        base = self._base_facts
        keep = [m for m in self._nodes if self._descends(m, node)] if subtree else [node]
        if not subtree:
            node.expanded, node.withheld, node.met, node.legal = False, [], False, None
        for m in self._nodes:
            self._release(m)
        #  THE PRESENT'S READINGS ARE THE ROOT'S GRAPH, observed: the imaginarium's copy is
        #  refreshed from the belief base rather than re-made from the old root plus the
        #  matched diff — the two agree exactly here, and the observed one is the one that
        #  says what the present is.
        self.imaginarium.observe(self.agent.beliefs, STATE_GRAPH)
        #  AND EVERY OTHER GRAPH A RULE READS, as the present holds it now, with the catalogue
        #  that says what they are: a round opened or a claim arrived since the cone was made
        #  is a timed graph, which the invariant half leaves out on purpose (#589) — the cone
        #  survives it, and the resumed pass has to read it.
        beliefs = self.agent.beliefs
        self.imaginarium.refresh(beliefs, beliefs.catalogue, *beliefs.graphs_of(*KNOWN))
        depth, cost0, landing0 = len(node.taken), node.cost, node.landing
        for m in keep:
            dplus, dminus = m.diff
            world = (base - dminus) | dplus
            #  WITHIN THE VIEW: a fact outside it that drifted between the passes is the
            #  present's, not the world's to predict, and is not carried into the diff.
            m.diff = (self._project(world - present), self._project(present - world))
            m.taken = m.taken[depth:]
            #  AND ITS NAME FOLLOWS ITS PATH. A world is named by the path that reached it, so
            #  a re-root that shortens the path renames the world — `_graph` would have done it
            #  silently the next time the readings were re-made, leaving whatever had been
            #  written ABOUT the world under a name nothing would find again. Said here, where
            #  the path changes, so the name is true from the moment it changes.
            if m is not node:
                m.graph = imaginarium.name_of(m.taken)
            m.cost -= cost0
            m.landing -= landing0
            m.origin = m.taken[0].action if m.taken else None
        #  THE NEW ROOT IS THE PRESENT, so the pass's clock is now: a kept world's landing
        #  is re-based below, and both halves of a node's instant move with the root (#588).
        self._clock = clock.now()
        node.parent, node.graph, node.materialised = None, STATE_GRAPH, True
        #  The root stands nowhere but the present. Re-based by set algebra it would carry
        #  the number it predicted against the number the present holds; by cell they are
        #  one world, and that is what made it the root.
        node.diff = signature.EMPTY
        self._root, self._nodes, self._base_facts = node, keep, present
        if not subtree and judgment is not None:
            #  Scored from the present, not from the number it was predicted to hold: a pot
            #  a hundredth below its aim is not a met want.
            node.urgency = self._urgency_in(node, judgment)
            node.estimate = self._estimate_in(node, judgment)
        #  Re-keyed AFTER the diffs are re-based above. A kept world's GROUND survives a
        #  re-root untouched: which of the world's branches it sits under is not measured from
        #  the root, and the new root is a world the old cone predicted on that same ground.
        self._by_diff = {signature.where(m.diff, m.ground): m for m in keep if m.verdict is None}
        self._seen = {signature.where(m.diff, m.ground): m.cost for m in keep if m.verdict is None}
        #  A world refused as dear is dear against a bound that went with the old root, and
        #  may be worth a look now; one refused as forbidden or late stays off the frontier.
        #  The new root too, where the last pass never took a row from it — a world reached
        #  at the budget's edge, or one completed on a miss (#570): the resumed pass expands
        #  it as a fresh pass expands its root.
        self._pending = [m for m in keep if not m.expanded
                         and m.verdict in (None, trace.COSTLY)]
        for m in self._pending:
            m.verdict = None
        node.verdict = None
        self._achieved = [m for m in keep if m.met and m is not node]
        self._bound = min((m.cost for m in self._achieved), default=None)
        self._best = min(keep, key=lambda m: (m.urgency, _near(m), m.cost))
        self._kept_worlds = len(keep)          # the present among them: one is a leaf resumed
        #  What `_begin` computes AT the root, for the new one.
        self._at_root(node)
        #  AND THE STORE SAYS THE WHOLE PASS AGAIN. Everything above moved a number in every
        #  kept row and dropped every row that is not kept; an account amended rather than
        #  rewritten would offer a reader somewhere to search from that no longer exists.
        self._renote()

    @staticmethod
    def _descends(m, node) -> bool:
        while m is not None:
            if m is node:
                return True
            m = m.parent
        return False

    def _release(self, node) -> None:
        """Drop this world's graph, keeping the node; the root's readings are never dropped."""
        if node.judged is not None and node.judged != node.graph:
            self.imaginarium.drop(node.judged)
        node.judged = None
        if node is not self._root and node.materialised:
            self.imaginarium.drop(node.graph)
            node.materialised = False
            node.readings = None

    def _graph(self, node) -> str:
        """This node's graph in the imaginarium, re-made from the nearest kept ancestor's if it
        was dropped — the parent's graph, forked, the node's two lists applied. A world is
        its parent plus its diff, and the graph is a cache of that (#553)."""
        if node is self._root or node.materialised:
            return node.graph
        parent = self._graph(node.parent)
        node.graph = self.imaginarium.reached(parent, node.taken, node.added, node.retracted)
        node.materialised = True
        return node.graph

    def _view_of(self, judgment: Want) -> frozenset | None:
        """The predicates this pass's worlds may differ in, or None for all of them."""
        reads = getattr(self, "_reads", relevance.ANYTHING)
        if reads is relevance.ANYTHING or self._compiled.relevant is None:
            return None
        view = set(reads)
        table = relevance.actions_of(self.agent.beliefs.reader(PUBLIC))
        for action in self._compiled.relevant:
            r, w = table.get(action, (frozenset(), frozenset()))
            if r is relevance.ANYTHING or w is relevance.ANYTHING:
                return None
            view |= set(r) | set(w)
        #  As strings: relevance answers rdflib terms, and a canonical fact names its
        #  predicate as text — an rdflib IRI is not equal to the same text.
        return frozenset(str(x) for x in view)

    def _standing_in(self) -> list:
        """The graphs a world's FACTS come from — everything the agent holds, less whatever
        holds during a period of its own (#589).

        A time-bounded graph is read by rules and is not part of where a plan stands. A
        forecast is the case: nothing the agent does moves what the weather will be, so it is
        a constant of the plan exactly as the outside reading the vent already leans on — and
        if it entered the signature, every kept world would die the moment the forecast
        refreshed, differing in facts no lever touched.
        """
        store = self.agent.beliefs
        #  AND THE CLASSIFICATION, SUBTRACTED BY NAME, which rule 1 allows for exactly this:
        #  saying which way a fact came by rather than enumerating what to read. What a graph
        #  IS is a mention, not a fact a plan stands on — and a forecast arriving at runtime
        #  says what it is there, so a signed classification would kill every kept world on a
        #  change no lever caused, which is the thing this exclusion exists to prevent.
        out = set(store.periods())
        return [iri for iri in store.graphs_of(*KNOWN) if iri not in out]

    def _dataset(self, at, world: str) -> list[str]:
        """What a rule is answered over in one imagined world: every graph of the kinds a rule
        reads, holding at `at`, with `world` — the node's readings — standing where the
        present's stand. Built here and handed to the imaginarium's `query`, so the instant
        and the place a rule is asked about are one list the search made, and a rule says
        neither (#666)."""
        readings = set(self.imaginarium.graphs_of(STATE))
        return [g for g in self.imaginarium.graphs_of(*KNOWN, at=at) if g not in readings] + [world]

    def _key(self, diff: tuple) -> frozenset:
        """The key the present is matched to a kept world by: the WORLD the diff reaches,
        within the view, a reading by what it IS — the bands the domain asserted on it
        (#576). The world and not the diff's halves, because a class the base already held
        cancels out of a diff and leaves the number standing alone: a dose from inside the
        region to inside the region changes the number and no class, and by class it is the
        same world as the present that landed a hundredth off."""
        base = self._base_facts
        return self._project(signature.by_class((base - diff[1]) | diff[0]))

    def _project(self, facts) -> frozenset:
        """The facts within the view. A plain fact is in it by its predicate; a keyed fact —
        a reading — by the property the want is about, since every reading carries the same
        predicates and only its key says which property it is of."""
        if self._compiled.view is None:
            return frozenset(facts)
        #  WHATEVER THE WANT IS ABOUT, and a want may be about several things (#566): a
        #  reading is in the view when its key names any of them, so a bed's comfort keeps
        #  both its soil and its air and still drops a neighbour's.
        about = self._compiled.about_of.get(getattr(self, "_desire_uri", None)) or ()
        out = set()
        for f in facts:
            if f[0] == "keyed":
                if not about or any(v in about for _, v in f[2]):
                    out.add(f)
            elif f[1] in self._compiled.view:
                out.add(f)
        return frozenset(out)

    def _facts_now(self) -> frozenset:
        """The whole base as the store holds it now, in canonical facts."""
        store = self.agent.beliefs
        return signature.facts((quad for iri in self._standing_in()
                                for quad in store.quads(iri)), self._compiled.keys)

    def _invariant_signature(self) -> frozenset:
        """Everything a node's world holds besides its readings, as canonical facts: public
        knowledge, the records, the wants. A kept cone is valid exactly while this is what
        it was computed against.

        LESS WHAT HOLDS DURING A PERIOD, AND LESS WHAT A GRAPH IS (#589). A forecast is in
        the world a judged node is made of — no step changes it, so it belongs in the
        invariant HALF — and neither it nor the classification saying what it is may be in
        this signature, or a cone would die every time a forecast refreshed, on a change no
        lever caused and no plan depends on.
        """
        store = self.agent.beliefs
        out = set(store.periods())
        quads = [quad for iri in self._compiled.invariant_graphs if iri not in out
                 for quad in store.quads(iri)]
        quads += [quad for iri in self._compiled.want_graphs for quad in self.agent.desires.quads(iri)]
        return signature.facts(quads, self._compiled.keys)

    def _record(self, judgment, plan, stands_at):
        """Write the pass down and hand back the plan unchanged.

        Threaded through the returns rather than wrapped around `plan()` so that the EARLY ones
        are recorded too — a desire already satisfied and a desire nothing points at are the two
        answers a reader most wants and the two a wrapper would have missed. The same threading
        is why the clock is read here: every return passes through, so no exit is untimed.
        """
        #  PLACED AT THE ROOT'S INSTANT (#625), where the pass stood later than now.
        if (judgment.holds_at is not None and plan.steps and self._root is not None
                and self._root.landing > 0):
            plan = replace(plan, placed_at=self._clock + timedelta(seconds=self._root.landing))
        trace.write(self.agent.beliefs, self.agent.id, judgment, plan,
                    getattr(self, "_weighed", []), stands_at,
                    time.monotonic() - self._started, self._judged(judgment),
                    kept=getattr(self, "_kept_worlds", 0),
                    surprise=getattr(self, "_surprise", None))
        #  THE PASS IS OVER: every imagined graph is dropped (#487, #553), the nodes stay.
        for node in getattr(self, "_nodes", ()):
            self._release(node)
        return plan

    def _judged(self, judgment: Want) -> tuple[str, str | None]:
        """Which way `_met_in` took for this want, and the text where the way is one (#502).

        The SAME order as `_met_in`, and only that order: an authored pattern first, then the
        select compiled in `_begin` — a shape want's violation select, or an avoided state's
        conformance select — and a module's measure for
        everything else. Asked after the pass rather than remembered during it so the trace
        says what the judge would have said of this want in ANY world, not what it happened
        to say of the last.
        """
        pattern = self._avoided_pattern(judgment)
        if pattern is not None:
            return trace.AUTHORED, pattern
        if self._compiled.unmet is not None:
            return trace.COMPILED, self._compiled.unmet
        return trace.MEASURE, None

    def _offer(self, plan: Plan, judgment: Want, node) -> Plan:
        """A plan, once it has been checked for legality — and only the winner is checked.

        Validating every candidate against the whole rulebook was the obvious reading and costs
        twenty times what the judgment check does: measured on the bench, 1.73s against 0.083s, so a
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
        #  THE PRECONDITION OF EVERY STEP, once, along the winning path (#550): what each
        #  step's rules read in the world it was planned from, asked of that world while
        #  the imaginarium still holds it — depth queries, never per fork. ONCE per node
        #  (#553): a kept node offered again by a resumed pass carries them already.
        if any(step.precondition is None for step in node.taken):
            node.taken = self._with_precondition(node.taken, judgment, node)
        plan = replace(plan, steps=node.taken)
        if node.legal is not None:
            return plan if node.legal else Plan(REFUSED, (), plan.urgency_now, plan.urgency_after)
        #  ASKED OF THE IMAGINARIUM, and the world never leaves the store (#548): every
        #  package shape about this agent and every shape it holds, compiled once to a
        #  select whose rows are its violations (`violation.report_selects`), run at this
        #  node's graph. What used to happen here — the world dumped to text, crossed into
        #  rudof, its report parsed back — cost 230 ms a pass on `world/simulation` after two
        #  rounds of trimming (#485, #547); the selects cost 60, and the judge stays at the
        #  gates, where the authored report prose is for a person.
        node.legal = not self._illegal(node, self._compiled.legal)
        if node.legal:
            return plan
        log.warning("the world this plan would reach is one the society refuses — not taken")
        return Plan(REFUSED, (), plan.urgency_now, plan.urgency_after)

    def _violation_shapes(self, world):
        """The MUST NOT the data carries: violation-severity shapes, met-tests excluded.

        Data-borne on purpose — the packages' shapes are about what an agent IS and run at
        the gates; what a plan may PASS THROUGH is ratified in the world, arrives as data,
        and is small, which is what makes asking it per node affordable. None where the
        world states none, and the per-node check then never runs.
        """
        met = set(world.objects(None, _AG.metWhen))
        law, found = rdflib.Graph(), False
        for shape in set(world.subjects(rdflib.RDF.type, _SH.NodeShape)) - met:
            cbd = world.cbd(shape)
            if (None, _SH.severity, _SH.Violation) in cbd:
                law += cbd
                found = True
        for prefix, ns in world.namespaces():
            law.bind(prefix, ns)
        return law if found else None

    def _forbidden_keys(self, node) -> frozenset:
        """Which forbidden states this world is in — keyed so never-newly-enter can subtract.

        The key is (shape, focus, value): enough to tell a NEW entry from the one the base
        already stood in, without counting a re-report of a standing violation as news.
        Severity is filtered again on the RESULT, because one shape may mix forces.
        """
        #  The law graph is Violation-only by construction (`_violation_shapes` keeps only
        #  declared-Violation cbds), and the compiled report keeps only what a shape states
        #  at `sh:Violation` besides, so a law shape mixing forces within itself would be
        #  read the way the judge reads it. Compiled once per pass, asked per candidate
        #  at its own graph (#548): a rudof verdict here had a fixed floor of ~75 ms per
        #  candidate, paid at every expansion in a world that ratifies a law.
        return frozenset(self._illegal(node, self._compiled.law_selects))

    def _with_precondition(self, steps: tuple, judgment: Want, node) -> tuple:
        """The steps with each one's precondition filled: the facts its rules read at its parent
        world, canonical, as `predicts` is. A step whose rules will not say is carried with
        None — the plan is not worse for it, and the log has the reason. `node` is the world
        the last step reached; its ancestry is the parent world of each step."""
        chain, m = [], node
        while m is not None:
            chain.append(m)
            m = m.parent
        chain.reverse()                      # the root first; chain[i] is step i's parent world
        out = []
        for i, step in enumerate(steps):
            reached = chain[i + 1] if i + 1 < len(chain) else chain[i]
            bind = self._bind(judgment, node=chain[i], row=step, litres=step.quantity or 0.0,
                              lands=reached.landing - chain[i].landing)
            try:
                read = effects.precondition(self.imaginarium, step.action,
                                        keyed=tuple(self._compiled.keys), **bind)
                found = signature.by_class(signature.facts(read, self._compiled.keys))
            except Exception as exc:               # noqa: BLE001 — a package's rule, not the pass
                log.error("could not read the precondition of %s: %s", step.action, exc)
                found = None
            out.append(replace(step, precondition=found))
        return tuple(out)

    def _illegal(self, node, selects: dict) -> list[tuple]:
        """The violations `selects` find in this node's world — (shape, focus, which
        constraint, the offending value or None) per row — asked of the imaginarium with the
        view the border text holds: public knowledge, the records, the wants, this node's
        readings. Empty is legal."""
        graphs = (*self._compiled.invariant_graphs, *self._compiled.want_graphs, self._graph(node))
        return [(str(shape), row["this"], row.get("_constraint"), row.get("_offending"))
                for shape, select in selects.items()
                for row in bindings(self.imaginarium.query_over(select, *graphs))]

    def _remembered_rows(self, judgment: Want) -> list:
        """The plans remembered for this want, as rows — asked once per pass."""
        if getattr(self, "_kept", None) is None:
            from . import remembered
            self._kept = [
                _Remembered(action=uri, via=(steps[0].via or uri), want=judgment.uri,
                            steps=tuple(steps), about=steps[0].about)
                for uri, steps, _ in remembered.remembered_for(self.agent, judgment.uri)]
        return self._kept

    def _absent(self, kept: _Remembered) -> list:
        """The facts of this plan's regressed precondition absent from the present — empty
        where it holds. A plan whose steps carry no precondition has none to ask, and is walked
        as before."""
        from . import remembered
        facts = remembered.regressed(kept.steps)
        return [] if facts is None else remembered.missing(self.agent, facts)

    def _walk(self, node, kept: _Remembered, judgment: Want, bound, budget_left: int):
        """A remembered plan walked from `node` as one candidate: the world its steps reach,
        or the verdict that stopped the walk, and how many worlds it forked either way.

        WALKED, NEVER SEARCHED: the steps are the plan's, in its order, and each is taken
        only where the menu of the world the walk stands in offers that very row — the same
        action through the same lever about the same thing. A step not on the menu is the
        plan not applying here, said as a verdict rather than guessed around; a step refused
        below, dear, unsimulable or landing in a forbidden state stops the walk by the same
        verdicts a primitive earns. Its composed effect is the world reached; its
        applicability was asked first, as the regressed precondition (#551), and the walk
        re-checks it step by step on the menu of each world reached.
        """
        cur, forks = node, 0
        keeper = getattr(self.agent, "keeper", None)
        for wanted in kept.steps:
            if forks >= budget_left:
                return trace.SPENT, forks
            if keeper is not None and keeper.refused_below(wanted.action, wanted.via, wanted.about):
                return trace.REFUSED, forks
            row = next((r for r in self.agent.afforder.offered(
                self._imagined, graphs=self._dataset(self._at(cur), self._graph(cur)),
                only=frozenset({wanted.action}))
                if r.is_own and r.via == wanted.via and (r.about or None) == (wanted.about or None)),
                None)
            if row is None:
                return trace.UNAVAILABLE, forks
            step = self._step_from(cur, row, judgment, bound)
            if step is TOO_DEAR:
                return trace.COSTLY, forks
            if step is None:
                return trace.UNSIMULATED, forks
            forks += 1
            if self._compiled.law is not None:
                #  EVERY STATE of the walk is held to the law, as every state of a plan is
                #  (#468): the world the last step reaches is settled by the caller, the
                #  ones between are held here.
                if self._forbidden_keys(step) - self._base_forbidden:
                    return trace.FORBIDDEN, forks
            cur = step
        cur.origin = kept.action
        return cur, forks

    def _candidates(self, node, judgment: Want):
        """The levers worth simulating from here — the menu, re-run in the world reached.

        AN AFFORDANCE IS THE PRECONDITION LANGUAGE, which is why chaining needs none of its own: a
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
        #  ASKED OF THE IMAGINARIUM, at the node's own graph (#359): a premise may be a fact
        #  an earlier step made true — Offering needs stock, Acquiring's effect raises it, and
        #  "acquire, then offer" is a plan only if the menu of the world after the first step
        #  shows the second. The root node's graph is the agent's own readings, so at depth 0
        #  this is the ordinary menu, exactly as before.
        rows = self.agent.afforder.offered(
            self._imagined, graphs=self._dataset(self._at(node), self._graph(node)),
            only=self._compiled.asked)
        #  WHAT THE MENU WAS when this node was expanded, so a resumed pass can tell a lever
        #  that is on it now and was not then (`_resume`).
        node.menu = frozenset((r.action, r.via, r.about, r.want) for r in rows)
        for row in rows:
            #  A ROW THAT NAMES A WANT SERVES THAT WANT — Dosing for this pot and not the next,
            #  and a look for this instrument. A row owed to someone serves the want it names
            #  and no other: the market joined it to the debt the want is about, so a debt is
            #  served by its counterparty's row or approached through this agent's own levers,
            #  and which of those levers serve a debt — the refill of the vessel a serve draws
            #  from (#255) — the market says by naming the want on them. What a counterparty
            #  is, this file does not know. A want ABOUT NOTHING — a call — ranges over every
            #  row of the agent's own, because what would raise the stock a round needs is a
            #  row the stake names (the dealer's two-step).
            if not row.is_own:
                if row.want != judgment.uri:
                    continue
            elif (row.want is not None and row.want != judgment.uri
                    and judgment.uri in self._compiled.about_of):
                continue
            yield row

    def _begin(self, judgment: Want) -> _Node:
        """This plan's imaginarium, and the root node standing in the world the agent is in.

        The imaginarium is built per PLAN and dropped with it — see `plan`, which does that in a
        `finally` so a pass that raises leaves nothing imagined behind either. What it holds is
        public knowledge, this agent's beliefs and this agent's readings, all copied: the
        readings are the root node's own graph, which is why `$state` at depth 0 still names
        exactly what it always did, and every deeper node forks from it.
        """
        #  A FRESH ONE PER CONE: everything below is worked out against the world as it
        #  stands now, and a field left over from the last cone would be read as this one's.
        self._compiled = _Compiled()
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
            *self.agent.beliefs.graphs_of(*KNOWN))
        #  The rows an imagined world affords, over the store those worlds live in — built here
        #  beside the imaginarium and once for the pass.
        self._imagined = Affordances(self.imaginarium)
        #  What this agent PURSUES, snapshotted for the pass. The WANT graphs alone — derived,
        #  asserted, and the promises a bridge raised — never the record projections: the
        #  flat world below already carries the pick record through the belief flatten, and a
        #  second copy with fresh blank nodes splits every aim in two, which AimShape rightly
        #  refuses as not steering. They come from the judgment modality's OWN store, and go
        #  two ways: into the imaginarium under their own names (#547), so a shape's target
        #  over a want is resolved where the world is and the border is one dump; and as one
        #  rdflib graph, because a cbd walks blank nodes and the carves below want one —
        #  small, a few hundred triples, and per pass for the same reason the imaginarium is.
        #  And the wants pursued under a root (#618): a derived want POINTS at its root's
        #  met-test, and a snapshot without the graph it points from has no shape to compile
        #  for it — the loner masked that, its child judged by sensing's measure instead.
        #  The ledger too (#635): a debt carries its met-test as every authored want does,
        #  and the snapshot is where `_avoided_pattern` looks for it.
        #  ASKED BY CLASS, never named (#705), and by what a graph HOLDS: every graph of
        #  desires (the roots, the promises, the world's asserted one), every graph of wants
        #  (each pursued want, the asserted one again) and the debts record — each classified
        #  by its owner, whatever it is called, the children holding now among them (#645).
        self._compiled.want_graphs = tuple(self.agent.beliefs.graphs_of(
            DESIRE, WANT, RECORD, at=self._clock))
        self.imaginarium.copy_in(self.agent.desires, *self._compiled.want_graphs)
        self._compiled.shapes = effects.applied((), self.agent.desires.construct(
            f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ "
            f"VALUES ?g {{ {' '.join(f'<{g}>' for g in self._compiled.want_graphs)} }} "
            f"GRAPH ?g {{ ?s ?p ?o }} }}"), ())
        base = self._beliefs()
        self._compiled.base = base
        #  The wants ride in the flat world too, exactly as they did when the constraint graph
        #  was public: `_offer`'s legality check validates the world the plan would reach, and
        #  the capability shapes demand the regions — a world without them is refused for a
        #  reason no lever caused (#312).
        for triple in self._compiled.shapes:
            base.add(triple)
        #  THE SHAPES THIS AGENT HOLDS, carved once (#547): the base does not change inside a
        #  pass, so the walk `_offer` used to repeat per winner answers the same graph every
        #  time. Carved AFTER the wants join the base, because a held want is one of them.
        self._compiled.held = held_shapes(base, self.me.uri)
        #  The base's canonical facts, once per pass: `advance` needs them to tell a fact
        #  restored from a fact introduced, which is what lets a path that returns to the base
        #  world return to the EMPTY diff instead of accumulating noise. Read as the store's
        #  own quads — the same graphs `_beliefs` flattens — because the signature works in
        #  pyoxigraph terms and the rdflib copy exists only for pySHACL.
        store = self.agent.beliefs
        #  Which beliefs are UPSERTED, and by what — declared by the package that writes them
        #  (`orexis:keyedBy`, `orexis:carries` on the node's class), read once per pass so the signature
        #  canonicalises a reading without this file knowing what one looks like.
        self._compiled.about_of = self.agent.desires.abouts(self.me.uri)
        self._compiled.keys = signature.keys_of(store.reader(PUBLIC))
        #  THE LAW THIS PASS PRUNES BY (#468): the violation-severity shapes the DATA
        #  carries — a world-authored MUST NOT over a runtime state — collected once, held
        #  against every candidate at expansion rather than against the winner alone. The
        #  base's own violations are kept because the rule is NEVER-NEWLY-ENTER: an agent
        #  already inside a forbidden state must keep its exit plans, or the recovery is
        #  pruned with everything else — the same trap that made the envelope a warning at
        #  the gates, met from the planner's side. Empty in a world that ratifies no such
        #  shape, and then this costs nothing per node.
        self._compiled.law = self._violation_shapes(base)
        self._base_facts = signature.facts((
            quad for iri in self._standing_in()
            for quad in store.quads(iri)), self._compiled.keys)
        #  COMPILED, ONCE PER PASS (#548): the law's selects, and the legality check's — the
        #  packages' shapes about this agent, compiled once per process and cached by
        #  focus, beside the shapes this agent holds, carved and compiled here. A shape the
        #  compiler cannot say REFUSES here, loudly, the way a want's does: a legality
        #  check that quietly judged less than the gates do would let the search reach a
        #  world boot refuses.
        self._compiled.law_selects = (violation.report_selects(self._compiled.law)
                             if self._compiled.law is not None else {})
        self._compiled.legal = {**legality_selects(self.me.uri),
                       **violation.report_selects(self._compiled.held)}
        #  THE INVARIANT HALF OF EVERY WORLD THIS PASS WILL JUDGE, written once by the store's
        #  own engine (#481). Every graph the imaginarium copied EXCEPT the readings — those
        #  are what a step changes, and each node carries its own — plus the wants, which the
        #  flat world carried before and `_offer` still needs. Asked rather than named, like
        #  everything else about which graphs exist.
        readings = set(self.agent.beliefs.graphs_of(STATE))
        self._compiled.invariant_graphs = tuple(
            iri for iri in self.agent.beliefs.graphs_of(*KNOWN, at=self._clock) if iri not in readings)
        #  SKOLEMIZED AT THE BORDER (#485), by the scheme `judge.crossed` uses for a graph: a
        #  blank focus node is then legal in rudof's VALUES pre-binding, and the legality
        #  check below reads this text as it is, with no rdflib graph in between.
        self._invariant_text = None      # written on the first `_border`, and most passes never ask
        #  THE WANT'S VIOLATION SELECT, compiled once for the pass (#497) — None where the
        #  want is not a shape (a pattern want, an obligation, a call). A shape this compiler
        #  cannot say REFUSES here, loudly, rather than judging by something quieter: a want
        #  that silently read as met is the failure the compiler exists to rule out.
        shape = self._shape_of(judgment)
        self._compiled.unmet = (violation.unmet_select(shape, self._shape_root(judgment))
                       if shape is not None else None)
        #  THE NEGATIVE TWIN AS A SHAPE (#499): an aversion under `orexis:unmetWhen` authored
        #  as the avoided state, compiled to its CONFORMANCE select — rows where the state
        #  has been entered — and judged by the same path as a compiled positive want.
        avoided = self._compiled.shapes.value(URIRef(judgment.uri), _AG.unmetWhen)
        if avoided is not None and self._compiled.unmet is None:
            shapes, flat = self._compiled.shapes, self._compiled.base
            source = (shapes if (avoided, RDF.type, _SH.NodeShape) in shapes
                      else flat if (avoided, RDF.type, _SH.NodeShape) in flat
                      else None)
            if source is not None:
                self._compiled.unmet = violation.entered_select(source.cbd(avoided), avoided)
        #  WHICH LEVERS COULD SERVE THIS WANT (#488): what the want reads, off its shape or
        #  its pattern; what each action writes and reads, off the actions themselves; the
        #  backward closure of the two. A row whose action is outside the set is never
        #  simulated — one free foreign action multiplied a hanoi solve 2.8 times, and this is
        #  the only defence that sees it. None where the want reads anything a parser cannot
        #  name, and then every row is weighed exactly as before: over-approximation is safe.
        self._compiled.relevant = self._relevant_actions(judgment, shape)
        #  THE WANT'S VIEW (#554, #565): the predicates its closure names — what it reads,
        #  and what the relevant levers read and write — and, for a reading, the property
        #  the want is about. A present is matched to a kept world WITHIN the view, so a fact
        #  the want never reads may drift without killing the cone; None is every fact.
        self._compiled.view = self._view_of(judgment)
        #  WHAT THE MENU IS ASKED FOR, per node (#504): the relevant levers. Every action on a
        #  menu states an effect — the gate holds a choosable action to both texts (#506) —
        #  so there is no lever to keep on the menu for the sake of saying it was passed over.
        self._compiled.asked = self._compiled.relevant
        #  THE LEVERS PASSED OVER, asked ONCE per pass at the root rather than at every node,
        #  and written as passed over only where they had a row to pass over: a trace that
        #  named every irrelevant action in the vocabulary would name Move in a plant world
        #  with no disk in it. One query per foreign action per pass is what a truthful
        #  trace costs, against one per node before this.
        here = _Node(graph=STATE_GRAPH)
        if judgment.holds_at is not None:
            here = self._projected(here, judgment, latest=not self._from_now)
        here.estimate = self._estimate_in(here, judgment)
        here.urgency = self._urgency_in(here, judgment)
        self._root = here
        self._at_root(here)
        #  THE ROOT IS A WORLD TOO, and says so in the store: where the pass stands, forked
        #  from nothing, nothing spent. Without its row the record reads as a forest whose
        #  trees begin nowhere, and a reader taking the next iteration could not tell the
        #  world the search started from apart from one it has never heard of.
        self._note(here)
        return here

    def _projected(self, here, judgment: Want, latest: bool = True):
        """The root of a pass for a want met AT an instant (#619, #625, #643): the present as it
        is PREDICTED to be at the latest start — the instant less the longest landing on the
        root's menu, the latest a plan could begin — where `latest` asks for it: a node of the
        same tree reached by nobody choosing, standing at that instant, so every step's rule
        reads the world holding THEN. Without `latest` the root stands at now, which is the
        pass a want falls back to when the latest start finds nothing on its menu.

        NO DRIFT AND NO AGE: what the world is at an instant is what a package predicted for
        it (the-drift-is-sensings-and-its-result-is-predictions), read off the prediction
        holding then, and a reading's age is inside that prediction already — the trap #619
        opened, a stretch counted from the wrong clock, has nothing left to count.
        """
        lead = 0.0
        if latest:
            longest = 0.0
            for row in self._candidates(here, judgment):
                lands = effects.lands_after(self.imaginarium, row.action, graphs=self._dataset(self._clock, self._world(here)),
                                            **self._bind(judgment, here, row))
                longest = max(longest, lands or 0.0)
            lead = max(0.0, (judgment.holds_at - self._clock).total_seconds() - longest)
        added, retracted = self._predicted(STATE_GRAPH, here, self._clock + timedelta(seconds=lead))
        if not added and not retracted:
            here.landing = lead
            return here
        fork = self.imaginarium.reached(STATE_GRAPH, (_PROJECTED,), added, retracted)
        added = list(added) + self.imaginarium.entailed(fork, added, self._compiled.keys)
        root = _Node(graph=fork)
        root.materialised = True
        root.landing = lead
        root.added, root.retracted = list(added), list(retracted)
        root.diff = signature.advance(signature.EMPTY, signature.facts(added, self._compiled.keys),
                                      signature.facts(retracted, self._compiled.keys), self._base_facts)
        return root

    def _at_root(self, here) -> None:
        """What a pass computes AT its root, for a fresh root and a re-rooted one alike
        (#553): the levers passed over, and the forbidden states the root already stands
        in, which never-newly-enter subtracts."""
        #  THE LEVERS PASSED OVER, asked ONCE per pass at the root rather than at every node,
        #  and written as passed over only where they had a row to pass over: a trace that
        #  named every irrelevant action in the vocabulary would name Move in a plant world
        #  with no disk in it. One query per foreign action per pass is what a truthful
        #  trace costs, against one per node before this.
        self._passed_over = [] if self._compiled.relevant is None else \
            self.agent.afforder.offered(
                self._imagined, graphs=self.imaginarium.graphs_of(*KNOWN, at=self._clock),
                only=frozenset(relevance.actions_of(self.agent.beliefs.reader(PUBLIC)))
                - self._compiled.relevant)
        self._base_forbidden = (self._forbidden_keys(here)
                                if self._compiled.law is not None else frozenset())

    @property
    def _invariant(self) -> str:
        """The invariant half of every world this pass would judge, as skolemized N-Triples,
        written by the store's own engine on the first ask and kept for the pass."""
        if self._invariant_text is None:
            self._invariant_text = crossed_text(
                self.imaginarium.border_text(*self._compiled.invariant_graphs,
                                             *self._compiled.want_graphs))
        return self._invariant_text

    def _border(self, node) -> str:
        """This node's whole world as one N-Triples text, for the judge — which, since #548,
        nothing in the search asks: the parity tests do, holding the compiled selects the
        search reads to the judge's verdict on the same world, and that path stays open at
        no cost to a pass that never takes it.

        The invariant half is every graph a judged world holds that no step can change —
        public knowledge, this agent's beliefs, whatever it records — plus the wants, which
        ride along because `_offer`'s legality check needs them. Written once per pass in
        `_begin`. The variant half is this node's readings, and a concatenation is all that
        separates them because N-Triples lines stand alone.

        WRITING THE VARIANT HALF IS DEFERRED TO HERE, and cached on the node once written. A
        pass forks far more worlds than it judges — 76 against 1 on a 3-disk solve — because
        scoring a want met by a pattern asks the store at `self._graph(node)` and never needs text.
        """
        if node.readings is None:
            node.readings = crossed_text(self.imaginarium.border_text(self._graph(node)))
        return self._invariant + node.readings

    def _step_from(self, node, row, judgment: Want, bound: float | None = None):
        """The node one step on from here, or None where the rule would not run.

        The diff lands in ONE place — the imaginarium graph the next step's rule will read —
        and the node keeps that graph's text for the judge. Asked of the IMAGINARIUM and not of
        the belief base, which is the whole of #254 — a retraction asked of the store finds the
        observation still on disk, so the second dose lands beside the first instead of
        replacing it and is then discarded as a world already seen.
        """
        #  WHEN THIS STEP'S CHANGE COMPLETES, asked BEFORE the effect rather than after it,
        #  so the rule can be told (#588): `orexis:landsAfter` reads the world the act is taken
        #  in, and the construct describes the world it reaches. Both are the same rule's, and
        #  a rule that ignores `$lands` loses nothing, as one ignoring `$via` does.
        #  ASKED AT THE INSTANT THE ACT IS TAKEN (#589): a rule reads the graphs that hold
        #  THEN — a forecast among them, once a world states one — and knows nothing about
        #  which those are. The clock is the pass's, read once at its root.
        taken_at = self._at(node)
        lands = effects.lands_after(self.imaginarium, row.action, graphs=self._dataset(taken_at, self._world(node)), **self._bind(judgment, node, row))
        bind = self._bind(judgment, node, row, lands=lands)
        #  WHAT IT SPENDS, ASKED FIRST — `orexis:costs`, the landing's twin (#466), and None is
        #  free. It is asked before the rule is run because that is what makes the bound worth
        #  having: a candidate already dearer than a plan in hand is dropped without simulating
        #  its effect or forking its world, which are the two expensive things a step does.
        spent = effects.cost_of(self.imaginarium, row.action, graphs=self._dataset(taken_at, self._world(node)), **bind)
        cost = node.cost + (spent or 0.0)
        if bound is not None and cost > bound:
            return TOO_DEAR
        try:
            #  AND THE EFFECT AT THE INSTANT IT LANDS, which is the world the construct
            #  DESCRIBES: a vent opened now but completing after dusk is judged against the
            #  dusk the forecast states, not against this afternoon.
            added, retracted = effects.apply(self.imaginarium, row.action,
                                             graphs=self._dataset(self._at(node, lands), self._world(node)), **bind)
        except Exception as exc:                 # a package's rule is not an agent's problem
            log.error("could not simulate %s: %s", row.action, exc)
            return None
        #  THE ROW BECOMES AN ACT here, where it is sized — the quantity the taker answered is
        #  what the rule just simulated — and the act becomes a STEP once the world it reaches
        #  is scored. An act carries no window yet: nothing in a search knows when.
        act = Step.from_row(row, quantity=bind["litres"] or None)
        path = node.taken + (act,)
        graph = self.imaginarium.reached(self._graph(node), path, added, retracted)
        #  AND WHAT THE WORLD IS PREDICTED TO BE when the step lands (#643): the prediction
        #  holding at that instant stands in for every reading the path did not itself
        #  change — the plan's branch beats the do-nothing branch — and the search computes
        #  no physics. Nothing dries after a step inside a pass: what the world does from the
        #  step's band is predicted once the plan is adopted, by the package, from there.
        own_added, own_retracted = list(added), list(retracted)
        changed = node.changed | self._places(own_added, own_retracted)
        added, retracted = self._predicted(graph, node, self._at(node, lands), added, retracted,
                                           apply=True, changed=changed)
        #  WHAT THE PREDICTED READING IS (#576): the bands the domain's entailment asserts on
        #  the node the rule added, asked of the forked world and carried in the diff beside
        #  the number, so a kept world and a step's prediction say the reading's class too.
        entailed = self.imaginarium.entailed(graph, added, self._compiled.keys)
        added = list(added) + entailed
        keys = self._compiled.keys
        adds, retracts = signature.facts(added, keys), signature.facts(retracted, keys)
        diff = signature.advance(node.diff, adds, retracts, self._base_facts)
        #  WHAT THE STEP ITSELF PREDICTED, apart from what the world is predicted to do around
        #  it (#643): the keeper holds a step to its own effect, and a prediction the overlay
        #  stood in for another reading is the package's promise, not this step's.
        own_subjects = {t.subject for t in own_added}
        own = (signature.facts(own_added + [t for t in entailed if t.subject in own_subjects], keys),
               signature.facts(own_retracted, self._compiled.keys))
        #  When this path's last change completes: the step's own `orexis:landsAfter`, asked
        #  above exactly as the keeper asks it, summed along the path (#472). None — no stated
        #  timing — adds nothing, which is the keeper's own contract for it.
        landing = node.landing + (lands or 0.0)
        #  A STEP IS A CHOSEN EDGE, so it stands on whatever its parent stands on: taking a
        #  lever does not change which of the world's own branches you are in. Extending a
        #  ground is a HAPPENING edge's to do, and nothing draws one yet (#589).
        step = _Node(graph=graph, diff=diff, landing=landing, cost=cost, ground=node.ground,
                     origin=node.origin if node.origin is not None else row.action,
                     parent=node, added=list(added), retracted=list(retracted), changed=changed)
        step.urgency = self._urgency_in(step, judgment)
        step.estimate = self._estimate_in(step, judgment)
        #  THE STEP CARRIES WHAT IT PREDICTED (#510): the same canonical facts the signature
        #  is made of, so the keeper can hold the world to this step without an imaginarium.
        step.taken = node.taken + (replace(act, urgency_after=step.urgency, predicts=own),)
        return step

    def _open_row(self, node, standing: bool) -> None:
        """Say in the store whether this world is on the frontier, or take it back.

        OPEN IS NOT MERELY UNEXPANDED. A world settled with a verdict — met, refused, too dear
        — is never put on the frontier at all, so its absence has to be said rather than
        inferred from what has been opened.
        """
        if self.imaginarium is None:
            return
        quad = [ox.Quad(ox.NamedNode(node.graph), ox.NamedNode(DELIBERATION + "open"),
                        ox.Literal("true", datatype=ox.NamedNode(XSD + "boolean")),
                        ox.NamedNode(PASS_GRAPH))]
        (self.imaginarium.note if standing else self.imaginarium.unnote)(quad)

    def _next_open(self, met_now: bool):
        """The world to open next, ASKED OF THE STORE rather than popped off a heap.

        `_priority` is `(spent + remaining, urgency, spent)` for an unmet want and depth alone
        for a met one, and those are exactly the columns a world's row carries — so the open
        list IS this `ORDER BY`, and an iteration needs nothing carried over from the last one
        but the name it gets back.

        MEASURED BEFORE IT REPLACED THE HEAP, and the microbenchmark was the wrong number:
        one query is 249 us against a heappop's 0.5, which is 544x and says nothing, because a
        pass pops about as many times as it keeps worlds worth opening — 6 on the two-disk
        puzzle, 22 on a courier delivery that keeps 79 worlds. Against the whole pass,
        alternated within one session since this bench drifts twofold between invocations and
        holding the same choice made in Python as the other side: +3.2% on the courier, same
        plan both ways. Forking and reading are what a search spends its time on.
        """
        #  AND THE TIE-BREAK IS ARRIVAL, which is what the heap's mint counter was. Not
        #  decoration: a want declaring no estimate scores every world alike, so the tie-break
        #  IS the order, and arrival is what makes the search go layer by layer rather than
        #  diving. Broken by the world's name instead, a greenhouse pass went alphabetically
        #  into Dosing and spent its whole budget without weighing the branch it needed.
        order = ("?depth" if met_now else "(?spent + ?left) ?urgency ?spent") + " ?minted"
        rows = bindings(self.imaginarium.query_over(f"""
SELECT ?w WHERE {{ ?w a deliberation:PossibleWorld ; deliberation:open true ;
    deliberation:spent ?spent ; deliberation:remaining ?left ;
    deliberation:wouldReach ?urgency ; deliberation:atDepth ?depth ;
    deliberation:minted ?minted . }}
ORDER BY {order} LIMIT 1""", PASS_GRAPH))
        return self._by_name.get(rows[0]["w"]) if rows else None

    def _keep(self, node) -> None:
        """A forked world becomes a NODE of the cone — and says so in the store.

        Not every fork does. One already reached more cheaply, or dearer than a plan in hand,
        is weighed and let go; a row for one of those would be handed to a reader asking what
        is still open, which is a place to search from the search itself refused. So the rows
        say what `_nodes` says, and `_renote` can rebuild them from it after a re-root.
        """
        self._nodes.append(node)
        self._note(node)

    def _note(self, node) -> None:
        """Say in the STORE what this pass knows about the world it just made.

        What the search knew about a world was a Python object: its parent, what the path had
        spent, what the want read there, how far the want still was, whether it had been
        opened. None of it was anywhere a query could reach, so a pass could not be stopped
        and resumed from the store, and the frontier could not be asked for — which is the
        whole of why the open list is a heap here and not an `ORDER BY`.

        BESIDE THE WORLDS AND NOT IN THEM: a row is ABOUT a world, and a world's graph holds
        that node's own readings and nothing else. Written into the imaginarium, which dies
        with the pass, as these rows should — a world that no longer exists is not a frontier.

        THE STEP IS THE LEDGER'S OWN WORDS, as a plan's is: `progression:Step`,
        `progression:fills`, `progression:through`. One vocabulary for a planned step, wherever
        it is written down.

        WRITTEN AND NOT YET READ. The search still keeps its own nodes and its own heap; these
        rows say the same thing where a query can reach it, and `test_expansions` holds the two
        to each other. One thing must be settled before the loop reads them instead: a
        re-rooted cone drops nodes and does not yet drop their rows, so a store-driven frontier
        would offer worlds that are gone.

        MEASURED, alternated within one session because this bench drifts twofold between
        invocations: 1.9% of the two-disk pass, fourteen forks. It was 38.6% written as
        `INSERT DATA` — two SPARQL texts parsed per fork, where the writing itself is nothing,
        which is why `Imaginarium.note` takes quads. The cost is per FORK, so it scales with
        how wide a search goes rather than with how long it runs.
        """
        #  AND THE WAY BACK. A row names a world and the search still holds nodes, so
        #  something must turn the one into the other; the index is kept where the row is
        #  written, so a world the store names is a world the search can find.
        self._by_name[node.graph] = node
        if self.imaginarium is None:
            return
        self.imaginarium.note(self._rows_for(node, self._minted))
        self._minted += 1

    def _rows_for(self, node, minted: int) -> list:
        """One world's row, as quads — what `_note` writes and what `_renote` rebuilds the
        whole account from after a re-root.

        WHERE IT CAME FROM AND WHAT IT TOOK are read off the node rather than handed in, so
        the two writers cannot derive them differently: the parent's graph is its NAME and not
        `self._graph(node.parent)`, which would MATERIALISE the world — a fork per row, for a
        string. A step's own duration is the difference of two landings, which survives a
        re-root because both halves are re-based by the same amount.
        """
        parent = None if node.parent is None else node.parent.graph
        act = node.taken[-1] if node.taken else None
        lands = None if node.parent is None else (node.landing - node.parent.landing)
        D, P = DELIBERATION, PROGRESSION
        me, g = ox.NamedNode(node.graph), ox.NamedNode(PASS_GRAPH)
        def q(s_, p_, o_):
            return ox.Quad(s_, ox.NamedNode(p_), o_, g)
        def dec(v):
            return ox.Literal(f"{v:.6f}", datatype=ox.NamedNode(XSD + "decimal"))
        out = [q(me, RDF_TYPE, ox.NamedNode(D + "PossibleWorld")),
               q(me, D + "spent", dec(node.cost)),
               q(me, D + "remaining", dec(node.estimate or 0.0)),
               q(me, D + "wouldReach", dec(node.urgency)),
               q(me, D + "takes", dec(node.landing)),
               q(me, D + "atDepth", ox.Literal(str(len(node.taken)),
                                               datatype=ox.NamedNode(XSD + "integer"))),
               q(me, D + "signature", ox.Literal(_signature_of(node))),
               #  WHEN THIS WORLD WAS MADE, and it is not decoration: it is the tie-break the
               #  heap kept as its mint counter, and it is load-bearing. A pass whose want
               #  declares no estimate scores every world alike — same spent, same remaining,
               #  same urgency — so the tie-break IS the order, and arrival order is what
               #  makes the search go layer by layer. Ordered by the world's NAME instead, a
               #  greenhouse pass dived alphabetically into Dosing and spent all 128 worlds of
               #  its budget without ever weighing the Heating branch the plan needed.
               q(me, D + "minted", ox.Literal(str(minted),
                                              datatype=ox.NamedNode(XSD + "integer"))),
               #  WHEN this world is, written and not derived: the engine binds nothing for
               #  duration arithmetic, so no query can add a path's seconds to the pass's
               #  clock. The root's instant is that clock, which is how it reaches the store.
               q(me, D + "atInstant", ox.Literal(self._at(node).isoformat(),
                                                 datatype=ox.NamedNode(XSD + "dateTime")))]
        #  THE ROOT HAS NO PARENT AND NO STEP: it is where the pass stands, reached by nothing.
        if parent is not None:
            out.append(q(me, D + "from", ox.NamedNode(parent)))
        if act is not None:
            step = ox.NamedNode(node.graph + ".step")
            out += [q(me, P + "by", step),
                    q(step, RDF_TYPE, ox.NamedNode(P + "Step")),
                    q(step, P + "fills", ox.NamedNode(act.action))]
            #  HOW LONG THE ACTION ITSELF TAKES — the step's own `orexis:landsAfter`, asked in
            #  the world it is taken in. The world's `takes` is the path's total, so a step's
            #  own would be a subtraction, and a duration this pass computed once is worth
            #  keeping where the step that has it is written down.
            if lands:
                out.append(q(step, D + "takes", dec(lands)))
            if act.via:
                out.append(q(step, P + "through", ox.NamedNode(act.via)))
            if act.about:
                out.append(q(step, OREXIS + "about", ox.NamedNode(act.about)))
            if act.quantity is not None:
                out.append(q(step, P + "quantity", dec(act.quantity)))
        if node.expanded:
            out.append(q(me, D + "expanded", ox.Literal("true", datatype=ox.NamedNode(XSD + "boolean"))))
        return out

    def _renote(self) -> None:
        """Say the whole pass again, after a re-root has changed what is true of every node.

        A re-root keeps the subtree under the matched world and DROPS the rest, then re-bases
        what it kept: new depths, new costs, new landings, a new clock, and a new root that
        stands nowhere. Every number in every row moves, and rows for the dropped worlds must
        go — a store-driven frontier reading a stale one would offer somewhere to search from
        that no longer exists.

        `node.graph` and not `self._graph(node)`: the name is what a row says, and asking for
        the graph MATERIALISES the world, which is a fork per kept node for nothing.
        """
        if self.imaginarium is None:
            return
        out: list = []
        self._by_name = {m.graph: m for m in self._nodes}
        #  ARRIVAL ORDER SURVIVES A RE-ROOT: `_nodes` is in the order the worlds were made, so
        #  re-numbering by that order keeps the tie-break saying what it said.
        for n, m in enumerate(self._nodes):
            out += self._rows_for(m, n)
            if m in self._pending:
                out += [ox.Quad(ox.NamedNode(m.graph), ox.NamedNode(DELIBERATION + "open"),
                                ox.Literal("true", datatype=ox.NamedNode(XSD + "boolean")),
                                ox.NamedNode(PASS_GRAPH))]
        self._minted = len(self._nodes)
        self.imaginarium.note(out, whole=True)

    def _opened(self, node) -> None:
        """Mark a world expanded — its levers tried, its children forked. The ABSENCE of this
        is what makes a world part of the frontier, so a query for the open list is a
        `FILTER NOT EXISTS` over these rows."""
        if self.imaginarium is not None:
            self.imaginarium.note([ox.Quad(
                ox.NamedNode(self._graph(node)), ox.NamedNode(DELIBERATION + "expanded"),
                ox.Literal("true", datatype=ox.NamedNode(XSD + "boolean")),
                ox.NamedNode(PASS_GRAPH))])

    def _predicted(self, graph: str, node, instant, added=(), retracted=(), apply: bool = False,
                   changed: frozenset | None = None):
        """The step's diff, plus what the world is PREDICTED to be at `instant` (#643,
        the-drift-is-sensings-and-its-result-is-predictions): for every reading a prediction
        holding then carries, the predicted node in place of the one this world holds — EXCEPT
        a PLACE the path itself changed, since the plan's branch beats the do-nothing branch.
        A place is what the signature says it is — a keyed node's class and key, any other
        subject — so a look, which re-stamps the reading it finds and nets to nothing, changes
        none and the prediction stands in for what it looked at, while a dose or a purchase
        changes its key whichever node it minted. The overlay fills the slot the drift filled
        at every fork, so the node's signature, the ground and the cone are untouched, and the
        search runs no rule that knows a rate.
        """
        beliefs = self.agent.beliefs
        holding = beliefs.graphs_of(PREDICTION, at=instant)
        if not holding:
            return list(added), list(retracted)
        if changed is None:
            changed = node.changed | self._places(added, retracted)
        more, gone = [], []
        for prediction in holding:
            for subject, triples in beliefs.nodes_of(prediction).items():
                if self._place_of(subject, triples) in changed:
                    continue
                #  THE WHOLE NODE IT REPLACES, type and key included — a retraction is
                #  canonicalised like an addition, and a reading retracted without its type is
                #  two plain triples that cancel nothing (#619).
                gone += self.imaginarium.node_of(graph, subject)
                more += triples
        if not more:
            return list(added), list(retracted)
        if apply:
            self.imaginarium.amend(graph, more, gone)
        dropped = set(gone)
        added = [x for x in added if x not in dropped] + more
        return added, list(retracted) + gone

    def _places(self, added, retracted) -> frozenset:
        """The places a diff CHANGES, read off its canonical facts: a keyed node's (class,
        key), any other fact's subject. Additions and retractions that cancel — a look's —
        change no place."""
        keys = self._compiled.keys
        net = signature.facts(added, keys) ^ signature.facts(retracted, keys)
        return frozenset(f[1:3] if f[0] == "keyed" else f[0] for f in net)

    def _place_of(self, subject, triples):
        """Where a predicted node stands, in the signature's words: its (class, key) where it
        is keyed, its own term otherwise — and None for a blank node nobody keys."""
        for f in signature.facts(triples, self._compiled.keys):
            if f[0] == "keyed":
                return f[1:3]
        return signature.named(subject)

    def _world(self, node) -> str:
        """The readings a rule asked about this node reads — its own, and the pass's root where
        there is no node (#666). Handed to the door; no rule text names it."""
        return self._graph(node) if node is not None else STATE_GRAPH

    def _bind(self, judgment: Want | None, node=None, row=None, litres: float | None = None,
              lands: float | None = None) -> dict:
        """What a rule needs filled in to answer about THIS agent and THIS want, HERE.

        `bound` is what the cheapest plan found so far spends, or None while none has been.
        BRANCH AND BOUND, and it changes which candidates are looked at rather than which plan
        wins: `orexis:costs` is never negative and a path sums it, so a candidate already
        dearer than a plan in hand can only grow dearer — no descendant of it can beat the
        bound. Measured on a 3-disk solve, the first achiever lands at node 48 of 76.

        STRICTLY dearer, and the strictness is load-bearing. An action that declares no cost is
        FREE, so a descendant may cost exactly what its parent did — and an achiever tying on
        cost still wins on urgency, the tie-break `min` applies among achievers. Pruning at
        `>=` would throw away a plan that ties on money and is nearer the aim.

        `node` is where the step is being taken FROM, and passing it is what makes depth 2
        more than a number. It carries BOTH halves of that, and the second is #254: the value
        the rule predicts from, read out of the node's flat world, and `$state` — the graph in
        the imaginarium holding the readings this node's path reached, which is what the
        retraction half of the rule asks about. Bound to the agent's own sensed graph, as it was
        before, the retraction found the observation still on disk and predicted a reading that
        landed BESIDE the previous step's instead of replacing it.

        Bound from the judgment alone — which is how this was first written —
        every step is predicted from the reading the agent actually holds, so a second dose
        computes `0.04 + 0.21/conversion` exactly as the first did, lands on the world the
        first one reached, and is discarded by cycle detection as somewhere already seen.
        The loop iterated twice and the search was depth 1, silently, for every means that
        moves a measured property. Measured before it was fixed: value 0.04 at depth 0, the
        world at 0.18 after one step, and `_bind` still saying 0.04.

        The DOSE moves with it for the same reason and by the same path: `dose_for` sizes an
        act from where the property stands, so a second dose asked about the world the first
        one reached is the act the actor would actually take next — which is the whole of what
        makes "too small to finish in one" a plannable situation rather than an unreachable one.
        """
        #  VALUES, NOT TEXT (#500): each is the IRI, the number or the literal it is, and
        #  `store.bind` renders it as the term where the rule's `$token` stands — whole token,
        #  never a prefix of a longer one, and a token nobody bound refuses.
        return {
            "me": self.me.uri,
            "subject": self.me.acts_for if self.me.acts_for else "urn:nobody",
            #  THE WANT AND WHAT IT IS ABOUT, carried from the row to the rule and never read
            #  here: `$about` is whatever the want's deriver said (`orexis:about`) — a property,
            #  for a region want — and the rule joins on it in its own words.
            "want": judgment.uri if judgment else "urn:nothing",
            "about": row.about if row is not None and row.about else "urn:nothing",
            #  THE LEVER, since the sovereign struck hanoi's ground-action grid: a row always
            #  carried which lever a step goes through, and the effect could never see it —
            #  so a two-parameter action was inexpressible and hanoi shipped six ground
            #  nodes. One schema needs the channel: $via is the row's lever, symmetric with
            #  $about, and a rule that ignores it loses nothing.
            "via": row.via if row is not None else "urn:nothing",
            "picks": self.agent.beliefs.graph,
            #  NOT SIZED (#579). The search plans on what a reading IS, and an effect declares
            #  the band it reaches; how much to pour or bid is progression's, computed from
            #  the reading in hand when the step is taken. The token stays bound at nothing
            #  for the timing and cost selects that still carry it, which then say nothing —
            #  a landing of zero, a cost unstated — and a caller walking a plan back may pass
            #  the quantity a step was taken with.
            "litres": litres if litres is not None else 0.0,
            #  WHEN THIS STEP'S CHANGE COMPLETES (#588), as the instant it is: this node's own
            #  instant — the pass's clock plus the path's landings — plus what this act's own
            #  `orexis:landsAfter` adds. A construct describes the world its act REACHES, so
            #  a reading it predicts exists then and is stamped then, rather than at the
            #  moment the plan happened to be made.
            #
            #  NOT the instant the act is TAKEN, which is a second thing and not bound here.
            #  The market proves they are two: a bid's own premise is that the round is still
            #  open, which is true when the bid is placed and false by the time the water
            #  arrives, since the bid's landing is the window PLUS the pour. A WHERE asking
            #  `NOW()` therefore still asks the real clock, and that is the seam.
            "lands": Raw(f'"{self._at(node, lands).isoformat()}"^^xsd:dateTime'),
        }

    def _at(self, node, lands: float | None = None) -> datetime:
        """The instant a node stands at, or the instant a step taken from it completes.

        The pass's clock plus the path's summed `orexis:landsAfter`. The clock is read ONCE,
        at the root, and never inside the search: a pass that read a wall clock per fork would
        describe two worlds differently for having taken longer to imagine them. It is not
        part of where a node IS — that is its facts and its ground (#587) — it is what a rule
        is told when it asks what time its own step happens at.
        """
        base = node.landing if node is not None else 0.0
        return self._clock + timedelta(seconds=base + (lands or 0.0))

    def _beliefs(self):
        """The DATA-BORNE world as an rdflib graph — what the pass carves shapes from.

        Everything this agent owns, asked (#444). The instruments are why completeness
        matters: a freshness want's met-test reads the horizon this agent published, and a
        shape whose pattern reaches a graph nobody copied does not fail — it finds nothing,
        reports nothing, and the want reads as met for ever. The debts are why it must
        include the received ones (#255): an obligation's met-test is a pattern over the
        record, and the world Apply's effect discharges an obligation in must hold it to
        discharge.

        WITHOUT THE T-BOX, EXCEPT ITS SHAPES (#484). What is carved from this graph is
        shapes — the law a plan may not pass through, a want's avoided state, a met-shape
        and its root — and a law is ratified, arriving as data in the world or the desires;
        but a PACKAGE may declare a want's shape beside its actions (the courier's
        `delivered`, hanoi's `solved`), and that lives in the vocabulary. So the two
        ontology graphs — 82% of the flatten, 2,312 of 2,828 triples and 253 ms of every
        pass on `world/simulation` — contribute their node shapes and nothing else: the
        shape, and what hangs off it through blank nodes. `tests/test_planning.py` holds a
        vocabulary to carrying no LAW, since a law there would be carved from a subgraph
        that keeps no severity it does not state. Asked by what a graph IS, never by name.
        """
        store = self.agent.beliefs
        vocabulary = {r["g"] for r in bindings(store.query(
            "SELECT ?g WHERE { ?g a orexis:OntologyGraph }", store.graphs_of(PUBLIC)))}
        base = graph_from(store, *(g for g in store.graphs_of(*KNOWN, at=self._clock) if g not in vocabulary))
        #  The vocabulary's shapes, as subgraphs: every triple of a node shape, and of every
        #  blank node reachable from it — a property shape, a qualified value shape, a list.
        #  The path walks through IRIs too, and the filter keeps only what is the shape's
        #  own, so a class an `sh:class` names is not dragged in with its whole axiom set.
        for triple in effects.applied((), store.construct("""
CONSTRUCT { ?x ?p ?o } WHERE {
  ?g a orexis:OntologyGraph .
  GRAPH ?g { ?s a sh:NodeShape . ?s (!<urn:none>)* ?x . ?x ?p ?o }
  FILTER(?x = ?s || isBlank(?x)) }""", store.graphs_of(PUBLIC)), ()):
            base.add(triple)
        return base


_AG_IRI = "http://example.org/orexis#"


@dataclass
class PlanningBeliefs:
    """What the sovereign said about this agent's thinking: how many worlds a pass may fork."""

    budget_worlds: int


#  Read the way the keeper's patience is (`KEEPING_PICKS`), with the one difference that this
#  block may be wholly absent: `read_optional`, and the engine's ceiling stands in.
PLANNING_PICKS = Picks(
    capability=DELIBERATION + "Deliberation",
    cls=PlanningBeliefs,
    terms={"budget_worlds": DELIBERATION + "budgetWorlds"},
)


def _priority(node, met_now: bool) -> tuple:
    """Where this world goes in the open list, lower first.

    FOR AN UNMET WANT, what the path has spent plus what the want says is left — `cost +
    estimate`, the A* key — so the search walks the estimate's gradient to an achiever early
    and the bound that achiever sets refuses the rest. Urgency breaks the tie, then cost
    alone: among worlds equally promising in the wallet's unit, the one nearer by the want's
    own measure is looked under first. Neither decides the winner — that is still `min` over
    the achievers by (cost, urgency), and `best` over every novel world — only how much is
    visited before the bound starts refusing work. A want declaring no estimate reads 0.0
    here, which makes the key plain cost: uniform-cost search, and the bound then refuses
    exactly what it refused before this ordering existed.

    FOR A MET WANT, depth then arrival — insertion order, layer by layer, which is exactly
    the order the layer loop expanded in. A met want returns on the FIRST novel step that
    keeps it met, deliberately: re-picking among keepers would be shopping for a want that is
    not shopping for anything. So the order there IS the answer, and a heap that reordered
    it would change which keeper a calm agent steers by, for no gain — a met pass has no
    achiever to bound against.
    """
    if met_now:
        return (len(node.taken),)
    return (node.cost + _near(node), node.urgency, node.cost)


def _said(diff: tuple) -> str:
    """A projected diff as one line a person can read: what the present holds beyond every
    imagined world and what it lacks, terms shortened."""
    def short(f):
        if f[0] == "keyed":
            key = ",".join(str(v).rsplit("#", 1)[-1].rsplit("/", 1)[-1] for _, v in f[2])
            return f"{key}={f[4]}"
        return " ".join(str(t).rsplit("#", 1)[-1].rsplit("/", 1)[-1] for t in f)
    plus, minus = diff
    return "+[" + "; ".join(sorted(map(short, plus))) + "] -[" + "; ".join(sorted(map(short, minus))) + "]"


def _near(node) -> float:
    """A node's declared distance from its want, or 0.0 where the want declares none.

    Zero rather than infinity, and the choice is what keeps a want with no estimate behaving
    exactly as it did before this term existed: every world reads equally far, so the
    comparisons that use it fall back on urgency and cost alone.
    """
    return node.estimate if node.estimate is not None else 0.0


#  What `_step_from` hands back for a candidate that cannot beat the plan already in hand.
#  Distinct from None, which means the rule would not run: one is a defect worth reporting and
#  the other is the search declining work it has proved it does not need.
TOO_DEAR = object()

#  A row that is on no menu, so the imaginarium can name the world it reaches (#619): the
#  present projected to an instant-bound want's start. A node's world AT the instant is named
#  by the node's own graph, in `_judged_at`.
_PROJECTED = Step(action="urn:orexis:projected", via="")

_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_AG = rdflib.Namespace(_AG_IRI)
#  No means or family is named here any more: sizing is `Module.size`, asked of the row's
#  taker by the action's own contribution exactly as execution finds it.
