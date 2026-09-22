"""The search: derive what is wanted, then walk the worlds each step would make.

**One pass, and this is the whole of it.** Handed the beliefs store and the one identifier a
process is told:

1. `derive_wants` judges every desire the store holds, at the present and at every instant a
   prediction reaches, and mints a want per cluster of what the met-tests read unmet;
2. the wants are grouped by SCOPE — which predicates move together, as `scope_actions` wrote
   them — and each group gets an imaginarium of its own, filled from the beliefs by
   `prepare_ground`;
3. inside each, a best-first walk: what does this world afford, what would each step make
   true, is the want met there. What a pass finds it WRITES: one `planning:Plan` graph per
   want, in the imaginarium that want was searched in, holding the steps in the ledger's own
   words and why the pass ended. Nothing comes back.

Nothing here commits. Copying a plan into the ledger is the execution layer's
(`plans.copy_plan`), because deciding a thing and remembering that it was decided are
different acts.

**WHAT THE PREDECESSOR'S SEARCH HAD AND THIS DOES NOT**, each an absence rather than an
oversight (an-agent-is-four-things):

- **the relevance closure** — only simulating actions whose predicates the want can read.
  A narrowing, measured and real; it returns when a world is big enough to need it.
- **the cone and the re-root** — resuming a search where the observed present still matches a
  node it had already reached. A pass here starts from the present every time.
- **remembered plans** — adopting a route that worked before without searching for it again.
- **the trace** — the record of what a pass considered, for a reader. Nothing in the search
  reads it back, so nothing here writes it.
- **what a plan LANDS at, where it was placed, and which candidate it came through** — three
  fields the predecessor's record carried and nothing read, two of which say nothing new
  while a pass stands at one instant. A term nobody reads is annotation; they come back with
  their readers.
- **the A\\* key** — ordering the frontier by cost plus the want's own `orexis:estimates`.
  The frontier is ordered by cost alone, which is uniform-cost search: the same answer, more
  worlds visited to reach it.

What is NOT missing is the part any of those could be wrong about: the budget in worlds, the
cycle detection by hash, and the met-test. A want is judged by the select its own shape
compiles to, which is the one judgment path (a-want-is-judged-by-its-met-test-and-nothing-else).

See knowledge/domain/planner.md.
"""

from __future__ import annotations

import heapq
import itertools
import logging
from datetime import datetime, timedelta
from urllib.parse import quote

import pyoxigraph as ox
import rdflib

from orexis.agent import clock
from orexis.agent import violation
from orexis.agent.execution.act import Step
from orexis.agent.ontology import (DESIRE, FORESEEN, GRAPH_PREFIX, OREXIS, PREDICTION,
                                             PUBLIC, RECORD, STATE, STATE_GRAPH, WANT,
                                             local_of)
from orexis.agent.hash_named_graph import hash_named_graph
from orexis.agent.store import (Memo, add_quads, bindings, catalogue_of, classify,
                                           clear_graph, copy_graph,
                                           forget_graph, graphs_of, query,
                                           rdflib_view)

from . import effects, touches
from .apply_effects import apply_effects
from .prepare_ground import prepare_ground
from .publish_plan import publish_plan
from .derive_wants import derive_wants
from .ontology import (BY, COSTS, EXHAUSTED, FOR_WANT, GROUND_GRAPH, NO_CANDIDATE,
                       OUTCOME, PLAN_GRAPH, POSSIBLE_GRAPH, SATISFIED)
from .scopes import find_scopes
from .steps import find_steps

log = logging.getLogger("search")

#  THE CEILING ON WHAT A PASS MAY SPEND, in the unit it spends: worlds forked in the
#  imaginarium (#494). It is a ceiling on COMPUTE and so not a preference an agent may
#  revise — the predecessor made it a pick a sovereign could state, and that pick is one of
#  the things that returns with the machinery for reading picks. Sized for a plant, whose
#  pass forks a handful, and enough to solve two disks of hanoi (14) but not three (50).
BUDGET = 32


