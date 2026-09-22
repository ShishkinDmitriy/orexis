"""The search: derive what is wanted, then walk the worlds each step would make.

**One pass, and this is the whole of it.** Handed the beliefs store and the one identifier a
process is told:

1. `derive_wants` judges every desire the store holds, at the present and at every instant a
   prediction reaches, and mints a want per cluster of what the met-tests read unmet;
2. the wants are grouped by SCOPE — which predicates move together, as `scope_actions` wrote
   them — and each group gets an imaginarium of its own, filled from the beliefs by
   `init_imaginarium`;
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
cycle detection by signature, and the met-test. A want is judged by the select its own shape
compiles to, which is the one judgment path (a-want-is-judged-by-its-met-test-and-nothing-else).

See knowledge/domain/planner.md.
"""

from __future__ import annotations

import heapq
import itertools
import logging
from datetime import datetime, timedelta

import pyoxigraph as ox
import rdflib

from orexis.agent import clock
from orexis.agent import violation
from orexis.agent.execution.act import Step
from orexis.agent.ontology import (DESIRE, FORESEEN, OREXIS, PREDICTION, PUBLIC, RECORD,
                                             STATE, WANT, local_of, picks_graph)
from orexis.agent.store import Memo, bindings, graphs_of, query, rdflib_view

