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

from datetime import datetime, timezone

import heapq
import logging
import time
from dataclasses import dataclass, field

import rdflib
from rdflib import RDF, URIRef

from . import effects, relevance, signature, trace, violation
from .beliefs import Picks
from orexis_agent_progression.act import Act, Step
from orexis_agent_deliberation.desire import Desire
from .afforder import affordances_of, wants_of
from .imaginarium import Imaginarium
from orexis_agent_progression.store import Raw, bind, bindings
from orexis_agent_progression.ontology import (DESIRE_ASSERTED_GRAPH, DESIRE_DERIVED_GRAPH,
                            STATE_GRAPH, beliefs_graph)
from orexis_agent_deliberation.conformance import conforms, graph_from
from orexis_agent_deliberation.judge import judge

log = logging.getLogger("search")

#  Why a pass ended, and they are not interchangeable. The two failures in particular: NOTHING
#  proposed anything (equip me), against EXHAUSTED, where levers exist and no bounded sequence
#  of them lands inside the region (my doses are too coarse, or my region is too tight for them).
SATISFIED = "satisfied"      # a world where the desire is met
IMPROVED = "improved"        # not met, but nearer than doing nothing
NOTHING = "no candidate"     # no lever this agent holds points at this want
EXHAUSTED = "exhausted"      # levers exist; none reaches the desire within the budget allowed
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

    The world is held ONCE, in the imaginarium, and `graph` names it — what the next step's
    rule reads and where its `$state` points. `readings` is that same graph as N-Triples text,
    written by the store's own engine, because the judge takes text at the border.

    It used to be held TWICE: the imaginarium graph AND the whole world flattened into an
    rdflib graph per node, which was 198,144 `Graph.add` calls and fifty-five percent of a
    hanoi solve — a full copy of a 2,300-triple world to express a step that changed four
    triples. The flat copy existed because pySHACL read rdflib; nothing does now (#481). What
    is left per node is the node's OWN readings, which is what actually differs: everything
    else a judged world holds is the same for every node in the pass and is written once, in
    `_begin`. See knowledge/runbooks/measure-the-search.md.
    """

    #  This node's graph as N-Triples, or None until somebody asks. LAZY since the measure
    #  that named it: a 3-disk solve forks 76 worlds and READS one — only a judged world needs
    #  text, and a want met by a pattern is judged by the store's own engine at `graph`, so
    #  most worlds are scored, weighed and discarded without ever being written out.
    readings: str | None = None
    graph: str = STATE_GRAPH                     # this node's readings, in the imaginarium
    taken: tuple = field(default_factory=tuple)   # the STEPS taken to get here, in order
    urgency: float = 1.0
    #  The net diff against the base world, in canonical facts — where this node IS, for cycle
    #  detection. The root stands nowhere but the world itself, so its diff is empty.
    diff: tuple = signature.EMPTY
    #  Seconds after commitment this path's LAST world-change completes — each step's own
    #  `orexis:landsAfter`, summed, for holding a candidate to a Within want's room (#472).
    #  The root has taken nothing and lands immediately.
    landing: float = 0.0
    #  What this world still owes the want, by the want's own declaration (`orexis:estimates`),
    #  or None where it declares none. Never compared across desires — only between worlds of
    #  one pass, which is the only comparison it means anything for.
    estimate: float | None = None
    #  What this path SPENDS, in the wallet's unit — each step's own `orexis:costs`, summed
    #  (#466). Free is the reading of an action that declares none.
    cost: float = 0.0


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
        #  The sovereign's pick, read the way every pick is — from the desire modality's copy,
        #  since the search is what reads a belief and nothing beneath it does — or the engine's
        #  own ceiling where the agent's beliefs say nothing. Optional on purpose, unlike the
        #  patience: `orexis:BudgetShape` bounds a stated one and demands none.
        picks = self.agent.desires.read_optional(PLANNING_PICKS)
        self.budget = picks.budget_worlds if picks is not None else self.BUDGET
        #  Alive only during a pass. Between passes there is no imaginarium, which is the point:
        #  a hypothesis explored against a world that has moved is not a hypothesis, so the
        #  snapshot is per plan and nothing carries over.
        self.imaginarium = None

    # --- what a world is worth ---------------------------------------------------------------

    def _urgency_in(self, node, desire: Desire) -> float:
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

        The NODE is what arrives, and its graph is the whole of what a measure needs: the flat
        rdflib copy this took alongside was only ever read by the wants that state no measure —
        an obligation, met-or-not over the record — and those ask the imaginarium now too (#481).
        Anything else unmeasured scores 1.0, the not-knowing answer.
        """
        answer = self.agent.desire_urgency(desire, self.imaginarium.query, node.graph)
        if answer is not None:
            return answer
        #  An avoided-pattern want is binary by its own contract — met 0, unmet 1 — and the
        #  kernel judges it (#468): no capability answers for pure ratified data, and the
        #  flat not-knowing fallback below would send the search shopping for a want that
        #  wants nothing whenever the pattern is held.
        pattern = self._avoided_pattern(desire)
        if pattern is not None:
            return 1.0 if self._pattern_binds(pattern, node.graph) else 0.0
        if self._unmet is not None:
            #  A compiled want nobody measures — the puzzles', an aversion authored as a
            #  shape — is binary by the same contract as a pattern want: unmet 1, met 0.
            #  Without this the not-knowing fallback below scored the delivered world 1.0
            #  beside the undelivered one, and only the met-test could tell them apart.
            return 0.0 if self._met_in(node, desire) else 1.0
        if desire.is_obligation:                        # met-or-not over the record
            return 0.0 if self._met_in(node, desire) else 1.0
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

    def _met_in(self, node, desire: Desire) -> bool:
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
        #  A WANT MET BY ABSENCE (#468): `orexis:unmetWhen` points at the avoided pattern,
        #  and met is the pattern binding nothing — one text, the store's own engine, judged
        #  against this node's own readings, so the flat/named-graph split a met-shape would
        #  force never opens.
        pattern = self._avoided_pattern(desire)
        if pattern is not None:
            return not self._pattern_binds(pattern, node.graph)
        if self._unmet is not None:
            #  A SHAPE-AUTHORED WANT, judged by its compiled violation select (#497): the
            #  shape is positive and universal, the select is its negation as rows, the
            #  kernel compiled it once in `_begin`, and the store's own engine runs it at
            #  this node's world — public knowledge, the records, and this node's readings
            #  as the default graph, the same view the judge was handed as one flat text.
            #  About a millisecond where the judge's reader floors at tens; held to the judge
            #  by parity in tests/test_violation.py.
            return not bindings(self.imaginarium.query_over(
                self._unmet, *self._invariant_graphs, node.graph))
        shape = self._shape_of(desire)
        if shape is None:
            #  A obligation's goal state is a PATTERN over the record, not a distance (#255): this
            #  claim discharged, in whatever world is being judged — which is what lets a
            #  possible world where Apply ran count as satisfying, and the world in hand not.
            if desire.is_obligation:
                return self._holds(node, desire.uri, str(_AG.dischargedAt))
            #  A want with no shape and no property — a CALL (#359) — is met exactly where
            #  whoever measures it says it is: zero urgency in the world being judged. Asked
            #  of the imaginarium at the node's graph, as `_urgency_in` asks.
            answer = self.agent.desire_urgency(desire, self.imaginarium.query, node.graph)
            if answer is not None:
                return answer <= 0.0
            return desire.is_met
        results, _ = judge(self._border(node), shape)
        return not list(results.subjects(RDF.type, _SH.ValidationResult))

    def _holds(self, node, subject: str, predicate: str) -> bool:
        """Whether this node's world states anything about `subject` under `predicate`.

        A membership test the flat world used to answer with `in`, asked of the imaginarium
        instead (#481). SCOPED, and that is the whole care of it: an unscoped `GRAPH ?g` would
        read every SIBLING world in the store too, so the graphs are named — this node's
        readings and the invariant ones, which is exactly what `_border` writes.
        """
        graphs = " ".join(f"<{iri}>" for iri in self._invariant_graphs + (node.graph,))
        return bool(bindings(self.imaginarium.query(
            f"SELECT ?x WHERE {{ VALUES ?g {{ {graphs} }} "
            f"GRAPH ?g {{ <{subject}> <{predicate}> ?x }} }} LIMIT 1")))

    def _estimate_in(self, node, desire: Desire) -> float | None:
        """How far this world still is from meeting the want, by the want's own declaration.

        The desire's term and the action's twin: `orexis:costs` says what a step spends,
        `orexis:estimates` says what is left to spend. Both are SELECTs the domain writes and
        the kernel runs, so a knowledge-only package can state one — which is the whole point,
        since the two domains that need this most carry no Python at all.

        None where the want declares none, and None where the select refuses to run: a want
        with no estimate is not a want that is zero away, and treating a broken declaration as
        "arrived" would crown a plan that achieved nothing.
        """
        node_uri = self._shapes.value(URIRef(desire.uri), _AG.estimates)
        if node_uri is None:
            return None
        text = self._select_of(node_uri)
        if text is None:
            return None
        try:
            rows = bindings(self.imaginarium.query(
                bind(str(text), this=self.me.uri, state=node.graph)))
        except Exception as exc:
            log.error("estimate failed to run for %s: %s", desire.uri, exc)
            return None
        return float(rows[0]["estimate"]) if rows and "estimate" in rows[0] else None

    def _avoided_pattern(self, desire: Desire) -> str | None:
        """The `orexis:unmetWhen` select this want carries, or None — the negative twin."""
        node = self._shapes.value(URIRef(desire.uri), _AG.unmetWhen)
        if node is None:
            return None
        #  A node that is a SHAPE carries no select of its own: it was compiled in `_begin`
        #  (#499) and `self._unmet` answers for it.
        if (node, RDF.type, _SH.NodeShape) in self._shapes or \
                (node, RDF.type, _SH.NodeShape) in self._base:
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
        rebuild, so it cannot answer for a package's node. One text, either road, and the
        same substitution after.
        """
        text = self._shapes.value(node, _SH.select)
        if text is not None:
            return str(text)
        rows = bindings(self.agent.beliefs.query(
            f"SELECT ?text WHERE {{ <{node}> <{_SH.select}> ?text }} LIMIT 1"))
        return str(rows[0]["text"]) if rows and rows[0].get("text") else None

    def _pattern_binds(self, text: str, graph: str) -> bool:
        """Whether the avoided pattern binds in the world at `graph` — rows mean entered.

        The same substitution a measure gets, run on the imaginarium so a candidate world
        answers exactly as the live one does. A pattern that fails to run reads as ENTERED:
        a select the gates admitted and the engine refuses is a defect someone must see,
        and a want stuck hot is how this architecture says so.
        """
        try:
            text = bind(text, this=self.me.uri, state=graph)
            return bool(bindings(self.imaginarium.query(text)))
        except Exception as exc:
            log.error("avoided-state pattern failed to run: %s", exc)
            return True

    def _shape_of(self, desire: Desire):
        """The desire's shape, with everything hanging off it, or None if it has none.

        Asked of the DESIRE MODALITY, not of the world being judged (#298): what is pursued
        and what is are different stores now, and validation was always two graphs — the
        world is the data, the shape is the question. It took a `world` argument it never
        read, for years, as a note that the met-check is about one; the shapes snapshot is per
        pass (`_begin`), so a rebuild mid-search cannot hand two depths two different wants.
        """
        root = self._shape_root(desire)
        if root is None:
            return None
        #  THE PACKAGE OWNS THE MEASURE: a world's asserted want may point at a shape the
        #  domain package declares — public knowledge, in the flat base this pass built,
        #  and not in the wants snapshot — so the carve is asked of whichever holds it.
        source = self._shapes if (root, RDF.type, _SH.NodeShape) in self._shapes else self._base
        return source.cbd(root)

    def _relevant_actions(self, desire: Desire, shape) -> frozenset | None:
        """The actions relevant to this want, or None for all of them — see `relevance.py`."""
        if shape is not None:
            reads = relevance.reads_of_shape(shape, self._shape_root(desire))
        else:
            avoided = self._shapes.value(URIRef(desire.uri), _AG.unmetWhen)
            pattern = self._avoided_pattern(desire) if avoided is not None else None
            if pattern is not None:
                reads = relevance.reads_of_select(pattern)
            elif avoided is not None and self._unmet is not None:
                source = (self._shapes if (avoided, RDF.type, _SH.NodeShape) in self._shapes
                          else self._base)
                reads = relevance.reads_of_shape(source.cbd(avoided), avoided)
            else:
                reads = relevance.ANYTHING          # an obligation, a call: anything
        if reads is relevance.ANYTHING:
            return None
        return relevance.relevant(reads, relevance.actions_of(self.agent.beliefs.query),
                                  relevance.rule_edges(),
                                  relevance.subproperties_of(self.agent.beliefs.query))

    def _shape_root(self, desire: Desire):
        """The node the desire's shape hangs from, or None where it has none."""
        node = URIRef(desire.uri)
        #  The met-test hangs OFF the desire node since the reification — a desire is a node
        #  carrying its shape, not the shape itself — so the walk is one hop of `orexis:metWhen`.
        #  A node that IS a shape stays legal: an asserted root desire is a bare NodeShape a
        #  world's TriG may state, and it never grew a desire node around it.
        met = self._shapes.value(node, _AG.metWhen)
        if met is not None and ((met, RDF.type, _SH.NodeShape) in self._shapes
                                or (met, RDF.type, _SH.NodeShape) in self._base):
            return met
        if (node, RDF.type, _SH.NodeShape) in self._shapes:
            return node
        return None

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
        met_now = self._met_in(here, desire)
        if met_now and here.urgency <= 0.0:
            return self._record(desire, Plan(SATISFIED, (), here.urgency, here.urgency),
                                here.urgency)

        #  THE ROOM, for a want scoped `orexis:Within` (#472): seconds left before it expires.
        #  The scope the ledger writes restates the deadline the record carries, and the
        #  deadline is what this branches on — so a legacy row from before the scope word
        #  behaves identically, which is the volume guarantee. None where nothing expires,
        #  and every stake is that.
        room = (max(0.0, (desire.expires - datetime.now(timezone.utc)).total_seconds())
                if desire.expires is not None else None)
        best, saw_candidate = here, False
        achieved = []
        #  THE BOUND: what the cheapest achiever found so far spends. None until one is found,
        #  and from then on a candidate spending MORE than it is discarded unexamined — see
        #  `_bind` below for why that is sound rather than a heuristic.
        bound = None
        self._skipped = False
        self._weighed = [(0, row, None, trace.IRRELEVANT) for row in self._passed_over]
        #  Every world reached, with the least this pass has found it to cost. A world reached
        #  again NO CHEAPER is somewhere already stood in; reached strictly cheaper, it is
        #  reopened — see the novelty test below for why best-first needs that where
        #  breadth-first did not.
        seen = {here.diff: here.cost}
        #  THE OPEN LIST, and it is one heap rather than one layer at a time (#492). The
        #  search used to expand breadth-first: every world at depth d before any at d+1, so
        #  the first achiever arrived in the LAST layer, and a bound that arrives last has
        #  nothing left to refuse. Measured before the change, `cost + estimate` pruned no
        #  node in either domain that declares an estimate — 198 forks on the courier's
        #  corner delivery with the heuristic and 198 without. Ordered by what a path has
        #  spent plus what its want says is left, the search follows the estimate to an
        #  achiever early, and the bound it sets then refuses the rest — which is the whole
        #  of A*, and the only reason a want's estimate is worth declaring. `_priority` says
        #  what the key is and why a met want keeps the old order.
        opened = [(_priority(here, met_now), 0, here)]
        minted = 1                       # heap entries so far: the tie-break, so nodes never compare
        forked = 0                       # worlds this pass has imagined, against `self.budget`
        while opened:
            _, _, node = heapq.heappop(opened)
            if forked >= self.budget:
                #  THE BUDGET IS SPENT, and the pass answers with what it has (#494): the
                #  cheapest achiever found if any, else the nearest world, exactly as an
                #  emptied open list answers below. The search is anytime by construction —
                #  `best` and `achieved` are kept as it goes — so stopping here loses
                #  nothing already found and forgoes only what was never looked at.
                break
            if bound is not None and node.cost + _near(node) > bound:
                #  EARLY TERMINATION, and it is the same floor the per-candidate prune below
                #  stands on: this node's `cost + estimate` is under everything a plan through
                #  it would finally spend, so it cannot beat the plan in hand — and the heap
                #  is ordered by exactly that sum, so neither can anything behind it. Strictly
                #  dearer, like the prune: a world tying the bound may still yield an achiever
                #  that ties on cost and wins on urgency. Never fires for a met want, whose
                #  pass returns on its first keeper and sets no bound.
                break
            depth = len(node.taken)
            for row in self._candidates(node, desire):
                if self._relevant is not None and row.action not in self._relevant:
                    #  A lever that touches nothing this want reads, by its own effect and
                    #  by nothing it could enable (#488). Recorded, never simulated, and not
                    #  a candidate seen: a menu of such rows is NOTHING — equip me — which is
                    #  the honest finding when no lever points at the want.
                    self._weighed.append((depth, row, None, trace.IRRELEVANT))
                    continue
                saw_candidate = True
                if forked >= self.budget:
                    #  The budget ran out while this node was being expanded. Its remaining
                    #  levers are recorded as never looked at rather than silently dropped,
                    #  so a trace reads "this was there and the pass could not afford it"
                    #  and not "this was weighed and lost".
                    self._weighed.append((depth, row, None, trace.SPENT))
                    continue
                #  Steps are ROWS, not means: a plan is a path through the affordance
                #  graph, and which lever a step goes through is half of what it says.
                step = self._step_from(node, row, desire, bound)
                if step is TOO_DEAR:
                    #  Never simulated, so there is no urgency to report: what the trace
                    #  records is that the search refused to spend on it, and why.
                    self._weighed.append((depth, row, None, trace.COSTLY))
                    continue
                if step is None:
                    self._weighed.append((depth, row, None, trace.UNSIMULATED))
                    continue
                forked += 1              # a world exists now, whatever becomes of it below
                if self._law is not None:
                    #  EVERY STATE of a plan is checked, not the end alone — the
                    #  sovereign's ruling (#468): a valid plan contains no state that
                    #  NEWLY matches a violation-severity shape, so a 4 to -10 to 5
                    #  walk dies at -10 however well it ends. Discarded before the
                    #  met-test can crown it and never expanded — and the next legal
                    #  candidate wins by construction, which retires the no-fallback
                    #  seam rather than implementing it.
                    newly = self._forbidden_keys(step) - self._base_forbidden
                    if newly:
                        self._weighed.append((depth, row, step.urgency, trace.FORBIDDEN))
                        continue
                if bound is not None and step.cost + _near(step) > bound:
                    #  A* PRUNING, and it is the estimate's whole reason for existing in
                    #  the search rather than only in the ranking. `orexis:estimates` never
                    #  overstates what is left, so `cost + estimate` is a floor under what
                    #  any plan THROUGH this world would finally spend: past the bound, no
                    #  completion of it can beat the plan already in hand. The candidate
                    #  before the bound existed had to be simulated to be dismissed; this
                    #  one is dismissed after its own world is known and before its
                    #  children are, which is where the subtree goes.
                    #
                    #  A want declaring no estimate reads 0.0 and this is the plain cost
                    #  bound above, exactly as before the term existed.
                    self._weighed.append((depth, row, step.urgency, trace.COSTLY))
                    continue
                if room is not None and step.landing > room:
                    #  A world reached after the want has lapsed is not an answer to it
                    #  (#472, `orexis:Within`): discarded BEFORE the met-test can crown
                    #  it, so a serve landing past the claim's expiry never becomes
                    #  SATISFIED — and never expands, since what it reaches it reaches
                    #  too late.
                    self._weighed.append((depth, row, step.urgency, trace.LATE))
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
                #
                #  REOPENED WHEN REACHED STRICTLY CHEAPER, and best-first is why (#492).
                #  Breadth-first reached every world by a shortest path first, so the path
                #  that claimed a world was never dearer than any later one. A heap ordered
                #  by `cost + estimate` expands a deep node before a shallow one whenever
                #  the estimate says to, so a world can be claimed first by a dearer path
                #  and the cheaper one arrive later — and a search that discarded it as
                #  seen would crown an eight-move hanoi where seven exist, since every
                #  achiever below that world would inherit the dear prefix. Reached no
                #  cheaper is still somewhere already stood in, which keeps +3 then -3
                #  pruned and a free action's return to the base world with it.
                #
                #  NO SHIPPED DOMAIN CAN WITNESS IT, measured: zero reopens on hanoi and on
                #  eight courier poses at depth 9. Both move by unit cost and both estimates
                #  move by at most one per step, so two paths to one world carry equal f and
                #  the cheaper pops first by the key's own tie-break. It is kept for the
                #  domain whose costs are real numbers — a dose priced in litres — where the
                #  argument fails and the loss would be silent. The test goes beside the
                #  courier's the day a domain can show it.
                where = step.diff
                novel = where not in seen or step.cost < seen[where]
                if novel:
                    seen[where] = step.cost
                    #  LEXICOGRAPHIC, urgency first (#466): cost speaks only where urgency
                    #  cannot separate two candidates — same urgency, cheaper wins — and
                    #  never outranks it, because a society that traded a plant's
                    #  wellbeing for money would have that ranking ratified nowhere. The
                    #  satisficing floor below is untouched: a plan no better than
                    #  standing still stays refused however cheap it is.
                    #  NEARER COUNTS AS BETTER when the want can say how near. A want
                    #  that only knows met from unmet leaves `estimate` None, and this is
                    #  the old comparison exactly; a want that declares one lets a world
                    #  three moves from done beat a world five moves from done, which is
                    #  what makes a search shallower than the solution worth running at
                    #  all. Cost still breaks a tie, and urgency still outranks both.
                    if (step.urgency, _near(step), step.cost) < (
                            best.urgency, _near(best), best.cost):
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
                if (novel or not met_now) and self._met_in(step, desire):
                    self._weighed.append((depth, row, step.urgency, trace.MET))
                    if met_now:
                        #  Already met and still steering: the first novel step that
                        #  keeps it met stays the answer — re-picking among keepers by
                        #  cost would be shopping for a want that is not shopping for
                        #  anything.
                        return self._record(
                            desire,
                            self._offer(Plan(SATISFIED, step.taken, here.urgency,
                                             step.urgency),
                                        desire, step),
                            here.urgency)
                    #  ACHIEVERS ARE COLLECTED, never returned on sight — the
                    #  sovereign's two-stage cut (#466): urgency is the DESIRE's term
                    #  and cost is the ACTION's. Urgency already picked which want this
                    #  pass serves, so among plans that ACHIEVE it, cost alone decides
                    #  — and returning the first met step was the one-axis shortcut,
                    #  crowning whichever achiever the menu happened to yield first.
                    #  An achiever still never extends the frontier: a step that
                    #  answers the question is not a place to search onward from.
                    achieved.append(step)
                    bound = step.cost if bound is None else min(bound, step.cost)
                    continue
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
                #  `orexis:confirmedBy orexis:ByObservation`, which every effect here answers — a
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
                #  No depth bounds the push (#494): what bounds the pass is the budget above,
                #  and a world is a place to search on from however long the path to it.
                heapq.heappush(opened, (_priority(step, met_now), minted, step))
                minted += 1

        if achieved:
            #  Achievement is absolute — the desire's demand — and cost orders the
            #  achievers; the desire's own measure breaks a cost tie (nearer the aim wins),
            #  so the answer is deterministic whatever order the menu yielded them in.
            won = min(achieved, key=lambda s: (s.cost, s.urgency))
            return self._record(
                desire,
                self._offer(Plan(SATISFIED, won.taken, here.urgency, won.urgency),
                            desire, won),
                here.urgency)

        #  A pass that ends with no step worth taking is labelled by the SHAPE, not by the
        #  search: a met desire that weighed its levers and found none worth pulling is
        #  SATISFIED — it is met, and near the pick every dose sizes to nothing, which is the
        #  deadband satisficing gives for free — where an unmet one in the same position is
        #  NOT_BETTER (my doses are too coarse) or NOTHING (equip me), and those must not blur.
        if not saw_candidate:
            return self._record(desire, Plan(SATISFIED if met_now else NOTHING,
                                           (), here.urgency, here.urgency,
                                           self._skipped), here.urgency)
        if best is here or (best.urgency, _near(best)) >= (here.urgency, _near(here)):
            after = here.urgency if best is here else best.urgency
            return self._record(desire, Plan(SATISFIED if met_now else NOT_BETTER,
                                           (), here.urgency, after,
                                           self._skipped), here.urgency)
        return self._record(desire, self._offer(
            Plan(EXHAUSTED if not self._met_in(best, desire) else SATISFIED,
                 best.taken, here.urgency, best.urgency), desire, best), here.urgency)

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

    def _offer(self, plan: Plan, desire: Desire, node) -> Plan:
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
        #  THE ONE PLACE A WORLD IS STILL FLATTENED INTO RDFLIB, and it is affordable because
        #  it happens once per pass rather than once per node: `conforms` carves the shapes an
        #  agent holds out of its own data with `cbd`, which is an rdflib walk. Parsed from
        #  the same text every other verdict this pass was given.
        world = rdflib.Graph()
        world.parse(data=self._border(node), format="nt")
        ok, _ = conforms(world, focus=self.me.uri)
        if ok:
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
        #  declared-Violation cbds), so judge.py's severity gap cannot reach the keys. A law
        #  shape MIXING forces within itself would need the split conformance._judged does —
        #  none exists today, and the result filter below is where it would show.
        results, _ = judge(self._border(node), self._law)
        return frozenset(
            (str(results.value(r, _SH.sourceShape)),
             str(results.value(r, _SH.focusNode)),
             str(results.value(r, _SH.value)))
            for r in results.subjects(rdflib.RDF.type, _SH.ValidationResult)
            if results.value(r, _SH.resultSeverity) == _SH.Violation)

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
        #  ASKED OF THE IMAGINARIUM, at the node's own graph (#359): a premise may be a fact
        #  an earlier step made true — Offering needs stock, Acquiring's effect raises it, and
        #  "acquire, then offer" is a plan only if the menu of the world after the first step
        #  shows the second. The root node's graph is the agent's own readings, so at depth 0
        #  this is the ordinary menu, exactly as before.
        for row in affordances_of(self.imaginarium.query, self.me.uri, self.agent.desires.query_union,
                           beliefs_graph(self.agent.id), node.graph, only=self._asked):
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
        self._base = base
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
        #  (`orexis:keyedBy`, `orexis:carries` on the node's class), read once per pass so the signature
        #  canonicalises a reading without this file knowing what one looks like.
        self._about_of = wants_of(self.agent.desires.query_union, self.me.uri)
        self._keys = signature.keys_of(store.query)
        self._base_facts = signature.facts((
            quad for iri in [*store.public_graphs(), *store.recorded_graphs()]
            for quad in store.quads(iri)), self._keys)
        #  THE LAW THIS PASS PRUNES BY (#468): the violation-severity shapes the DATA
        #  carries — a world-authored MUST NOT over a runtime state — collected once, held
        #  against every candidate at expansion rather than against the winner alone. The
        #  base's own violations are kept because the rule is NEVER-NEWLY-ENTER: an agent
        #  already inside a forbidden state must keep its exit plans, or the recovery is
        #  pruned with everything else — the same trap that made the envelope a warning at
        #  the gates, met from the planner's side. Empty in a world that ratifies no such
        #  shape, and then this costs nothing per node.
        self._law = self._violation_shapes(base)
        #  THE INVARIANT HALF OF EVERY WORLD THIS PASS WILL JUDGE, written once by the store's
        #  own engine (#481). Every graph the imaginarium copied EXCEPT the readings — those
        #  are what a step changes, and each node carries its own — plus the wants, which the
        #  flat world carried before and `_offer` still needs. Asked rather than named, like
        #  everything else about which graphs exist.
        self._invariant_graphs = tuple(
            iri for iri in list(self.agent.beliefs.public_graphs())
            + list(self.agent.beliefs.recorded_graphs()) if iri != STATE_GRAPH)
        self._invariant = (self.imaginarium.dump_nt(*self._invariant_graphs)
                           + self._shapes.serialize(format="nt"))
        #  THE WANT'S VIOLATION SELECT, compiled once for the pass (#497) — None where the
        #  want is not a shape (a pattern want, an obligation, a call). A shape this compiler
        #  cannot say REFUSES here, loudly, rather than judging by something quieter: a want
        #  that silently read as met is the failure the compiler exists to rule out.
        shape = self._shape_of(desire)
        self._unmet = (violation.unmet_select(shape, self._shape_root(desire))
                       if shape is not None else None)
        #  THE NEGATIVE TWIN AS A SHAPE (#499): an aversion under `orexis:unmetWhen` authored
        #  as the avoided state, compiled to its CONFORMANCE select — rows where the state
        #  has been entered — and judged by the same road as a compiled positive want.
        avoided = self._shapes.value(URIRef(desire.uri), _AG.unmetWhen)
        if avoided is not None and self._unmet is None:
            source = (self._shapes if (avoided, RDF.type, _SH.NodeShape) in self._shapes
                      else self._base if (avoided, RDF.type, _SH.NodeShape) in self._base
                      else None)
            if source is not None:
                self._unmet = violation.entered_select(source.cbd(avoided), avoided)
        #  WHICH LEVERS COULD SERVE THIS WANT (#488): what the want reads, off its shape or
        #  its pattern; what each action writes and reads, off the actions themselves; the
        #  backward closure of the two. A row whose action is outside the set is never
        #  simulated — one free foreign action multiplied a hanoi solve 2.8 times, and this is
        #  the only defence that sees it. None where the want reads anything a parser cannot
        #  name, and then every row is weighed exactly as before: over-approximation is safe.
        self._relevant = self._relevant_actions(desire, shape)
        #  WHAT THE MENU IS ASKED FOR, per node (#504): the relevant levers, plus every lever
        #  stating no effect — outside the closure, never simulated, but a row of it must
        #  still reach the pass so the pass can say it could not see the whole menu.
        self._asked = (None if self._relevant is None
                       else self._relevant | relevance.effectless_of(self.agent.beliefs.query))
        #  THE LEVERS PASSED OVER, asked ONCE per pass at the root rather than at every node,
        #  and written as passed over only where they had a row to pass over: a trace that
        #  named every irrelevant action in the vocabulary would name Move in a plant world
        #  with no disk in it. One query per foreign action per pass is what a truthful
        #  trace costs, against one per node before this.
        self._passed_over = [] if self._relevant is None else affordances_of(
            self.imaginarium.query, self.me.uri, self.agent.desires.query_union,
            beliefs_graph(self.agent.id), STATE_GRAPH,
            only=frozenset(relevance.actions_of(self.agent.beliefs.query)) - self._relevant)
        here = _Node(graph=STATE_GRAPH)
        here.estimate = self._estimate_in(here, desire)
        self._base_forbidden = (self._forbidden_keys(here)
                                if self._law is not None else frozenset())
        here.urgency = self._urgency_in(here, desire)
        return here

    def _border(self, node) -> str:
        """This node's whole world as one N-Triples text, for the judge.

        The invariant half is every graph a judged world holds that no step can change —
        public knowledge, this agent's beliefs, whatever it records — plus the wants, which
        ride along because `_offer`'s legality check needs them. Written once per pass in
        `_begin`. The variant half is this node's readings, and a concatenation is all that
        separates them because N-Triples lines stand alone.

        WRITING THE VARIANT HALF IS DEFERRED TO HERE, and cached on the node once written. A
        pass forks far more worlds than it judges — 76 against 1 on a 3-disk solve — because
        scoring a want met by a pattern asks the store at `node.graph` and never needs text.
        """
        if node.readings is None:
            node.readings = self.imaginarium.dump_nt(node.graph)
        return self._invariant + node.readings

    def _step_from(self, node, row, desire: Desire, bound: float | None = None):
        """The node one step on from here, or None where the rule would not run.

        The diff lands in ONE place — the imaginarium graph the next step's rule will read —
        and the node keeps that graph's text for the judge. Asked of the IMAGINARIUM and not of
        the belief base, which is the whole of #254 — a retraction asked of the store finds the
        observation still on disk, so the second dose lands beside the first instead of
        replacing it and is then discarded as a world already seen.
        """
        bind = self._bind(desire, node, row)
        #  WHAT IT SPENDS, ASKED FIRST — `orexis:costs`, the landing's twin (#466), and None is
        #  free. It is asked before the rule is run because that is what makes the bound worth
        #  having: a candidate already dearer than a plan in hand is dropped without simulating
        #  its effect or forking its world, which are the two expensive things a step does.
        spent = effects.cost_of(self.imaginarium, row.action, **bind)
        cost = node.cost + (spent or 0.0)
        if bound is not None and cost > bound:
            return TOO_DEAR
        try:
            added, retracted = effects.apply(self.imaginarium, row.action, **bind)
        except Exception as exc:                 # a package's rule is not an agent's problem
            log.error("could not simulate %s: %s", row.action, exc)
            return None
        #  THE ROW BECOMES AN ACT here, where it is sized — the quantity the taker answered is
        #  what the rule just simulated — and the act becomes a STEP once the world it reaches
        #  is scored. An act carries no window yet: nothing in a search knows when.
        act = Act.from_row(row, quantity=bind["litres"] or None)
        path = node.taken + (Step(act),)
        diff = signature.advance(node.diff, signature.facts(added, self._keys),
                                 signature.facts(retracted, self._keys), self._base_facts)
        graph = self.imaginarium.reached(node.graph, path, added, retracted)
        #  When this path's last change completes: the step's own `orexis:landsAfter`, asked of
        #  the rule exactly as the keeper asks it, summed along the path (#472). None — no
        #  stated timing — adds nothing, which is the keeper's own contract for it.
        lands = effects.lands_after(self.imaginarium, row.action, **bind)
        landing = node.landing + (lands or 0.0)
        step = _Node(graph=graph, diff=diff, landing=landing, cost=cost)
        step.urgency = self._urgency_in(step, desire)
        step.estimate = self._estimate_in(step, desire)
        step.taken = node.taken + (Step(act, urgency_after=step.urgency),)
        return step

    def _bind(self, desire: Desire | None, node=None, row=None) -> dict:
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
        #  VALUES, NOT TEXT (#500): each is the IRI, the number or the literal it is, and
        #  `store.bind` renders it as the term where the rule's `$token` stands — whole token,
        #  never a prefix of a longer one, and a token nobody bound refuses.
        graph = node.graph if node is not None else STATE_GRAPH
        return {
            "me": self.me.uri,
            "claim": Raw(f'"{desire.claim}"') if desire and desire.claim else Raw('"urn:nobody"'),
            "subject": self.me.acts_for if self.me.acts_for else "urn:nobody",
            #  THE WANT AND WHAT IT IS ABOUT, carried from the row to the rule and never read
            #  here: `$about` is whatever the want's deriver said (`orexis:about`) — a property,
            #  for a region want — and the rule joins on it in its own words.
            "want": desire.uri if desire else "urn:nothing",
            "about": row.about if row is not None and row.about else "urn:nothing",
            #  THE LEVER, since the sovereign struck hanoi's ground-action grid: a row always
            #  carried which lever a step goes through, and the effect could never see it —
            #  so a two-parameter action was inexpressible and hanoi shipped six ground
            #  nodes. One schema needs the channel: $via is the row's lever, symmetric with
            #  $about, and a rule that ignores it loses nothing.
            "via": row.via if row is not None else "urn:nothing",
            "beliefs": beliefs_graph(self.agent.id),
            "state": graph,
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

        ASKED OF THE TAKER, found the way execution finds it — the action's `orexis:takenBy` family
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
        from orexis_agent_progression.execution import taken_by

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


_AG_IRI = "http://example.org/orexis#"


@dataclass
class PlanningBeliefs:
    """What the sovereign said about this agent's thinking: how many worlds a pass may fork."""

    budget_worlds: int


#  Read the way the keeper's patience is (`KEEPING_PICKS`), with the one difference that this
#  block may be wholly absent: `read_optional`, and the engine's ceiling stands in.
PLANNING_PICKS = Picks(
    capability=_AG_IRI + "Deliberation",
    cls=PlanningBeliefs,
    terms={"budget_worlds": _AG_IRI + "budgetWorlds"},
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

_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
_AG = rdflib.Namespace(_AG_IRI)
#  No means or family is named here any more: sizing is `Module.size`, asked of the row's
#  taker through `orexis:takenBy` exactly as execution finds it.