class Planner:
    """One agent's search. Holds the beliefs store, the pass's memo, and who it is."""

    def __init__(self, beliefs: ox.Store, agent_id: str, intentions: ox.Store | None = None):
        """The beliefs store, the one identifier a process is told, and where a plan goes.

        Everything else is discovered from the graph, which is rule 1: the world says
        `?a orexis:localId "<id>"`, and who I am and what I act for are the answer rather
        than arguments.

        `intentions` is the LEDGER, and a pass hands its plans down to it as its last act. A
        planner given none searches and writes its findings into the imaginarium and no
        further — which is what a case wants, and what the search itself is.
        """
        self.beliefs = beliefs
        self.intentions = intentions
        self.id = agent_id
        self.uri, self.acts_for = self._identity(agent_id)
        #  The readings graph of the pass in hand — set at `plan`, since which graph that is
        #  is the catalogue's to say and a pass is what stands somewhere.
        self._state: str | None = None
        #  THE WORLD IN HAND and its memo, set per scope at `plan`. A pass stands somewhere,
        #  and where is not an argument every method between here and the frontier carries.
        self._store: ox.Store | None = None
        self._memo = Memo()
        #  THE PASS'S IMAGINARIA, one per scope, replaced at every `plan`. They are where the
        #  pass wrote what it found, so this is how a caller reaches it — each is asked for
        #  its graphs of class `planning:PlanGraph`, the same by-kind read as everywhere
        #  else. They are memory and die with the Planner, as a plan about a world that has
        #  moved should.
        self.imaginaria: list[ox.Store] = []

    def _identity(self, agent_id: str) -> tuple[str, str | None]:
        """Who this agent is and what it acts for, off the world graph.

        `a orexis:Agent` is load-bearing and not decoration: a plant, a sensor and a valve
        carry `orexis:localId` too, and a world names its subject after its agent — so the
        bare pattern matches two things and `LIMIT 1` picks by the store's internal order,
        which a change to load order silently flips. It did once, and every pick read asked
        the PLANT.
        """
        found = bindings(query(self.beliefs, f"""
SELECT ?a ?for WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" .
                        OPTIONAL {{ ?a orexis:actsFor ?for }} }} LIMIT 1""",
                               graphs_of(self.beliefs, PUBLIC)))
        if not found:
            raise LookupError(
                f"no agent with localId '{agent_id}' in this store — was the world loaded "
                "before the planner was built?")
        return found[0]["a"], found[0].get("for")

    # --- the pass ----------------------------------------------------------------------------

    def plan(self, now: datetime | None = None) -> None:
        """One pass: make a world per scope, judge what is wanted in it, and plan for each.

        THE IMAGINARIUM COMES FIRST, AND THE DERIVATION RUNS INSIDE IT. What a desire reads at
        a future instant is what the GROUND holding then says — the present with each
        prediction applied in turn, one graph per period — and a ground exists only where
        `prepare_ground` has laid one. Judged against the belief base instead, a desire sees
        the reading AND the prediction of it at once, and a shape holds over every value, so
        the stale one still violates: a tank low now with a forecast refilling it reads unmet
        for ever. Nothing was wrong with the forecast; there was nowhere in the pass where it
        REPLACED anything, and the grounds are that place.

        WHAT IS DERIVED IS KEPT. A pass writes its wants into the imaginarium and takes none
        of them away: the store is memory, so what the derivation did not mint this pass is
        not there to withdraw, and withdrawal is an act about a store that OUTLIVES a pass.

        ONE PER SCOPE OF THE STORE, which is what the scopes are for: two wants whose
        predicates move together are searched in one imagined world, so a step taken for the
        first is visible to the second, and two in different scopes cannot affect each other
        by construction. The scopes are READ and never computed — `scope_actions` wrote them,
        and a store holding no scope graph is refused rather than guessed at as one scope.

        NOTHING COMES BACK, because everything a pass finds it WRITES: one graph per want in
        the imaginarium it was searched in, `planning:Plan`, holding the steps in the ledger's
        own words and why the pass ended. A reader asks the imaginaria this pass left
        (`self.imaginaria`) for their graphs of that class, exactly as every other read here
        asks by kind.

        AND THE LAST ACT IS `publish_plan`, where a planner was given a ledger: the
        imaginarium is memory and dies with the pass, so an intention is the only thing a pass
        leaves behind. A plan with no steps does not cross — an answer is not a commitment.
        """
        at = now or clock.now()
        scopes = find_scopes(self.beliefs)
        if scopes is None:
            raise RuntimeError("the store holds no scope graph — scope_actions has not run")
        #  A STORE WITH NO ACTION HAS ONE WORLD, not none. `scope_actions` writes the scope
        #  graph whatever it finds, so a store with nothing to do is scoped and EMPTY — and a
        #  desire in it still has to be judged, to say that no lever points at it. Iterating
        #  the scopes alone made no imaginarium at all and the want went unjudged.
        families = sorted(set(scopes.values())) or [UNSCOPED]
        self.imaginaria = []
        for scope in families:
            #  WHAT CROSSES IS THE FILL'S TO ASK. `prepare_ground` asks the catalogue for
            #  the kinds a search reads and lays the ground worlds while it is there.
            self._store = prepare_ground(self.beliefs, ox.Store(),
                                           _scope_name(scope), at)
            self.imaginaria.append(self._store)
            #  THE PASS'S MEMO, one per world. The action templates, a rule text and the class
            #  definitions cost more to re-read than a pass can afford and can change only by
            #  a write the search does not make. Per WORLD and not per pass, because each
            #  derives its own wants and the shapes cached here are theirs.
            self._memo = Memo()
            #  AND NOTHING IS TAKEN AWAY. A pass used to withdraw what the desires no longer
            #  imply, which is an act about a belief base that OUTLIVES the pass; the wants
            #  are the imaginarium's now and the imaginarium is memory, so what the derivation
            #  did not mint this pass simply is not there. The whole set it answers with is
            #  kept, and `forget_wants.withdraw` waits for a store that persists them.
            derive_wants(self._store, at)
            #  THE WORLD THE SEARCH STARTS IN is the GROUND holding at the instant it stands
            #  at — asked of the catalogue by class, never named (a graph IRI is an instance).
            self._state = next(iter(graphs_of(self._store, GROUND_GRAPH, at=at)), None)
            for want in self._of_scope(scope, scopes, at):
                self._search(want, at)
            #  AND THE LAST ACT OF THE PASS: what was found crosses to the ledger. Per scope,
            #  because the imaginarium dies with the pass and this is the only thing that
            #  outlives it.
            if self.intentions is not None:
                publish_plan(self._store, self.intentions, self.id)

    def _of_scope(self, scope: str, scopes: dict,
                  at: datetime) -> list[str]:
        """The wants this imaginarium is the world for: those whose met-test reads a predicate
        in `scope`, and those it reads nothing readable of, which join everything.

        WHAT A WANT READS IS PARSED OFF ITS MET-TEST, never declared beside it. A want used to
        state the one domain property it was about and this keyed on that, which is the
        planning problem answered before the planner is asked — and in a real world it did not
        even work: the scopes are over RDF PREDICATES while an about is a quantity kind, so
        `water:SoilMoisture` matched no scope and every want fell through to its own name.
        A shape's paths ARE predicates, so this separates what cannot interfere.

        A WANT SPANNING SCOPES IS SEARCHED IN THE FIRST OF THEM, and that is a LOSS this
        ordering bought. The grouping it replaced was keyed by every scope a want reached, so
        two wants that could interfere through it shared a world; scopes are the store's now
        and a want cannot join two of them after the worlds are made. What it costs is that
        the third want's step is invisible to the other two, not that anything is done twice:
        one world is picked, deterministically, so a want has one plan.
        """
        shapes = rdflib_view(self._store,
                             *graphs_of(self._store, DESIRE, WANT, RECORD, at=at))
        first = (sorted(set(scopes.values())) or [UNSCOPED])[0]
        mine = []
        for want in find_wants(self._store, at, holder=self.uri):
            reads = touches.reads_of_shape(shapes, rdflib.URIRef(want))
            if reads is touches.ANYTHING:
                #  A WANT WHOSE SHAPE THE WALKER CANNOT READ joins everything, which is the
                #  safe direction — it is searched once, in the first scope, rather than
                #  separated from a world that could repair it.
                if scope == first:
                    mine.append(want)
                continue
            reached = sorted({scopes[str(p)] for p in reads if str(p) in scopes})
            if reached[:1] == [scope] or (not reached and scope == first):
                mine.append(want)
        return mine

    # --- one want ----------------------------------------------------------------------------

    def _search(self, want: str, at: datetime) -> None:
        """Best-first over the worlds this want's steps would make, bounded by `BUDGET`.

        WRITES ITS FINDING AND RETURNS NOTHING — the plan graph is the answer, and it is
        written whatever the pass concludes, since an empty plan says which of the two
        silences it is and that is the finding a want most needs.

        THE FRONTIER IS ORDERED BY COST ALONE — uniform-cost search. The predecessor added
        what the want said was left to spend and walked that gradient, which is A\\*; the
        answer is the same and the number of worlds visited is not.

        THE FIRST ACHIEVER BOUNDS THE REST. Once a world where the want is met has been
        reached for some cost, nothing costing more can win, so the frontier is cut there —
        which is what makes the budget a ceiling on a search rather than on an enumeration.

        A CYCLE IS A WORLD ALREADY SEEN, by hash: +3 then −3 returns to the world you
        started in, and a search that does not notice spends its whole budget going nowhere.
        """
        select = self._met_select(want)
        root = _Node(world=self._state, taken=(), cost=0.0, at=at)
        if self._met(select, root, want):
            self._write(want, SATISFIED, (), 0.0)
            return

        seen = {self._hash_of(root)}
        tick = itertools.count()
        frontier: list = [(0.0, next(tick), root)]
        best: "_Node | None" = None
        forked = 0
        saw_step = False

        while frontier and forked < BUDGET:
            cost, _, node = heapq.heappop(frontier)
            if best is not None and cost >= best.cost:
                break                       # the first achiever's bound refuses the rest
            #  THE MENU, asked of the world this node stands in: one step per action per
            #  legal filling, name-ordered. Not narrowed by what the want is about — the
            #  closure that would narrow it is among this tree's absences, and filtering to a
            #  goal's own predicates deletes every chain anyway.
            for step in find_steps(self._store, self.uri,
                                   graphs=self._dataset(node), memo=self._memo):
                saw_step = True
                if forked >= BUDGET:
                    break
                child = self._take(node, step, want)
                if child is None:
                    continue
                forked += 1
                fingerprint = self._hash_of(child)
                if fingerprint in seen:
                    drop_world(self._store, child.world)
                    continue
                seen.add(fingerprint)
                if self._met(select, child, want):
                    if best is None or child.cost < best.cost:
                        best = child
                    continue
                heapq.heappush(frontier, (child.cost, next(tick), child))

        if best is not None:
            self._write(want, SATISFIED, best.taken, best.cost)
            return
        #  THE TWO SILENCES ARE NOT THE SAME, and telling them apart is most of why an empty
        #  plan is written at all: NO CANDIDATE says no lever this agent holds points at this
        #  want (equip me), EXHAUSTED says levers exist and no bounded sequence of them lands
        #  inside the region (my doses are too coarse, or my region is too tight for them).
        self._write(want, EXHAUSTED if saw_step else NO_CANDIDATE, (), None)

    # --- the moves ---------------------------------------------------------------------------

    def _take(self, node: "_Node", step: Step,
              want: str) -> "_Node | None":
        """The world one step past this one, or None where the step's effect says nothing.

        THREE QUESTIONS AND ONE ACT. What the step costs and how long it takes to land are
        asked of the world it is taken IN, before anything is applied — a cost read off the
        state it is about to change would answer about the change. Then `apply_action` makes
        the world.
        """
        graphs = self._dataset(node)
        binding = self._bind(step, node, want)
        spent = effects.cost_of(self._store, step.action, graphs,
                                memo=self._memo, **binding) or 0.0
        lands = effects.lands_after(self._store, step.action, graphs,
                                    memo=self._memo, **binding) or 0.0
        taken = node.taken + (step,)
        world = apply_action(self._store, node.world, world_of(taken), step.action, graphs,
                             memo=self._memo, **binding)
        if world is None:
            return None
        return _Node(world=world, taken=taken, cost=node.cost + spent,
                     at=node.at + timedelta(seconds=lands))

    def _bind(self, step: Step, node: "_Node", want: str) -> dict:
        """The `$tokens` a rule text of this step's takes: what it is filled with, who is
        asking, what the want is about, and which world.

        ONE SPELLING SERVES THREE PLACES (an-action-takes-parameters): a parameter's local
        part is the variable its precondition projects, the `$token` its rules read and the
        predicate the step is written under, so nothing maps between them.
        """
        out = {"state": _raw(node.world), "me": self.uri,
               "subject": self.acts_for or "urn:nobody",
               "want": want, "now": _instant(node.at)}
        for parameter, value in step.binding:
            out[local_of(parameter)] = value
        if step.quantity is not None:
            out["quantity"] = step.quantity
        return out

    def _dataset(self, node: "_Node") -> list[str]:
        """What a rule is answered over in this world: everything a rule may read at the
        instant this node stands at, with the node's own readings in the state's place.

        THE READER STATES THE KINDS IT READS and the instant it stands at, and a list built
        for the wrong instant returns an EMPTY RESULT rather than an error — so it is built
        in one place (#666).

        WHAT IS LEFT OUT IS EVERYTHING THE GROUND ALREADY SPEAKS FOR: the agent's own readings,
        and every ground but this node's. A ground IS the readings as they stand over a period,
        with each prediction applied — so handing the raw state graph beside it puts the
        present's value in the world next to the one that superseded it, and a shape holding
        over every value sees both. Measured the moment the root became a ground: a tank filled
        to ten still read below ten, because the nought it started at was in the world too.

        PREDICTIONS ARE LEFT OUT FOR THE SAME REASON — they are the diffs the grounds were made
        from, and a diff is not a fact about a world.
        """
        #  ASKED ONCE PER INSTANT, not once per fork. What is in the list depends on the
        #  INSTANT and nothing else — the node's own world is appended after — and building it
        #  is four questions to the catalogue. Measured on the plans case before this: a
        #  `_take` cost nine engine calls of which five were these, so the search spent more
        #  of itself asking which graphs to read than reading them.
        graphs = self._memo.get(("dataset", node.at), lambda: self._graphs_at(node.at))
        return [*graphs, node.world] if node.world else list(graphs)

    def _graphs_at(self, at: datetime) -> tuple[str, ...]:
        spoken_for = {*graphs_of(self._store, STATE),
                      *graphs_of(self._store, PREDICTION),
                      *graphs_of(self._store, GROUND_GRAPH)}
        return tuple(g for g in graphs_of(self._store, *FORESEEN, at=at)
                     if g not in spoken_for)

    # --- the verdict -------------------------------------------------------------------------

    def _met_select(self, want: str) -> str | None:
        """The want's met-test, compiled to the select whose rows are its violations.

        A VERDICT THE SEARCH READS IS A QUERY. The judge's own reader floors at tens of
        milliseconds where a compiled select costs one, and a search asks this at every node;
        holding the two to one answer by parity is what makes that safe, which is
        `conformance`'s job at the gates and not this one's.

        THE SHAPE IS IN THE WANT'S OWN GRAPH, pointed at by `orexis:metWhen`: the derivation
        writes the desire's met-test instantiated at this want's witness — the same shape
        under the want's own name, targeting the one instance in trouble
        (a-desire-is-universal-and-a-want-is-existential). Carved to its blank-node closure,
        because a shape is a structure and not a triple.

        None where nothing points at a shape, which nothing this package mints is.
        """
        shapes = self._shapes()
        root = shapes.value(rdflib.URIRef(want), _MET_WHEN)
        if root is None:
            return None
        return violation.unmet_select(shapes.cbd(root), root)

    def _shapes(self) -> rdflib.Graph:
        """Every want and desire this agent holds, as one rdflib graph — where a met-test is
        declared. Per pass, because a search writes none of them: a rebuild in the middle
        would hand two depths two different wants."""
        return self._memo.get(("shapes",), lambda: rdflib_view(
            self._store, *graphs_of(self._store, DESIRE, WANT, RECORD)))

    def _met(self, select: str | None, node: "_Node",
             want: str) -> bool:
        """Is the want met in this node's world? A row is a violation, so none means met.

        A want with no compiled met-test reads as UNMET, which is the safe direction: it
        makes the search look for a repair rather than declare a want it cannot judge to be
        already satisfied.
        """
        if select is None:
            return False
        return not bindings(query(self._store, select,
                                  self._dataset(node)))

    def _hash_of(self, node: "_Node") -> str:
        """This world's hash — what tells two worlds apart, and so what makes a cycle visible.
        Written onto the world's own catalogue row by the same call that computes it."""
        return hash_named_graph(self._store, node.world)

    # --- what was found ----------------------------------------------------------------------

    def _write(self, want: str, outcome: str, steps: tuple,
               cost: float | None) -> str:
        """The finding, into its own graph in the imaginarium — replaced whole, so a second
        pass over one want leaves one plan and not two.

        WRITTEN WHATEVER THE PASS CONCLUDED. A plan with no steps is an ANSWER, and
        `planning:outcome` is which of the three it is: the want was already met, no lever
        points at it, or the levers there are could not reach it inside the budget. Those
        were fields on a Python record the pass returned and then dropped, so the finding a
        want most needs — that nothing this agent holds points at it — was the one thing
        nothing outside the process could read.

        A GRAPH OF ITS OWN, because that is what a plan is: clearing it means clearing a graph
        rather than removing every subject a plan of up to sixty-four steps MIGHT have used,
        which is a count the writer had to guess at and a shorter plan had to over-clear.

        **THE STEPS ARE WRITTEN IN THE LEDGER'S WORDS.** A step is `execution:Step`, what it
        fills is `execution:fills`, what follows it is `execution:then` — the execution
        layer's vocabulary, because the ledger is where they are going and a step that
        arrived in this layer's words would have to be translated on the way, which is a
        second place the two shapes could disagree. `plans.copy_plan` is a copy.

        THE PLAN ITSELF IS THIS LAYER'S, and so is which want it is for: a plan is what a
        SEARCH found, and a ledger keeps commitments rather than the reasoning that produced
        them. So the root is `planning:Plan` and the ledger reads past it to the steps.
        """
        graph = plan_graph(want)
        clear_graph(self._store, graph)
        node, root = ox.NamedNode(graph), ox.NamedNode(graph)
        quads = [ox.Quad(root, _RDF_TYPE, _P("Plan"), node),
                 ox.Quad(root, ox.NamedNode(FOR_WANT), ox.NamedNode(want), node),
                 ox.Quad(root, ox.NamedNode(OUTCOME), ox.NamedNode(outcome), node)]
        if cost is not None:
            quads.append(ox.Quad(root, ox.NamedNode(COSTS), _decimal(cost), node))
        uris = [ox.NamedNode(f"{graph}.{n}") for n in range(len(steps))]
        for n, (uri, step) in enumerate(zip(uris, steps)):
            quads += [ox.Quad(uri, _RDF_TYPE, _E("Step"), node),
                      ox.Quad(uri, _E("fills"), ox.NamedNode(step.action), node),
                      ox.Quad(uri, _E("partOf"), root, node)]
            if n + 1 < len(uris):
                quads.append(ox.Quad(uri, _E("then"), uris[n + 1], node))
            for parameter, value in step.binding:
                quads.append(ox.Quad(uri, ox.NamedNode(parameter), _term(value), node))
        add_quads(self._store, quads)
        classify(self._store, graph, PLAN_GRAPH, OREXIS + "Derived")
        return graph


