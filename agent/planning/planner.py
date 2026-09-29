"""The Planner: the one thing the rest of the tree uses, and the one place the acts are
sequenced.

**A STAR, NOT A CHAIN.** Every act of the package — laying the ground, weighing, deriving,
admitting, taking, extracting a plan, publishing it — is a function over the store that calls
no other act; what it needs of another's work it reads off the rows the other wrote. This
class is the orchestration: `plan` is the pass, `search` is one want's search, `expand` is
one iteration of it, and each is a method here rather than a module, so a reader who wants
to know what happens in what order reads one file, and a reader who wants to know what one
act does reads that act alone. It was a chain — the pass called the search, the search called
the expansion and the extraction, the expansion called the admission and the taking, the
derivation called the weighing — and what a pass did was spread across the files it
went through.

**One pass, and this is the whole of it.** Handed the beliefs store and the one identifier a
process is told:

1. per scope, an imaginarium — the Planner's, kept from pass to pass: `prepare_ground` copies
   what a rule may read, or refreshes the copy; `lay_ground` lays one ground per period the
   predictions make; `reroot` finds the world the last pass imagined that the present landed
   in, keeps its cone under the new ground and drops the rest;
2. every desire is weighed in every ground (`weigh`, over what `unweighed` lists),
   `derive_wants` reads the weighings and mints a want per cluster of what they read unmet,
   and `withdraw` takes away what no desire implies and no intention is walking;
3. per want that no intention is walking, `search`: the want is weighed in the present
   ground, and `expand` opens the cheapest open world until nothing is open, the cheapest
   achiever refuses the top, or the budget is spent — an iteration admits the world's
   candidates, takes each and weighs what it reached; then `extract_plan` writes what the
   want's weighings come to;
4. `publish_plan` hands every plan no intention is already walking DOWN, through the belief base:
   an `orexis:PlanGraph` published once in execution's words, each step a bridge may keep below marked so
   (`bridge.keeps`), which the executor takes up and commits.

And before any of it, every step an intention stands at that is kept below and has fallen due is
given the want that keeps it (`refine`), which the executor then waits on.

Nothing comes back but the graphs written: everything a pass finds it WRITES, and
`self.imaginaria` is how a reader reaches it. Nothing here commits and nothing here calls the
executor: planning and execution meet at the store (a-package-starts-itself) — the plans handed
down, the wants that keep a step below, and the intentions, which planning reads by pattern
to know what is walked and where each stands.

**THE IMAGINARIUM OUTLIVES THE PASS.** Called every minute, a planner that imagined afresh
each time searched the same cone three times over and handed down three intentions for
one want — measured before this was built. What the last pass imagined is kept, and the next
pass begins by asking which of those worlds the present IS (`reroot`, by hash): the plan
landed as predicted and the cone beneath the landing is the search already done from here;
nothing happened and the whole cone is kept under the new ground; the world surprised the
agent and everything goes. A want an intention is walking is not searched again and its plan
is not handed down again: the world has not answered yet, and re-deciding is what the
executor's verdict on a step is for.

**THE SEARCH'S STATE IS IN THE STORE, AND THE FRONTIER IS A QUERY.** What is true of a world
whoever asks is on its row; what a want's search worked out about it is a `planning:Weighing`
— met there, on the frontier, opened — and a candidate passed over is weighed too. `search`
called again on the same imaginarium takes up where it stopped, which `tests/test_search.py`
holds. The frontier is ordered by cost alone, uniform-cost search, and then by the order the
worlds were minted; the first achiever bounds the rest.

WHAT THE PREDECESSOR'S SEARCH HAD AND THIS DOES NOT, each an absence rather than an oversight
(an-agent-is-four-things): the relevance closure; remembered plans; the trace, of which the
weighings are what a search itself needs back; and the A* key. The re-root it has, as
`reroot`, and by hash alone.

See knowledge/domain/planning/planner.md.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime

import pyoxigraph as ox
import rdflib

from agent import clock, metrics
from agent.ontology import ACTION, PUBLIC, RECORD, local_of
from agent.store import (Memo, Raw, forget_graph, bind, bindings, catalogue_of, graphs_of, instant, query, rdflib_view,
                         remember, rows, update)

from . import footprint
from . import metrics as reported
from .admit import admit
from .bridge import keeps
from .derive_wants import derive_wants
from .extract_plan import extract_plan
from .find_scopes import find_scopes
from .refine import refine
from .find_wants import find_wants
from .lay_ground import lay_ground
from .ontology import DESIRE, PLAN_GRAPH, PLANNING, SCOPE_GRAPH, SHAPES, WANT
from .prepare_ground import prepare_ground
from .publish_plan import publish_plan
from .reroot import reroot
from .scope_actions import scope_actions
from .take import take
from .unweighed import unweighed
from .weigh import weigh
from .withdraw import withdraw
from .world_at import world_at

log = logging.getLogger("planner")

#  THE CEILING ON WHAT A SEARCH MAY SPEND, in the unit it spends: candidates weighed for one
#  want — every fork made, and every candidate passed over because its fork repeated a world
#  already seen, since both cost a copy and a rule (#494). It is a ceiling on COMPUTE and so
#  not a preference an agent may revise — the predecessor made it a pick a sovereign could
#  state, and that pick is one of the things that returns with the machinery for reading
#  picks. Sized for a plant, whose pass forks a handful.
BUDGET = 32

#  THE WORLD OF A STORE THAT SCOPED NOTHING. A name for eyes like any other scope's, and the
#  one every want falls to when no predicate it reads is in a scope.
UNSCOPED = "unscoped"

#  WHAT A STEP PREDICTS, off the intentions — execution's word, read from the layer beneath.
_IN_SCOPE_Q = """SELECT ?a WHERE { ?a planning:inScope $scope }"""

#  EVERY WANT KEPT BELOW FOR A STEP, with its graph and the step.
_REFINED_Q = """
SELECT ?want ?g ?step WHERE { GRAPH ?g { ?step execution:keptBy ?want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph } }"""

#  WHAT THIS AGENT IS WALKING, off execution's rows in the belief base: every want a standing
#  intention pursues, and every want a plan published and adopted by no intention yet pursues.
_WALKING_Q = """
SELECT DISTINCT ?want WHERE {
  { GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
               FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
  UNION
  { GRAPH $cat { ?plan a orexis:PlanGraph } GRAPH ?plan { ?plan execution:pursues ?want }
    FILTER NOT EXISTS { GRAPH ?h { ?i execution:adopts ?plan } } } }
ORDER BY ?want"""

#  THE STEP EVERY STANDING INTENTION STANDS AT.
_STANDING_AT_Q = """
SELECT DISTINCT ?step WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step .
                                         FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }"""

#  EVERY STEP AN INTENTION STANDS AT THAT IS KEPT BELOW, HAS FALLEN DUE AND HAS NO WANT KEEPING IT
#  YET, with what it predicts.
_KEPT_DUE_Q = """
SELECT ?step ?predicts WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } }
  GRAPH ?plan { ?step execution:keptBelow true ; execution:predicts ?predicts .
                OPTIONAL { ?step execution:notBefore ?due } }
  FILTER(!BOUND(?due) || ?due <= $now)
  FILTER NOT EXISTS { GRAPH ?h { ?step execution:keptBy ?w } } }