from . import effects, relevance, signature
from .derive_wants import derive_wants
from .forget_wants import withdraw
from .imaginarium import Imaginarium, plan_graph
from .ontology import (COSTS, EXHAUSTED, FOR_WANT, GROUND_GRAPH, NO_CANDIDATE,
                       OUTCOME, SATISFIED)
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

    def __init__(self, beliefs: ox.Store, agent_id: str):
        """The beliefs store and the one identifier a process is told. Everything else is
        discovered from the graph, which is rule 1: the world says
        `?a orexis:localId "<id>"`, and who I am and what I act for are the answer rather
        than arguments.
        """
        self.beliefs = beliefs
        self.id = agent_id
        self.picks = picks_graph(agent_id)
        #  THE PASS'S MEMO. The action templates, a rule text and the class definitions cost
        #  more to re-read than a pass can afford and can change only by a write a pass does
        #  not make — a fact about the pass, so the pass owns the memo rather than the store
        #  quietly keeping one (an-agent-is-four-things).
        self.memo = Memo()
        self.uri, self.acts_for = self._identity(agent_id)
        #  The readings graph of the pass in hand — set at `plan`, since which graph that is
        #  is the catalogue's to say and a pass is what stands somewhere.
        self._state: str | None = None
        #  THE PASS'S IMAGINARIA, one per scope, replaced at every `plan`. They are where the
        #  pass wrote what it found, so this is how a caller reaches it — each is asked for
        #  its graphs of class `planning:PlanGraph`, the same by-kind read as everywhere
        #  else. They are memory and die with the Planner, as a plan about a world that has
        #  moved should.
        self.imaginaria: list[Imaginarium] = []

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
        """One pass: derive what is wanted, and find a plan for each of it.

        NOTHING COMES BACK, because everything a pass finds it WRITES: one graph per want in
        the imaginarium it was searched in, `planning:Plan`, holding the steps in the ledger's
        own words and why the pass ended. A reader asks the imaginaria this pass left
        (`self.imaginaria`) for their graphs of that class, exactly as every other read here
        asks by kind. The predecessor returned a Python record beside the graph it had already
        written, so the finding existed twice and only one of the two could cross a layer.

        THE IMAGINARIUM IS PER SCOPE and not per want, which is what the scopes are for: two
        wants whose predicates move together are searched in one imagined world, so a step
        taken for the first is visible to the second. Two in different scopes cannot affect
        each other by construction, so they get a world each and the filling is paid twice
        rather than the worlds being confused once.
        """
        at = now or clock.now()
        self.memo.forget()          # the derivation writes; nothing read before it still holds
        #  TWO ACTS, AND THE PASS IS WHERE THEY MEET. What the desires imply is read off the
        #  desires; what is taken away is read off that answer plus what a plan is walking.
        #  The derivation hands its conclusion on rather than acting on it, so nothing asks a
        #  standing want's own met-test a second time to find out what one pass concluded.
        withdraw(self.beliefs, derive_wants(self.beliefs, at), at)
        wants = find_wants(self.beliefs, at, holder=self.uri)
        #  WHAT CROSSES IS THE FILL'S TO ASK. The caller used to list which of its own graphs
        #  went in; `init_imaginarium` asks the catalogue for the kinds a search reads, and
        #  lays the ground worlds while it is there.
        #  WHAT EACH WANT READS is asked of the graphs of wants, where the derivation wrote
        #  each met-test narrowed to its own witness.
        shapes = rdflib_view(self.beliefs, *graphs_of(self.beliefs, DESIRE, WANT, RECORD, at=at))
        self.imaginaria = []
        for scope, group in self._by_scope(wants, shapes).items():
            imaginarium = Imaginarium(self.beliefs, _scope_name(scope), at)
            self.imaginaria.append(imaginarium)
            #  THE WORLD THE SEARCH STARTS IN is the GROUND holding at the instant it stands
            #  at — asked of the catalogue by class, never named (a graph IRI is an instance).
            self._state = next(iter(graphs_of(imaginarium.store, GROUND_GRAPH, at=at)), None)
            for want in group:
                self._search(imaginarium, want, at)

    def _by_scope(self, wants: list[str], shapes: rdflib.Graph) -> dict:
        """The wants grouped by the scope of what their met-tests READ, order kept.

        THE SCOPES ARE READ, NEVER COMPUTED: `scope_actions` wrote them, and a store holding
        no scope graph is refused rather than guessed at as one scope — a store nobody scoped
        is a store nothing can say what moves together in.

        WHAT A WANT READS IS PARSED OFF ITS MET-TEST, never declared beside it. A want used to
        state the one domain property it was about and this keyed on that, which is the
        planning problem answered before the planner is asked — and in a real world it did not
        even work: the scopes are over RDF PREDICATES while an about is a quantity kind, so
        `water:SoilMoisture` matched no scope and every want fell through to its own name.
        A shape's paths ARE predicates, so this now groups what could interfere and separates
        what cannot.

        A WANT SPANNING SCOPES IS NOT SPLIT, it JOINS them: its group is keyed by every scope
        it reaches, so two wants that could interfere through it share a world. The
        alternative — taking the first scope and ignoring the rest — is the under-approximating
        direction, which separates worlds that can affect each other and loses the interaction
        silently. A want whose shape the walker cannot read reads as ANYTHING and joins
        everything, which is the same safe direction.
        """
        scopes = find_scopes(self.beliefs)
        if scopes is None:
            raise RuntimeError("the store holds no scope graph — scope_actions has not run")
        groups: dict = {}
        for want in wants:
            reads = relevance.reads_of_shape(shapes, rdflib.URIRef(want))
            key = (relevance.ANYTHING if reads is relevance.ANYTHING
                   else tuple(sorted({scopes[str(p)] for p in reads if str(p) in scopes})) or want)
            groups.setdefault(key, []).append(want)
        return groups

    # --- one want ----------------------------------------------------------------------------

    def _search(self, imaginarium: Imaginarium, want: str, at: datetime) -> None:
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

        A CYCLE IS A WORLD ALREADY SEEN, by signature: +3 then −3 returns to the world you
        started in, and a search that does not notice spends its whole budget going nowhere.
        """
        select = self._met_select(imaginarium, want)
        keys = self._keys(imaginarium)
        root = _Node(world=self._state, taken=(), cost=0.0, at=at)
        if self._met(imaginarium, select, root, want):
            self._write(imaginarium, want, SATISFIED, (), 0.0)
            return

        seen = {self._signature(imaginarium, root, keys)}
        tick = itertools.count()
        frontier: list = [(0.0, next(tick), root)]
        best: "_Node | None" = None
        forked = 0
        saw_step = False

        while frontier and forked < BUDGET:
            cost, _, node = heapq.heappop(frontier)
            if best is not None and cost >= best.cost:
                break                       # the first achiever's bound refuses the rest
            for step in self._steps(imaginarium, node, want):
                saw_step = True
                if forked >= BUDGET:
                    break
                child = self._take(imaginarium, node, step, want)
                if child is None:
                    continue
                forked += 1
                fingerprint = self._signature(imaginarium, child, keys)
                if fingerprint in seen:
                    imaginarium.drop(child.world)
                    continue
                seen.add(fingerprint)
                if self._met(imaginarium, select, child, want):
                    if best is None or child.cost < best.cost:
                        best = child
                    continue
                heapq.heappush(frontier, (child.cost, next(tick), child))

        if best is not None:
            self._write(imaginarium, want, SATISFIED, best.taken, best.cost)
            return
        #  THE TWO SILENCES ARE NOT THE SAME, and telling them apart is most of why an empty
        #  plan is written at all: NO CANDIDATE says no lever this agent holds points at this
        #  want (equip me), EXHAUSTED says levers exist and no bounded sequence of them lands
        #  inside the region (my doses are too coarse, or my region is too tight for them).
        self._write(imaginarium, want, EXHAUSTED if saw_step else NO_CANDIDATE, (), None)

    # --- the moves ---------------------------------------------------------------------------

    def _steps(self, imaginarium: Imaginarium, node: "_Node", want: str) -> list[Step]:
        """What this world affords — one step per action per legal filling, name-ordered."""
        return find_steps(imaginarium.store, self.uri, self.picks,
                          graphs=self._dataset(imaginarium, node), memo=imaginarium.memo)

    def _take(self, imaginarium: Imaginarium, node: "_Node", step: Step,
              want: str) -> "_Node | None":
        """The world one step past this one, or None where the step's effect says nothing.

        What a step costs is the action's own `orexis:costs` select and what it takes to land
        is its `orexis:landsAt`, both run against the world the step is taken IN — a package
        declares them because they are claims about that package's own actions.
        """
        graphs = self._dataset(imaginarium, node)
        binding = self._bind(step, node, want)
        added, retracted = effects.apply(imaginarium.store, step.action, graphs,
                                         memo=imaginarium.memo, **binding)
        if not added and not retracted:
            #  AN ACTION THAT CHANGES NOTHING IS NOT A MOVE. It is a legal filling whose
            #  effect rule produced no diff in this world, and forking on it would spend a
            #  world to arrive where we already are.
            return None
        spent = effects.cost_of(imaginarium.store, step.action, graphs,
                                memo=imaginarium.memo, **binding) or 0.0
        lands = effects.lands_after(imaginarium.store, step.action, graphs,
                                    memo=imaginarium.memo, **binding) or 0.0
        taken = node.taken + (step,)
        world = imaginarium.reached(node.world, taken, added, retracted)
        #  AND WHAT THE VOCABULARY ENTAILS OF WHAT THE STEP WROTE (#576): a predicted reading's
        #  bands, asserted in the forked world so the met-test can read what the reading IS
        #  rather than walk a subclass path to work it out.
        imaginarium.entailed(world, added, self._keys(imaginarium))
        return _Node(world=world, taken=taken, cost=node.cost + spent,
                     at=node.at + timedelta(seconds=lands))

    def _keys(self, imaginarium: Imaginarium) -> dict:
        """WHICH PREDICATES IDENTIFY A NODE, per class a package declared `orexis:keyedBy` —
        what makes a re-stamped reading the same fact and a new value a different one. Read
        off public knowledge, which nothing writes once the imaginarium is filled, so it is
        the pass's to keep."""
        return imaginarium.memo.get(("keys",), lambda: signature.keys_of(
            lambda text: query(imaginarium.store, text,
                               graphs_of(imaginarium.store, PUBLIC))))

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

    def _dataset(self, imaginarium: Imaginarium, node: "_Node") -> list[str]:
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
        spoken_for = {*graphs_of(imaginarium.store, STATE),
                      *graphs_of(imaginarium.store, PREDICTION),
                      *graphs_of(imaginarium.store, GROUND_GRAPH)}
        graphs = [g for g in graphs_of(imaginarium.store, *FORESEEN, at=node.at)
                  if g not in spoken_for]
        return [*graphs, node.world] if node.world else graphs

    # --- the verdict -------------------------------------------------------------------------

    def _met_select(self, imaginarium: Imaginarium, want: str) -> str | None:
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
        shapes = self._shapes(imaginarium)
        root = shapes.value(rdflib.URIRef(want), _MET_WHEN)
        if root is None:
            return None
        return violation.unmet_select(shapes.cbd(root), root)

    def _shapes(self, imaginarium: Imaginarium) -> rdflib.Graph:
        """Every want and desire this agent holds, as one rdflib graph — where a met-test is
        declared. Per pass, because a search writes none of them: a rebuild in the middle
        would hand two depths two different wants."""
        return imaginarium.memo.get(("shapes",), lambda: rdflib_view(
            imaginarium.store, *graphs_of(imaginarium.store, DESIRE, WANT, RECORD)))

    def _met(self, imaginarium: Imaginarium, select: str | None, node: "_Node",
             want: str) -> bool:
        """Is the want met in this node's world? A row is a violation, so none means met.

        A want with no compiled met-test reads as UNMET, which is the safe direction: it
        makes the search look for a repair rather than declare a want it cannot judge to be
        already satisfied.
        """
        if select is None:
            return False
        return not bindings(query(imaginarium.store, select,
                                  self._dataset(imaginarium, node)))

    def _signature(self, imaginarium: Imaginarium, node: "_Node", keys: dict) -> frozenset:
        """This world's canonical facts — what tells two worlds apart, and so what makes a
        cycle visible. Keyed nodes compare by their key rather than by their blank node's
        name, which is why a re-stamped reading is the same fact and a new value is not."""
        return signature.facts(
            (ox.Triple(q.subject, q.predicate, q.object)
             for q in imaginarium.quads_for_pattern(graph=node.world)), keys)

    # --- what was found ----------------------------------------------------------------------

    def _write(self, imaginarium: Imaginarium, want: str, outcome: str, steps: tuple,
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
        imaginarium.forget_plan(graph)
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
        imaginarium.note(quads)
        imaginarium.classify_plan(graph, want)
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