# --- what is wanted ------------------------------------------------------------------------
#
#  THE READ LIVES WITH ITS READER. This was `wants.py`, and before that a `Wants` class holding
#  one attribute — the store it was handed. What the class bought is that the GRAPH NAMES and
#  the QUERY TEXT stop being things a caller knows, and that is bought by a function just as
#  well; what the separate MODULE bought was nothing, since the pass is the only thing that
#  asks. `find_want`, the one-or-None cut, went with it: its own name was earned by the shape
#  of its answer and nothing in this tree branches on that shape.
#
#  FIVE FINDERS WERE ONE QUESTION ASKED FIVE WAYS. `find_all`, `find_all_pursued`,
#  `find_all_by_desire`, `find_first_by_desire` and `find_first_by_uri` ran one query with one
#  `where` clause swapped and one graph family named or not; three had no caller outside their
#  own test. The criteria are arguments, said at the call site where a reader can see them.
#
#  IT READS ITS OWN WRITES. Reading through a projection meant a want was invisible between
#  being written and the projection being rebuilt, so every writer had to remember to rebuild
#  before any reader looked. A want is there the moment it is written, and one whose period has
#  CLOSED is not there at all (#645) — the filter is in `_select`, because a want IS its graph.
#
#  IT READS AND DOES NOT WRITE. Writing a want is the derivation's and lives where the want is
#  decided (`derive_wants`); whoever wrote says what changed. Where a want LIVES is
#  `derive_wants.graph_of`, asked of the module that writes it rather than re-exported here.
#
#  WANTS LIVE IN GRAPHS OF WANTS AND IN RECORDS, and this reads both. The derivation's are one
#  graph of wants each, `orexis:arrivedBy orexis:Derived`; a world's ratified want is a graph of
#  wants that is `orexis:Asserted`; the ledger's debts are in its record. Which writer put a
#  want there is the ARRIVAL axis, and `derived=True` is the only caller that cares — it was a
#  graph CLASS of the derivation's own, which is arrival wearing content, and the cost was that
#  a read for the world's wants could not be written at all.
#
#  HOW MANY A READ HANDS BACK unless the caller says otherwise. Every read is bounded,
#  because a collection whose size is the world's is one an author sizes by hoping: wants are
#  tens today — a few roots, a debt per claim in its window — and nothing enforces that, since
#  a market with a busy ledger mints one per claim and a stuck sweep leaves them standing.
#  Generous enough that no correct caller meets it, small enough that meeting it is survivable.
PAGE = 100