ORDER BY ?step"""

#  EVERY STEP AN INTENTION STANDS AT THAT HAS FALLEN DUE, NOT BEEN TAKEN AND IS NOT KEPT BELOW, with
#  the action it fills — what the present must still admit for it to be taken.
_DUE_HEADS_Q = """
SELECT ?step ?action WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done }
             FILTER NOT EXISTS { ?act execution:of ?step } }
  GRAPH ?plan { ?step planning:fills ?action . OPTIONAL { ?step execution:notBefore ?due }
                FILTER NOT EXISTS { ?step execution:keptBelow true } }
  FILTER(!BOUND(?due) || ?due <= $now) }
ORDER BY ?step"""

#  AN ACTION'S PRECONDITION AND THE PARAMETERS IT TAKES, and a step's value for each.
_PRECONDITION_Q = """SELECT ?text ?takes WHERE { $action planning:precondition ?text . OPTIONAL { $action orexis:takes ?takes } }"""
_FILLING_Q = """SELECT ?p ?v WHERE { GRAPH ?plan { $step ?p ?v } }"""

#  EVERY STEP OF A PLAN PUBLISHED WHOSE ACTION IS TAKEN FICTIVELY, with what it predicts.
_FICTIVE_STEPS_Q = """
SELECT ?step ?predicts WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?action ; execution:predicts ?predicts }
  ?action execution:implementation/execution:operation ?op . ?op a execution:Fictive }