#  HOW THE DERIVATION'S WANTS ARRIVED, which `derived=True` narrows to. This was a graph CLASS
#  of its own once, under `orexis:WantGraph`, whose whole content was that the derivation
#  rather than a world put the rows there — the ARRIVAL axis wearing a content class, which the
#  kernel vocabulary forbids in its own words. A want is in a graph of wants whoever wrote it,
#  and which writer is `orexis:arrivedBy`.
DERIVED = OREXIS + "Derived"


def find_wants(store, at: datetime | None = None, *, uri: str = "", desire: str = "",
               derived: bool = False, holder: str = "", limit: int = PAGE,
               offset: int = 0) -> list[str]:
    """The uris of the wants `store` holds that stand at `at`, narrowed by whichever criteria
    are named, ordered by name.

    `uri` asks after one want by name, `desire` after those derived from one desire, and
    `derived` narrows to the family the derivation mints into — as against a debt, which the
    ledger mints when a claim arrives, or a promise, which a level below raises. Said at the
    call site rather than spelled into a method name, so a reader sees what is being asked.

    THE READ TAKES NO OWNER ORDINARILY, and that is not an oversight: one agent, one volume
    (rule 4), so the store IS the scope and a want in it is this agent's by construction. A
    store built with a WHOLE WORLD in it is the exception, and there `holder` is a criterion
    like any other — said at the call site, because the predecessor kept it on the store and a
    read that asks the store whose it is is a read that cannot be given a second answer.

    **A FULL PAGE IS SAID OUT LOUD.** Truncating in silence is the empty-result trap wearing a
    cap: the caller gets a plausible answer and no way to know it was cut. Whoever meets the
    bound either pages or has a leak, and either way someone should see it.
    """
    patterns = "?w a orexis:Want"
    if desire:
        patterns += f" ; prov:wasDerivedFrom <{desire}>"
    where = f"BIND(<{uri}> AS ?w) {patterns} ." if uri else f"{patterns} ."
    found = _select(store, where, at, limit, offset, DERIVED if derived else "", holder)
    #  A PAGE OF ONE IS ALWAYS FULL: `find_want` asks for one, and one standing is the
    #  ordinary answer, not a leak.
    if limit > 1 and len(found) == limit:
        log.warning("wants: a full page of %d at offset %d — page or there is a leak",
                    limit, offset)
    return found


def _select(store, where: str, at: datetime | None, limit: int, offset: int,
            arrival: str, holder: str = "") -> list[str]:
    """Read the graphs of wants holding at `at` — of one arrival where a caller names it — and
    hand back one ordered page.

    A WANT IS ITS GRAPH, so which family it belongs to and whether it still holds are
    questions about the graph — the classification its writer set and the period it set with
    it, never a property on the want — and a want lives in ONE graph, so the text asks both of
    the catalogue itself, by the kinds it names and the instant it stands at
    (a-reader-states-the-kinds-it-reads). No name, and no graph list handed in. It replaced a
    filter on `orexis:bindsWhen`, which named a kind where a graph class already said it (#681).

    **ORDERED BEFORE IT IS CUT.** SPARQL returns a result in whatever order the engine reached
    it, so a `LIMIT` over one is a pick by internal layout — the trap `beliefs.py` records,
    where a bare `LIMIT 1` read the PLANT for every pick until a load order changed. Ordering
    by the want's own name makes a page mean something, makes `offset` walk the collection
    rather than resample it, and makes `find_want` answer the same way twice.
    """
    #  EVERY GRAPH A WANT MAY LIVE IN, where no family is named: the graphs of wants, and
    #  the records — the ledger writes its debts as wants into its own record.
    #  SAID IN THE TEXT, since a want lives in one graph: which kinds, by the catalogue's
    #  rows — every kind a graph is stands on its row — and which instant, by the period
    #  on the same row. The text is handed no default graph; it names what it reads.
    #
    #  AND WHOSE, where the CALLER said so: a reader that means its own says whose, which
    #  is what `graphs_of(store, …, holder=…)` takes for every read that goes through it.
    #  Rule 4 makes the two the same in a volume — one agent, one store — and they are not
    #  the same in a store built with a whole world in it, where the derivation derives under
    #  every holder's desires and this read would otherwise hand back another agent's wants.
    #  A graph saying no owner is anyone's, and a read told nothing keeps every graph.
    now = (at or clock.now()).isoformat()
    kinds = " ".join(f"<{k}>" for k in (WANT, RECORD))
    #  AND HOW IT ARRIVED, where the caller said: the derivation's wants are the graphs of
    #  wants it wrote, and a world's ratified want is a graph of wants the sovereign wrote.
    #  One axis each, asked separately, because they ARE separate.
    came = f"    ?g orexis:arrivedBy <{arrival}> .\n" if arrival else ""
    mine = (f'    OPTIONAL {{ ?g orexis:beliefsOf ?owner }}\n'
            f'    FILTER(!BOUND(?owner) || ?owner = <{holder}>)'
            if holder else "")
    #  `?g a ?kind` IS THE JOIN, not only the filter, and removing it loses a want SILENTLY.
    #  Finding the rows needs no class at all — `GRAPH ?g { ?w a orexis:Want }` with `?g` a
    #  variable already searches every named graph, which is what this does. What the clause
    #  buys is that `?g` appears in the catalogue block's REQUIRED part: drop it and the only
    #  required pattern there is `?catalogue a orexis:CatalogueGraph`, so `?g` is bound solely
    #  inside the OPTIONAL, the left-join happens before the two groups meet, and `?g` binds to
    #  whichever graph HAS a period rather than to this want's. Measured: a debt whose graph
    #  carries no period vanished from the answer, no error and no empty result. Same family as
    #  the `BIND` inside a `UNION` that cannot see an outer variable — a group is a scope.
    #
    #  DISTINCT because `?g` is a variable: a want lives in ONE graph, so the two agree
    #  today, and a projection of one column out of a pattern that binds a graph is a
    #  projection that should not depend on that holding.
    rows = bindings(query(store, f"""
SELECT DISTINCT ?w WHERE {{
  GRAPH ?g {{ {where} }}
  GRAPH ?catalogue {{
    ?catalogue a orexis:CatalogueGraph .
    ?g a ?kind . VALUES ?kind {{ {kinds} }}
{came}{mine}
    OPTIONAL {{ ?g dcterms:temporal ?period . OPTIONAL {{ ?period orexis:start ?start }} OPTIONAL {{ ?period orexis:end ?end }} }} }}
  FILTER(!BOUND(?start) || ?start <= "{now}"^^xsd:dateTime)
  FILTER(!BOUND(?end) || ?end > "{now}"^^xsd:dateTime)
}} ORDER BY ?w LIMIT {int(limit)} OFFSET {int(offset)}""", ()))
    return [r["w"] for r in rows]