ORDER BY ?step"""

#  THE CATALOGUE IS BOUND, NOT FOUND, IN THE HOT READS: `GRAPH ?cat { ?cat a
#  orexis:CatalogueGraph . … }` makes the engine evaluate the group per named graph, and with
#  a store of sixteen possible worlds each such read cost 0.5 to 1.0 ms where a read over one
#  bound graph costs 0.1 to 0.2 — measured on the two-disk bench. The name is asked of the
#  store once per pass (`catalogue_of`, remembered) and spliced as `$cat`: a reader asking
#  the store for the catalogue's name is what the rule allows; spelling it is what it refuses.
#  THE TOP OF THE FRONTIER: the cheapest open world, its weighing, and the bound. The open
#  weighings' worlds, cheapest first and then in the order they were made — the tie-break that
#  keeps a uniform-cost search going layer by layer rather than diving alphabetically into
#  whichever action sorts first — and beside the top, what the cheapest achiever so far spent.
#  The ground spent nothing and says nothing, so an absent number reads as nought.
#  AND WHAT THE SEARCH HAS SPENT so far — every weighing but the ground's — in the same
#  question, since an iteration asks both and a round trip is what a small store pays for.
#  THE KEY IS SPENT PLUS REMAINING — A*, where the want declares an estimate, uniform-cost
#  where it does not, since a weighing with no `planning:remaining` reads nought. The estimate
#  is on the weighing already, written when the world was weighed, so ordering by it costs
#  the frontier nothing per iteration. Measured on the predecessor: hanoi 56 forks to 50, the
#  courier's corner delivery 198 to 78; this tree's figures are in the runbook.
EXHAUSTED = PLANNING + "Exhausted"
#  THE WANTS MET IN THE PRESENT GROUND: a weighing of a want in the ground just laid, saying met.
_MET_NOW_Q = """
SELECT DISTINCT ?for WHERE {
  GRAPH ?cat { ?x planning:weighs $ground ; planning:for ?for ; planning:met true .
               ?cat a orexis:CatalogueGraph }
  GRAPH ?any { ?for a planning:Want } }"""

_OUTCOMES_Q = "SELECT ?o WHERE { GRAPH $plan { ?p a planning:Plan ; planning:outcome ?o } }"

_FRONTIER_Q = """
SELECT ?w ?spent ?remaining ?minted ?weighing ?best ?used WHERE {
  GRAPH $cat { ?weighing a planning:Weighing ; planning:for $want ; planning:open true ; planning:weighs ?w .
    OPTIONAL { ?w planning:spent ?s } OPTIONAL { ?w planning:minted ?m }
    OPTIONAL { ?weighing planning:remaining ?r } }
  OPTIONAL { SELECT (MIN(?bs) AS ?best) WHERE {
    GRAPH $cat { ?y a planning:Weighing ; planning:for $want ; planning:met true ; planning:weighs ?bw .
      ?bw planning:spent ?bs } } }
  { SELECT (COUNT(?x) AS ?used) WHERE {
    GRAPH $cat { ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
      FILTER NOT EXISTS { ?u a planning:GroundGraph } } } }
  BIND(COALESCE(?s, 0.0) AS ?spent) BIND(COALESCE(?m, 0) AS ?minted) BIND(COALESCE(?r, 0.0) AS ?remaining) }