#  THE WORLD OF A STORE THAT SCOPED NOTHING. A name for eyes like any other scope's, and the
#  one every want falls to when no predicate it reads is in a scope.
UNSCOPED = "unscoped"


def _scope_name(key) -> str:
    """A name for the imaginarium of one scope group, for eyes. A group keyed by several scopes
    — a want that reaches into more than one — is named for all of them, joined."""
    if isinstance(key, tuple):
        return "-".join(sorted(k.rsplit("/", 1)[-1] for k in key)) or "unscoped"
    return str(key).rsplit("/", 1)[-1]


class _Node:
    """One world the search reached: its graph, the steps that reached it, what they spent,
    and the instant it stands at.

    NOT a dataclass with ordering: two worlds of equal cost must not be compared by their
    fields, so the frontier carries a monotonic counter and this is never the tie-break.
    """

    __slots__ = ("world", "taken", "cost", "at")

    def __init__(self, world: str, taken: tuple, cost: float, at: datetime):
        self.world, self.taken, self.cost, self.at = world, taken, cost, at


_MET_WHEN = rdflib.URIRef("http://example.org/orexis#metWhen")
_EXECUTION = "http://example.org/orexis/execution#"
_PLANNING = "http://example.org/orexis/planning#"
_PROV = "http://www.w3.org/ns/prov#"
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_XSD_DATETIME = ox.NamedNode("http://www.w3.org/2001/XMLSchema#dateTime")