ORDER BY (?spent + ?remaining) ?minted LIMIT 1"""

#  A WORLD OPENED: off the frontier, and said to have been expanded.
_CLOSE_U = """
DELETE { GRAPH ?cat { $weighing planning:open ?o } }
INSERT { GRAPH ?cat { $weighing planning:expanded true } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $weighing planning:open ?o } }"""


class Planner:
    """One agent's planning: the pass, one want's search, and one iteration of it, each a
    method that sequences the package's acts and reads the store between them."""

    def __init__(self, beliefs: ox.Store, agent_id: str, budget: int = BUDGET):
        """The beliefs store, the one identifier a process is told, and how much a search may
        spend — a ceiling on compute in the unit the search spends,
        which is a container's to size from a measured cost per candidate and not the
        agent's to revise.

        Everything else is discovered from the graph, which is rule 1: the world says
        `?a orexis:localId "<id>"`, and who I am is the answer rather than an argument.

        A plan is published into the beliefs, as an `orexis:PlanGraph`, and what is walked is
        read off the intentions there; the Planner holds no executor.
        """
        self.beliefs = beliefs
        self.id = agent_id
        self.budget = budget
        self.uri = self._identity(agent_id)
        #  THE PLANNER'S IMAGINARIA, one per scope, kept from pass to pass and refreshed at
        #  every `plan`. They are where a pass wrote what it found, so this is how a caller
        #  reaches it — each is asked for its graphs of class `planning:PlanGraph`, the same
        #  by-kind read as everywhere else. They are memory and die with the Planner; what
        #  outlives the Planner is the intentions, a graph of the beliefs.
        self.imaginaria: dict[str, ox.Store] = {}
        self.handed: list[tuple[str, str]] = []
        self.reached: set[str] = set()
        self.blocked: list[str] = []
        #  TELEMETRY AND NOT A ROW: per want, when it was first searched and in how many passes,
        #  kept only where a metrics sink is loaded and said at its adoption. No plan branches
        #  on it, so it is memory and never a belief.
        self._searches: dict[str, list] = {}

    def _identity(self, agent_id: str) -> str:
        """Who this agent is, off the world graph.

        `a orexis:Agent` is load-bearing and not decoration: a plant, a sensor and a valve
        carry `orexis:localId` too, and a world names its subject after its agent — so the
        bare pattern matches two things and `LIMIT 1` picks by the store's internal order,
        which a change to load order silently flips. It did once, and every pick read asked
        the PLANT.
        """
        found = bindings(query(self.beliefs, f"""
SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId "{agent_id}" }} LIMIT 1""",
                               graphs_of(self.beliefs, PUBLIC)))
        if not found:
            raise LookupError(
                f"no agent with localId '{agent_id}' in this store — was the world loaded "
                "before the planner was built?")
        return found[0]["a"]

    # --- the pass ------------------------------------------------------------------------

    def plan(self, now: datetime | None = None) -> list[str]:
        """One pass: an imaginarium per scope, every desire weighed in every ground, the wants
        derived, each searched, and the plans handed down. The graphs written in the beliefs — the
        plans handed down and the wants that keep a step below — for whoever hears what was written.

        THE IMAGINARIUM COMES FIRST, AND THE DERIVATION RUNS INSIDE IT. What a desire reads at
        a future instant is what the GROUND holding then says — the present with each
        prediction applied in turn, one graph per period — and a ground exists only where
        `lay_ground` has laid one. Judged against the belief base instead, a desire sees the
        reading AND the prediction of it at once, and a shape holds over every value, so the
        stale one still violates: a tank low now with a prediction refilling it reads unmet for
        ever.

        WHAT IS DERIVED IS KEPT, AND WITHDRAWN BY ITS OWN RULE. The imaginarium outlives the
        pass, so a want the last pass minted is still here; `withdraw` takes away what the
        derivation no longer implies, except what an intention is walking, which is kept
        whatever its desire reads.

        ONE PER SCOPE OF THE STORE, which is what the scopes are for: the wants of a scope are
        searched in one imaginarium, whose worlds they share — a world one want's search made,
        another's weighs without forking it again — and two in different scopes cannot affect
        each other by construction. The scopes are READ and never computed — `scope_actions`
        wrote them, and a store holding no scope graph is refused rather than guessed at.

        AND THE LAST ACT IS `publish_plan`, handing each plan down into the beliefs: the
        imaginarium is the Planner's and dies with it, so an intention, committed from what was
        handed down, is the only thing a pass leaves the agent. A plan with no steps does not cross — an answer is not a
        commitment — and neither does a plan for a want an intention is already walking.
        """
        at = now or clock.now()
        scopes = find_scopes(self.beliefs)
        if scopes is None:
            raise RuntimeError("the store holds no scope graph — scope_actions has not run")
        #  A STORE WITH NO ACTION HAS ONE WORLD, not none: `scope_actions` writes the scope
        #  graph whatever it finds, and a desire in a scoped, empty store still has to be
        #  judged, to say that no lever points at it.
        walking = self.walking()
        self._withdraw_orphaned_refinements(walking)
        written = self._keep_below(at)
        #  WHAT THE PASS SAYS, for whoever runs it to signal: the plans it published with their wants,
        #  the wants an intention walks that the present meets, and the steps it can no longer take.
        self.handed, self.reached, self.blocked = [], set(), []
        #  HOW LONG EACH PART OF THE PASS TOOK, where a metrics sink is loaded: in real seconds by
        #  `perf_counter`, since the agent's clock may run fast and a test's ticks per read.
        lap = metrics.Laps() if metrics.recording() else None
        searched: set[str] = set()
        for _scope in sorted(set(scopes.values())) or [UNSCOPED]:
            store = self.imaginaria.setdefault(_scope, ox.Store())
            prepare_ground(self.beliefs, store)
            #  THE PASS'S MEMO, one per world: the action templates, a rule text, the graph
            #  list per instant and the shapes cost more to re-read than a pass can afford
            #  and can change only by a write the search does not make.
            memo = Memo()
            present, *_ = lay_ground(store, at)
            reroot(store, present)
            if lap:
                lap("ground")
            self.blocked += self._blocked(store, present, at, memo)
            for pair in unweighed(store, memo=memo):
                #  GROUNDS ONLY. A candidate the budget left untaken in a world it cut is
                #  unweighed too, and weighed here it would never be offered to the expansion
                #  that takes it: its world would never be forked, and the search the passes
                #  after were to finish would empty its frontier short of the answer — the
                #  courier's corner delivery did, at sixteen candidates a pass.
                if not pair.get("from"):
                    weigh(store, pair["for"], pair["about"], memo=memo)  # every desire, every ground
            if lap:
                lap("weigh")
            #  A WANT MET IN THE PRESENT IS REACHED, and one-shot: it goes, from here and from the
            #  beliefs, where a want the world authored lives — unless a plan is still walking it,
            #  whose last step the executor has yet to see answered.
            met_now = {r["for"] for r in rows(store, _MET_NOW_Q, (), ground=present)}
            self.reached |= met_now & walking
            reached = met_now - walking
            withdraw(store, derive_wants(store, at) | walking, at, reached=reached)
            if reached:
                withdraw(self.beliefs, None, at, reached=reached)
            if lap:
                lap("derive")
            memo.forget("shapes", "select")
            #  THE SHAPES ARE FORGOTTEN AFTER THE DERIVATION, because the derivation WRITES
            #  them: the shapes crossed to judge the desires hold no want, and a search that
            #  reused them compiled every want's met-test to nothing and reported Exhausted —
            #  measured the day the pass became one method. Only the shapes and what was
            #  compiled from them: the rule texts, the templates and the graph lists per
            #  instant are as good after the derivation as before, and a fresh memo cost a
            #  fifth of a pass re-reading them, measured.
            #  THE SHAPES, CROSSED ONCE PER SCOPE and after the derivation, under the memo's
            #  key so `weigh` finds the same crossing.
            #  THE SCOPE'S OWN ACTIONS are what its worlds admit; a store of no scope admits all.
            only = None if _scope == UNSCOPED else {
                r["a"] for r in rows(self.beliefs, _IN_SCOPE_Q, graphs_of(self.beliefs, SCOPE_GRAPH), scope=_scope)}
            shapes = memo.get(("shapes",), lambda: rdflib_view(store, *graphs_of(store, DESIRE, WANT, RECORD, SHAPES)))
            for want in _of_scope(store, shapes, self.uri, _scope, scopes, at):
                if want in walking:
                    continue                # a want a plan is walking is not planned again
                self.search(store, want, budget=self.budget, only=only, memo=memo, scope=_scope)
                searched.add(want)
            if lap:
                lap("search")
            handed = publish_plan(store, self.beliefs, self.uri, walking)
            self._mark_kept(handed)
            written += handed
            self.handed += [(plan, reported.pursued_by(self.beliefs, plan)) for plan in handed]
            walking = self.walking()        # a want handed down from one scope is walked in the next
            if lap:
                self._adopted(store, handed, present, _scope, memo)
                lap("publish")
        if lap:
            reported.PLANNER({**lap.spent, "wants": len(searched)})
            #  A WANT NO LONGER SEARCHED — reached, withdrawn, or walked — takes its tally with it.
            self._searches = {w: s for w, s in self._searches.items() if w in searched}
        return written

    # --- a step kept one level down ----------------------------------------------------------

    def walking(self) -> set[str]:
        """Every want this agent is walking, off execution's rows in the belief base: pursued by a
        standing intention, or by a plan handed down and not yet taken up. Neither searched again
        nor withdrawn, whatever its desire reads."""
        cat = Raw(f"<{catalogue_of(self.beliefs)}>")
        return {r["want"] for r in rows(self.beliefs, _WALKING_Q, (), cat=cat)}

    def _keep_below(self, at: datetime) -> list[str]:
        """Give every step an intention stands at that is kept below and has fallen due the want
        that keeps it, one level down (`refine`), which the executor waits on. The want graphs."""
        minted = []
        for r in rows(self.beliefs, _KEPT_DUE_Q, (), now=instant(at)):
            predicted = json.loads(r["predicts"])
            want = refine(self.beliefs, self.uri, r["step"], predicted.get("adds", ()), at, predicted.get("retracts", ()))
            if want is not None:
                minted += [g["g"] for g in rows(self.beliefs, _REFINED_Q, ()) if g["want"] == want]
        return minted

    def _blocked(self, store: ox.Store, present: str, at: datetime, memo: Memo) -> list[str]:
        """Every step an intention stands at, fallen due and not yet taken, that the `present` ground
        of `store` no longer admits: its action's precondition answers there with no row carrying
        the step's own value for every parameter the action takes. Only an action this scope's
        imaginarium holds is asked; a step of another scope's is that scope's to judge."""
        blocked = []
        actions = graphs_of(store, ACTION)
        world = None
        for head in rows(self.beliefs, _DUE_HEADS_Q, (), now=instant(at)):
            found = rows(store, _PRECONDITION_Q, actions, action=head["action"])
            if not found:
                continue
            world = world or world_at(store, present, memo=memo)
            takes = {r["takes"] for r in found if r.get("takes")}
            filling = {local_of(r["p"]): r["v"] for r in rows(self.beliefs, _FILLING_Q, (), step=head["step"])
                       if r["p"] in takes}
            answers = bindings(query(store, bind(found[0]["text"], me=self.uri), world))
            if not any(all(row.get(k) == v for k, v in filling.items()) for row in answers):
                log.info("%s: %s can no longer be taken — the present admits it no more", self.id, local_of(head["step"]))
                blocked.append(head["step"])
        return blocked

    def _mark_kept(self, handed: list[str]) -> None:
        """Say of every step of a plan handed down that a bridge keeps below — one taken
        fictively whose predicted fact a rule the store holds concludes — that it is
        `execution:keptBelow`: not the executor's to take fictively."""
        actions = graphs_of(self.beliefs, ACTION)
        for plan in handed:
            for r in rows(self.beliefs, _FICTIVE_STEPS_Q, actions, plan=Raw(f"<{plan}>")):
                if keeps(self.beliefs, json.loads(r["predicts"]).get("adds", ())):
                    update(self.beliefs, f'INSERT DATA {{ GRAPH <{plan}> {{ <{r["step"]}> execution:keptBelow true }} }}')

    def _withdraw_orphaned_refinements(self, walking: set[str]) -> None:
        """A want kept below for a step no intention stands at any more — the step answered, or
        its intention failed or superseded — is nothing's: withdrawn, so a plan in flight never
        outlives what it was for."""
        standing_at = {r["step"] for r in rows(self.beliefs, _STANDING_AT_Q, ())}
        for r in rows(self.beliefs, _REFINED_Q, ()):
            if r["step"] not in standing_at and r["want"] not in walking:
                forget_graph(self.beliefs, r["g"])
                #  AND WHAT EACH IMAGINARIUM SEARCHED FOR IT: its plan outlives the pass there,
                #  and a plan whose intention is over is handed down again unless it goes.
                for store in self.imaginaria.values():
                    withdraw(store, None, clock.now(), reached={r["want"]})
                log.info("%s: withdrew %s, since nothing stands at the step it kept", self.id,
                         r["want"].rsplit("#", 1)[-1])

    # --- what a runtime asks after a pass ---------------------------------------------------

    def standing(self, at: datetime | None = None) -> list[str]:
        """Every want that stands after the last pass, across the imaginaria — which is where
        the derivation mints them, so the beliefs hold none. Empty, with nothing walking, is
        every desire met."""
        at = at or clock.now()
        return sorted({w for store in self.imaginaria.values() for w in find_wants(store, at)})

    def holds_a_desire(self) -> bool:
        """Whether the agent holds any desire — what keeps it running when nothing is wanted now,
        since a desire asks at every instant. The container's question and planning's word."""
        return bool(rows(self.beliefs, "SELECT ?d WHERE { ?d a planning:Desire } LIMIT 1",
                         graphs_of(self.beliefs, DESIRE)))

    def exhausted(self) -> bool:
        """Whether any search of the last pass stopped on its budget rather than on an answer,
        `planning:Exhausted` on its plan — the next pass continues it, where a want standing
        with no exhausted search is one nothing this agent holds reaches."""
        return any(r["o"] == EXHAUSTED
                   for store in self.imaginaria.values()
                   for plan in graphs_of(store, PLAN_GRAPH)
                   for r in rows(store, _OUTCOMES_Q, (), plan=plan))

    @staticmethod
    def scope(beliefs: ox.Store) -> None:
        """Write the scopes a pass reads — `scope_actions`, the boot's act, since a store with
        no scope graph is refused rather than guessed at."""
        scope_actions(beliefs)

    # --- one want ------------------------------------------------------------------------

    def search(self, store: ox.Store, want: str, *, budget: int = BUDGET, only=None,
               memo: Memo | None = None, scope: str | None = None) -> None:
        """Plan for `want` from the present ground, spending at most `budget` candidates, and
        write the plan — whatever the search concluded, since an empty plan is an answer and
        `planning:outcome` says which of the three.

        Nothing is carried across an iteration but what the store says: called again on the
        same imaginarium, this weighs nothing twice, opens what was left open, and writes the
        plan the weighings come to.

        THE BUDGET IS THIS CALL'S. What the want's search spent before — a search the budget
        cut short, a cone kept across the pass — is on the rows already, and a ceiling on
        compute is a ceiling on what is spent NOW; so the ceiling stands that much above what
        stands, and a want with forty weighings kept from yesterday is not refused its first
        fork today.

        WHERE A METRICS SINK IS LOADED the search is said as it ends — how long it took in real
        seconds, the budget, the candidates it weighed and how it ended — one event per want per
        pass, never one per weighing, and the want's tally of searches is kept for its adoption.
        """
        memo = Memo() if memo is None else memo
        started = time.perf_counter() if metrics.recording() else None
        for pair in unweighed(store, for_=want, memo=memo):
            if not pair.get("from"):
                weigh(store, want, pair["about"], memo=memo)             # the root: the present
        ceiling = _spent(store, want, memo) + budget
        while (spent := self.expand(store, want, budget=ceiling, only=only, memo=memo)) is not None \
                and spent < ceiling:
            pass
        extract_plan(store, want)
        if started is not None:
            tally = self._searches.setdefault(want, [started, 0])
            tally[1] += 1
            reported.report_search(store, want, took=time.perf_counter() - started, budget=budget,
                                   weighed=_spent(store, want, memo) - (ceiling - budget), scope=scope)

    def _adopted(self, store: ox.Store, handed: list[str], present: str, scope: str, memo: Memo) -> None:
        """Say each plan this pass handed down from `store` (`metrics.report_adoption`), with the
        tally of its want's searches, which goes with it."""
        for plan in handed:
            want = reported.pursued_by(self.beliefs, plan)
            if want is None:
                continue
            first, passes = self._searches.pop(want, (None, 0))
            reported.report_adoption(store, self.beliefs, want, first=first, passes=passes,
                                     weighed=_spent(store, want, memo), present=present, scope=scope)

    def desire_of(self, want: str) -> str | None:
        """The local name of the desire `want` was derived under, off whichever imaginarium holds
        it — or None, for a want the world authored or a step kept below — for the runtime's
        events about a want."""
        return next((d for store in self.imaginaria.values() if (d := reported.desire_of(store, want))), None)

    def gauges(self) -> list:
        """Planning's gauges, sampled over the imaginaria this Planner keeps — the one store a plan,
        a world and a weighing are written in — for the runtime's flush (`metrics.py` beside this)."""
        return reported.gauges(self.imaginaria.values())

    # --- one iteration -------------------------------------------------------------------

    def expand(self, store: ox.Store, want: str, *, budget: int = BUDGET, only=None,
               memo: Memo | None = None) -> int | None:
        """Open the top of `want`'s frontier: admit what it admits, take each candidate this
        want has not yet weighed, weigh what it reached, close the world's weighing. What the
        want's search has spent afterwards, in candidates weighed — or None where there was
        nothing to open: the frontier is empty, or the cheapest achiever refuses its top.

        THE BOUND IS HERE and not in the loop, because a case of one iteration must not open
        what the search would not. It is on the top's spent PLUS what its want's estimate says
        is left, so an estimate that never overstates refuses a world that cannot beat the
        cheapest achiever before it is opened, and one that overstates would let the pass end
        with a dearer plan than exists — the package's promise, which no test here can hold
        it to. A candidate another want's search already took here has
        its world already, so it is not taken again; a candidate this want already weighed —
        the expansion was cut by the budget and this is the resumption — is not offered by
        `unweighed`. The weighing is closed only when every candidate was weighed, so a cut
        expansion stays open and is taken up next time.
        """
        memo = Memo() if memo is None else memo
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        top = next(iter(rows(store, _FRONTIER_Q, (), want=want, cat=cat)), None)
        if top is None or (top.get("best") is not None
                           and float(top["spent"]) + float(top["remaining"]) >= float(top["best"])):
            return None
        world = top["w"]
        admit(store, world, self.uri, only=only, memo=memo)
        spent = int(top.get("used") or 0)
        for pair in unweighed(store, for_=want, leaving=world, memo=memo):
            if spent >= budget:
                return spent            # cut: the world stays open, to be taken up next time
            if not pair.get("child"):
                take(store, pair["about"], self.uri, memo=memo)
            weigh(store, want, pair["about"], memo=memo)
            spent += 1
        update(store, bind(_CLOSE_U, weighing=Raw(f"<{top['weighing']}>")))
        return spent