def _decimal(value: float) -> ox.Literal:
    """A cost, as the decimal the ontology says it is. The kernel interprets no literal; this
    only says which type it wrote."""
    return ox.Literal(str(value), datatype=ox.NamedNode(
        "http://www.w3.org/2001/XMLSchema#decimal"))


def _E(local: str) -> ox.NamedNode:
    """One of the ledger's words. A plan is written in them because the ledger is where it is
    going (`plans.copy_plan`), and a translation on the way is a second place the two shapes
    could disagree."""
    return ox.NamedNode(_EXECUTION + local)


def _P(local: str) -> ox.NamedNode:
    """One of this layer's. There is one: which want a plan is FOR, which the ledger's
    vocabulary has no word for because a ledger keeps commitments and not reasons."""
    return ox.NamedNode(_PLANNING + local)


def _term(value: str):
    """One binding's value as the term it is — an IRI where it looks like one, else a literal."""
    return ox.NamedNode(value) if "://" in value else ox.Literal(value)


def _instant(at: datetime) -> ox.Literal:
    return ox.Literal(at.isoformat(), datatype=_XSD_DATETIME)


def _raw(graph: str):
    """A graph named in a rule text as `GRAPH $state` — spliced verbatim, not rendered."""
    from orexis.agent.store import Raw
    return Raw(f"<{graph}>")


# --- the worlds a search makes --------------------------------------------------------------
#
#  **ONE NAMED GRAPH PER SEARCH NODE, AND NONE OF THEM IS EVER MUTATED.** The obvious reading
#  is a single hypothesis graph each step overwrites, and it is wrong: siblings are alive at
#  the same time, so BRANCHING rather than backtracking is the hard case. A world is therefore
#  a VALUE — written once when the node is created, and choosing another branch is binding
#  `$state` to another name. There is nothing to restore because nothing was disturbed.
#
#  THEY LIVE HERE because the search is the only thing that makes one. This was
#  `imaginarium.py`, which by the end held a one-line fill, a fork, a drop and two name
#  builders, every one of them called from this file and nowhere else. What an imaginarium IS
#  stays in `prepare_ground.py`, the module that fills one.

#  Where a node's readings sit. Under the same root as every other graph, because a graph IRI is
#  a graph IRI — but in a store nothing else can open, which is what keeps `orexis:PossibleGraph`'s
#  promise that nothing here survives anything.
_POSSIBLE = GRAPH_PREFIX + "possible/"

#  AND ONE GRAPH PER WANT'S PLAN. A name is for eyes and nothing depends on it: a reader asks
#  the catalogue for `planning:PlanGraph`, and the writer that made it may name what it wrote.
_PLAN = GRAPH_PREFIX + "plan/"


def plan_graph(want: str) -> str:
    """The graph one want's plan is written into — one per want, replaced whole."""
    return _PLAN + quote(local_of(want), safe="")
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")



def apply_action(store: ox.Store, parent: str, name: str, action: str, graphs,
                 *, memo=None, **bind) -> str | None:
    """The world one action past `parent`: forked, marked with where it came from, and the
    action's effect applied to it. The new world's name, or None where the action changes
    nothing and the fork is dropped.

    THE FOUR ACTS IN ORDER, and each is somebody's: `fork` copies (this module's, since a
    world is what a search makes), `effects.apply_effects` deletes what the action replaces
    and adds what it makes true (the action's, since the order and the binding are facts about
    what an effect IS), `mark_world` says where the world came from, and `drop_world` takes
    back a fork that turned out to be no move at all.

    AN ACTION THAT CHANGES NOTHING IS NOT A MOVE — a legal filling whose effect rule produced
    no diff in this world. The world's own hash would reach the same answer, having kept the
    copy; measured, the suite is green either way. Saying it here is what keeps the fork off
    the budget.
    """
    copy_graph(store, parent, name)
    if not apply_effects(store, action, name, graphs, memo=memo, **bind):
        drop_world(store, name)
        return None
    mark_world(store, name, parent, action)
    return name


def mark_world(store: ox.Store, name: str, parent: str, by: str | None = None) -> None:
    """Say of a world what it is, which world it was forked FROM, and what made the fork.

    IN THE STORE AND NOT IN THE NAME. A possible world was called after the path of actions
    reaching it, so the only record of the tree a pass walked was a spelling — and a graph's
    name is for eyes, which no reader may depend on. A ground marks itself the same way and
    says no `planning:by`: what makes a ground is a prediction nobody takes, and its own
    period says when.
    """
    classify(store, name, POSSIBLE_GRAPH if by else GROUND_GRAPH, OREXIS + "Derived")
    quads = [ox.Quad(ox.NamedNode(name), ox.NamedNode(_PROV + "wasDerivedFrom"),
                     ox.NamedNode(parent), ox.NamedNode(catalogue_of(store)))]
    if by:
        quads.append(ox.Quad(ox.NamedNode(name), ox.NamedNode(BY), ox.NamedNode(by),
                             ox.NamedNode(catalogue_of(store))))
    add_quads(store, quads)


def drop_world(store: ox.Store, name: str) -> None:
    """Forget one imagined world's graph (#553, #487), and what the catalogue said of it — its
    hash, written when the search hashed it. A row pointing at a graph that is gone is litter.
    The ground the search starts in is never dropped here."""
    if name != STATE_GRAPH:
        forget_graph(store, name)


def segment_of(row) -> str:
    """One filled action as a name-safe segment: the action and every value it bound.

    EVERY VALUE IS IN IT, and all of them are load-bearing: a schema action yields several rows
    differing in one parameter alone, and a segment built from fewer made two siblings COLLIDE —
    the second child's quads merged into the first's graph, a disk resting on two supports at
    once, and the search saw a menu of duplicates pointing home.
    """
    return "-".join(quote(local_of(part), safe="")
                    for part in (row.action, *(v for _, v in row.binding)))


def world_of(path) -> str:
    """One graph per node, named by the path that reached it.

    The search needs no tree structure added to it and none is wanted: `_Node.taken` is already
    the ordered tuple of steps taken to get here, so the path IS the ancestry
    anything asks about, and what this design adds is a name for it.

    DETERMINISTIC: built from the IRIs themselves rather
    than from `hash()`, which Python salts per interpreter. Nothing outside one plan reads these
    names, so determinism buys reproducibility in a log rather than findability in a store —
    but a name that moved between runs would make two traces of the same search incomparable,
    which is the one thing anybody reads them for.

    Each segment is `segment_of`, which is also how a candidate is named — a world IS its
    path, so the world a candidate reaches is its parent's name plus that candidate's segment.
    """
    return _POSSIBLE + (".".join(segment_of(row) for row in path) or "here")