#  WHAT A WANT'S SEARCH HAS SPENT — every weighing for it but a ground's — before this call.
_SPENT_Q = """
SELECT (COUNT(?x) AS ?used) WHERE {
  GRAPH $cat { ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
               FILTER NOT EXISTS { ?u a planning:GroundGraph } } }"""


def _spent(store: ox.Store, want: str, memo: Memo) -> int:
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    return int(next(iter(rows(store, _SPENT_Q, (), want=want, cat=cat)), {}).get("used") or 0)


def _of_scope(store: ox.Store, shapes: rdflib.Graph, holder: str, scope: str, scopes: dict,
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
    first = (sorted(set(scopes.values())) or [UNSCOPED])[0]
    mine = []
    written = footprint.written(store, at)       # at the pass's instant: a read of the clock is a tick
    for want in find_wants(store, at, holder=holder):
        #  WHAT ITS MET-TEST READS, off the shape it is met when — the want node itself is no
        #  shape and reads nothing, which placed every want in the first scope and went unseen
        #  while every world was one scope.
        met = shapes.value(rdflib.URIRef(want), rdflib.URIRef(PLANNING + "metWhen"))
        reads = footprint.reads_of_shape(shapes, met) if met is not None else footprint.ANYTHING
        if reads is footprint.ANYTHING:
            #  A WANT WHOSE SHAPE THE WALKER CANNOT READ joins everything, which is the
            #  safe direction — it is searched once, in the first scope, rather than
            #  separated from a world that could repair it.
            if scope == first:
                mine.append(want)
            continue
        #  PLACED BY WHAT IT READS THAT SOME ACTION CAN CHANGE. A disk's size and what a peg is
        #  are read by a want refined below and changed by nothing, so they say nothing about
        #  which world could repair it — counted, they pulled a courier goal into hanoi's scope.
        changeable = [p for p in reads if str(p) in written] or list(reads)
        reached = sorted({scopes[str(p)] for p in changeable if str(p) in scopes})
        if reached[:1] == [scope] or (not reached and scope == first):
            mine.append(want)
    return mine
