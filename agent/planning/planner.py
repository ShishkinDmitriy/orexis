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
   predictions make, and one where each step in flight lands where a constraint is held;
   `reroot` finds the world the last pass imagined that the present landed in, keeps its cone
   under the new ground and drops the rest;
2. every desire is weighed in every ground (`weigh`, over what `unweighed` lists); where a belief
   has arrived, every walking plan of the scope is replayed on the grounds and a walking want one
   of whose worlds a constraint makes impossible is reopened (`_impossible_ahead`, #921);
   `derive_wants` reads the weighings and mints a want per cluster of what they read unmet —
   one a constraint couples to a walking want reopening it, and a walking want a belief reopened
   minted again reopening itself, each where its step in flight lands — and `withdraw` takes
   away what no desire implies and no intention is walking;
3. per want that no intention is walking, and per walking want that reopens itself and has no
   plan yet, `search`: the want is weighed in the ground holding at its instant
   ground, and `expand` opens the cheapest open world until nothing is open, the cheapest
   achiever refuses the top, or the budget is spent — an iteration admits the world's
   candidates, takes each and weighs what it reached; then `extract_plan` writes what the
   want's weighings come to, and `_reconsider` holds a reopening want's plan against the
   walking intention's untaken steps;
4. `publish_plan` hands every plan no intention is already walking DOWN, through the belief base,
   less the steps a standing intention already walks:
   an `orexis:PlanGraph` published once in execution's words, each step a bridge may keep below marked so
   (`bridge.keeps`), which the executor adopts by reference.

And before any of it, every step an intention stands at that is kept below and has fallen due is
given the want that keeps it (`refine`), which the executor then waits on.

And outside the pass, `check`: a head about to be taken is asked of the present whether its action's
precondition still admits it, as the executor is about to hand it over (#916).

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
executor's verdict on a step is for — until a want a constraint couples to it arrives, or a
belief arrives that makes a world its untaken steps reach impossible, the two triggers that reopen
it: the step in flight stays, the reopening want is searched from the ground in which that step has
landed, and its plan is held against the intention's untaken steps
(`_reconsider`, knowledge/domain/execution/commitment.md).

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

import logging
import time
from datetime import datetime, timedelta

import pyoxigraph as ox
import rdflib

from agent import clock
from agent.lifecycle import Signal
from agent.metrics import Laps
from agent.ontology import ACTION, PUBLIC, RECORD, local_of
from agent.store import (Memo, Raw, add_quads, copy_graph, forget_graph, bind, bindings, catalogue_of, graphs_of, instant,
                         query, rdflib_view, remember, rows, update)

from . import footprint
from .admit import admit
from .bridge import keeps
from .derive_wants import derive_wants
from .events import (Imagined, Planned, PlanPublished, Reconsidered, Rerooted, SearchEnded, StepBlocked,
                     WantReached, WantUnreachable)
from .extract_plan import extract_plan
from .find_scopes import find_scopes
from .refine import refine
from .find_wants import find_wants
from .lay_ground import lay_ground
from .ontology import CONSTRAINT_GRAPH, DESIRE, GROUND_GRAPH, PLAN_GRAPH, PLANNING, SATISFIED, SCOPE_GRAPH, SHAPES, WANT
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

#  WHERE EVERY STANDING INTENTION STANDS: the want it pursues, the plan it adopts, its head and the
#  action the head fills, and — where the head has been TAKEN, handed to its taker with an act on
#  record and not yet answered, which is a step IN FLIGHT — when it was due, when it was taken and
#  when its plan placed it to land. Execution's rows, read from the layer beneath as `walking` reads them.
_STANDS_AT_Q = """
SELECT ?intention ?want ?plan ?step ?action ?due ?taken ?lands ?ending WHERE {
  GRAPH ?g { ?intention a execution:Intention ; execution:pursues ?want ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
             OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken }
             OPTIONAL { ?intention execution:endsAfter ?ending } }
  GRAPH ?plan { ?step planning:fills ?action .
                OPTIONAL { ?step execution:notBefore ?due } OPTIONAL { ?step execution:landsAt ?lands } } }
ORDER BY ?intention"""

#  A PLAN'S STEPS AS A CHAIN, in either store: each step, the one after it, the action it fills and
#  every value it states — of which the parameters its action takes are its filling.
_CHAIN_Q = """
SELECT ?step ?next ?action ?p ?v WHERE { GRAPH $plan { ?step a execution:Step ; planning:fills ?action ; ?p ?v .
  OPTIONAL { ?step execution:then ?next } } }"""
_TAKES_Q = """SELECT ?takes WHERE { $action orexis:takes ?takes }"""

#  THE WALKING WANTS A WANT REOPENS — the derivation's row — and the plan its search wrote, with how it ended.
_REOPENS_Q = """SELECT ?w WHERE { GRAPH ?g { $want planning:reopens ?w } } ORDER BY ?w"""
_PLAN_FOR_Q = """SELECT ?plan ?outcome WHERE { GRAPH ?plan { ?plan a planning:Plan ; planning:for $want ; planning:outcome ?outcome } } LIMIT 1"""

#  EVERY WALKING WANT THAT REOPENS ITSELF and whose search has found no plan yet — a want a belief
#  arriving reopened, which is searched until it has one (#921).
_REOPENING_Q = """
SELECT ?w WHERE { GRAPH ?g { ?w planning:reopens ?w }
  FILTER NOT EXISTS { GRAPH ?p { ?p a planning:Plan ; planning:for ?w ; planning:outcome planning:Satisfied } } }"""

#  WHAT EACH GROUND OF THIS PASS HOLDS, by the hash `lay_ground` wrote on its row; and what every world
#  an imaginarium holds does — its grounds and its possible worlds — asked before the grounds are laid,
#  when what it holds is what the last pass left.
_GROUND_HASHES_Q = """SELECT ?h WHERE { GRAPH $cat { ?g a planning:GroundGraph ; orexis:hash ?h } }"""
_HASHES_Q = """SELECT DISTINCT ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w orexis:hash ?h } }"""

#  THE WANTS THE DERIVATION MINTED in an imaginarium — the only ones it can mint again.
_DERIVED_Q = """
SELECT ?w WHERE { GRAPH ?g { ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }"""

#  WHAT EACH STEP OF A PLAN PUBLISHED PREDICTS, AND WHEN: its landing and the two graphs it names.
_PREDICTS_Q = """
SELECT ?step ?lands ?adds ?retracts WHERE { GRAPH $plan { ?step a execution:Step .
  OPTIONAL { ?step execution:landsAt ?lands } OPTIONAL { ?step execution:adds ?adds }
  OPTIONAL { ?step execution:retracts ?retracts } } }"""

#  A WORLD FORESEEN FOR A WALKING PLAN'S STEP: the instant it stands at, which is all `world_at` asks
#  of a world; no kind, so no reader asking by kind is handed it while it stands.
_FORESEEN_U = """
INSERT { GRAPH ?cat { $world dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start $start ] } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"""

#  AND THE WEIGHINGS OF ONE, with the violation rows hanging off each, taken back with it.
_UNWEIGH_U = """
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"""

#  WHETHER THE HOLDER HOLDS ANY CONSTRAINT — the one thing that can reopen a walking want, by either trigger.
_HOLDS_CONSTRAINT_Q = """SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } LIMIT 1"""

#  THE STEP EVERY STANDING INTENTION STANDS AT.
_STANDING_AT_Q = """
SELECT DISTINCT ?step WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step .
                                         FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }"""

#  EVERY STEP AN INTENTION STANDS AT THAT IS KEPT BELOW, HAS FALLEN DUE AND HAS NO WANT KEEPING IT
#  YET; what it predicts is read off the two graphs it names, by `refine`.
_KEPT_DUE_Q = """
SELECT ?step WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } }
  GRAPH ?plan { ?step execution:keptBelow true .
                OPTIONAL { ?step execution:notBefore ?due } }
  FILTER(!BOUND(?due) || ?due <= $now)
  FILTER NOT EXISTS { GRAPH ?h { ?step execution:keptBy ?w } } }
ORDER BY ?step"""

#  THE ACTION A HEAD ABOUT TO BE TAKEN FILLS — what the present must still admit for it to be taken
#  — unless it is kept below, whose own facts a want one level down answers. Asked of any graph for
#  each half: the step's filling is stated in its plan and in its committed step, and the mark that
#  keeps it below in the plan alone, so a read inside one graph would find the committed step's row
#  and call a step kept below one to check.
_HEAD_Q = """
SELECT ?action WHERE { GRAPH ?p { $step planning:fills ?action }
  FILTER NOT EXISTS { GRAPH ?k { $step execution:keptBelow true } } } LIMIT 1"""

#  AN ACTION'S PRECONDITION AND THE PARAMETERS IT TAKES, and a step's value for each.
_PRECONDITION_Q = """SELECT ?text ?takes WHERE { $action planning:precondition ?text . OPTIONAL { $action orexis:takes ?takes } }"""
_FILLING_Q = """SELECT ?p ?v WHERE { GRAPH ?plan { $step ?p ?v } }"""

#  EVERY STEP OF A PLAN PUBLISHED WHOSE ACTION IS TAKEN FICTIVELY; what it predicts is read off
#  the two graphs it names, by `keeps`.
_FICTIVE_STEPS_Q = """
SELECT ?step WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?action }
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

#  EVERY INSTANT A GROUND BEGINS AT — the instants the agent can see, which is where a want may hold.
_GROUND_STARTS_Q = """
SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?s } }
ORDER BY ?s"""

#  WHAT THE EVENTS SAY OF A WANT, read where the event is made: the plan its search wrote and how it
#  ended, the desire it was derived under, what its estimate said at the present ground, and how many
#  intentions have pursued it — off the beliefs, where execution's rows are.
_PLAN_OF_Q = """
SELECT ?outcome ?spent WHERE { GRAPH ?g { ?p a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
  OPTIONAL { ?p planning:spent ?spent } } } LIMIT 1"""
_DESIRE_OF_Q = """SELECT ?d WHERE { GRAPH ?g { $want a planning:Want ; prov:wasDerivedFrom ?d } } LIMIT 1"""
_ESTIMATE_Q = """
SELECT ?remaining WHERE { GRAPH $cat { ?x planning:weighs $ground ; planning:for $want ; planning:remaining ?remaining } } LIMIT 1"""
_PURSUES_Q = """SELECT ?want WHERE { GRAPH ?g { $plan execution:pursues ?want } } LIMIT 1"""
_PURSUERS_Q = """SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention ; execution:pursues $want } }"""

#  WHAT AN IMAGINARIUM HOLDS: its possible worlds and the weighings of them, of those how many are on
#  a frontier and how many met their want; and its plans, by why each search ended.
#
#  Counted by OPTIONAL rows inside the catalogue and not by `EXISTS` in the aggregate: an EXISTS in
#  a projected expression is evaluated against the DEFAULT graph, which this read is handed empty,
#  and it answered no met weighing on a greenhouse imaginarium holding one — measured, 2026-09-27.
_CONE_Q = """
SELECT ?worlds ?weighings ?open ?met WHERE {
  { SELECT (COUNT(?w) AS ?worlds) WHERE { GRAPH $cat { ?w a planning:PossibleGraph } } }
  { SELECT (COUNT(?x) AS ?weighings) (COUNT(?o) AS ?open) (COUNT(?m) AS ?met) WHERE {
      GRAPH $cat { ?x a planning:Weighing .
                   OPTIONAL { ?x planning:open true BIND(?x AS ?o) }
                   OPTIONAL { ?x planning:met true BIND(?x AS ?m) } } } } }"""
_PLANS_HELD_Q = """
SELECT (SUM(IF(?outcome = planning:Satisfied, 1, 0)) AS ?satisfied)
       (SUM(IF(?outcome = planning:Exhausted, 1, 0)) AS ?exhausted)
       (SUM(IF(?outcome = planning:NoCandidate, 1, 0)) AS ?noCandidate)
WHERE { GRAPH ?plan { ?p a planning:Plan ; planning:outcome ?outcome } }"""

#  AND THE ACHIEVER IS NEVER AN IMPOSSIBLE WORLD, with no filter to say so: a want's weighing of a
#  world a constraint marks `planning:impossible` is BARE — `planning:met` and `planning:open` taken
#  back, or never written — so it matches neither the frontier's pattern nor the achiever's by its
#  rows. The alternative was a `FILTER NOT EXISTS` on the world's mark inside the `MIN` subselect,
#  and that shape cost a quarter of every pass on the search bench — hanoi, the courier, holders with
#  no constraint at all — measured alternated against the tree before (#902).
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

#  THE CONSTRAINTS THE HOLDER HOLDS — what the world says is POSSIBLE, each a `planning:Constraint`
#  carrying a shape or an avoided state in a desire's words (`constraint.md`), read where a world
#  states them. Which polarity each carries, and what it reads, is read off the shapes crossed.
_CONSTRAINTS_Q = """SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c"""

#  THE WORLD A WEIGHING IS OF, where it is a possible world — a candidate passed over weighs the
#  candidate, and reaches nothing a constraint could mark — and whether it is marked already, by a
#  want whose search reached it first, in which case the weighing is bare and nothing is asked.
_REACHED_Q = """
SELECT ?w ?marked WHERE { GRAPH $cat { $x planning:weighs ?w . ?w a planning:PossibleGraph .
                                       OPTIONAL { ?w planning:impossible ?marked } } } LIMIT 1"""

#  WHETHER `for` HAS BEEN WEIGHED IN `world`, and by which node — asked by the rows and never by
#  the node's spelling, since a name is for eyes.
_WEIGHED_IN_Q = """SELECT ?x WHERE { GRAPH $cat { ?x planning:weighs $world ; planning:for $for } } LIMIT 1"""

#  THE ROWS OF ONE WEIGHING: each violation's instance, constraint, what it is about and the value
#  that offended — for a constraint, one way the world cannot be, said in the log.
_ROWS_Q = """
SELECT ?i ?c ?a ?o WHERE {
  GRAPH $cat { $x planning:violation ?v . ?v planning:instance ?i .
               OPTIONAL { ?v planning:constraint ?c } OPTIONAL { ?v planning:about ?a } OPTIONAL { ?v planning:offending ?o } } }
ORDER BY ?i ?c ?o"""

#  A WORLD MARKED IMPOSSIBLE: `planning:impossible` naming the constraint on the WORLD'S row, since a
#  world's possibility is true of it whoever asks — and the want's weighing of it made BARE, its
#  verdict, its estimate and its rows taken back, so the weighing is off the frontier and never an
#  achiever by its rows alone and reads as `weigh` writes one in a world already marked. The
#  constraint's own weighing stands beside with its rows, saying what the world violates.
_MARK_U = """
DELETE { GRAPH ?cat { $weighing planning:open ?o . $weighing planning:met ?m . $weighing planning:remaining ?r .
                      $weighing planning:violation ?v . ?v ?p ?x } }
INSERT { GRAPH ?cat { $world planning:impossible $by } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      OPTIONAL { $weighing planning:open ?o } OPTIONAL { $weighing planning:met ?m }
                      OPTIONAL { $weighing planning:remaining ?r }
                      OPTIONAL { $weighing planning:violation ?v . ?v ?p ?x } } }"""


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
        #  WHAT THE TEXTS A PASS EVALUATES READ, remembered while the graphs they live in stand.
        self._read: tuple[frozenset | None, frozenset | None] = (None, None)
        self.handed: list[tuple[str, str]] = []
        self.reached: set[str] = set()
        self.blocked: list[str] = []
        self.superseded: list[Reconsidered] = []
        #  WHAT THE PLANNER SAYS HAPPENED, its own words for whoever connects, each carrying an event
        #  of `events.py`: a plan published; a want an intention walks that the present meets; a
        #  head about to be taken that the present no longer admits (`check`); an intention a
        #  reconsideration replaced, to end after its step in flight; a want nothing reaches;
        #  and, made only where heard, a search ended, a pass, a re-root and what an imaginarium holds.
        self.plan_published = Signal("plan_published")
        self.want_reached = Signal("want_reached")
        self.step_blocked = Signal("step_blocked")
        self.reconsidered = Signal("reconsidered")
        self.want_unreachable = Signal("want_unreachable")
        self.searched = Signal("searched")
        self.planned = Signal("planned")
        self.rerooted = Signal("rerooted")
        self.imagined = Signal("imagined")
        #  TELEMETRY AND NOT A ROW: per want, when it was first searched and in how many passes,
        #  said when its plan is published. No plan branches on it, so it is memory and never a belief.
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
        derived, each searched, and the plans published. The graphs written in the beliefs — the
        plans published and the wants that keep a step below — for whoever hears what was written.

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

        THE PRESENT IS VALIDATED AGAINST THE WORLD'S CONSTRAINTS, in each scope's ground for the
        constraints that scope's actions could violate, and a violation is SAID and not minted —
        a constraint is what the world says is possible, of another modality than a desire, so a
        present that violates one is a contradiction and not a want (`constraint.md`).

        AND THE LAST ACT IS `publish_plan`, publishing each plan into the beliefs: the imaginarium is
        the Planner's and dies with it, so a plan published, and the intention adopting it, are what a
        pass leaves the agent. A plan with no steps does not cross — an answer is not a
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
        #  WHERE EVERY STANDING INTENTION STANDS, and where its step in flight lands — read once, and
        #  read at all only where a constraint is held, since only a constraint can reopen a walking
        #  want (knowledge/domain/execution/commitment.md, #905): a holder with none pays one query.
        flights = self._flights(at) if self._holds_a_constraint() else {}
        #  WHAT THE PASS SAYS, for whoever runs it to signal: the plans it published with their wants,
        #  the wants an intention walks that the present meets, and the intentions a reconsideration
        #  replaced, to end after their steps in flight — and, from here to the next pass, the heads
        #  `check` refused as they were about to be taken.
        self.handed, self.reached, self.blocked, self.superseded = [], set(), [], []
        #  HOW LONG EACH PART OF THE PASS TOOK, where anybody hears the pass: in real seconds by
        #  `perf_counter`, since the agent's clock may run fast and a test's ticks per read.
        lap = Laps() if self.planned.connected else None
        searched: set[str] = set()
        #  WHAT A WORLD IS HASHED WITHIN, read off the texts once and kept while the graphs holding
        #  them are the ones it was read off: actions, desires and shapes are documents, and
        #  reading them every pass cost 20 ms of an idle greenhouse pass's 132, measured with the
        #  two alternated in one session.
        texts = frozenset(graphs_of(self.beliefs, ACTION, DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH))
        if self._read[0] != texts:
            self._read = (texts, _read_anywhere(self.beliefs, at))
        read = self._read[1]
        for _scope in sorted(scopes.all()) or [UNSCOPED]:
            #  THE SCOPE'S OWN ACTIONS are what its worlds admit; a store of no scope admits all.
            only = None if _scope == UNSCOPED else {
                r["a"] for r in rows(self.beliefs, _IN_SCOPE_Q, graphs_of(self.beliefs, SCOPE_GRAPH), scope=_scope)}
            #  AND THE TERMS THAT ARE ANOTHER SCOPE'S — every member this scope is not among the
            #  scopes of — so a filling of a shared action that is theirs — the lamp's heating, in
            #  the air's search — is not admitted here (#593); and the partition whole, so a reading
            #  keyed by them — the air's, in the soil's; the other bed's, in this bed's — does not
            #  cross: the imaginarium is the scope's, its grounds the scope's readings, and a world
            #  their size.
            elsewhere = frozenset(m for m, ss in scopes.items() if _scope not in ss) if _scope != UNSCOPED else frozenset()
            store = self.imaginaria.setdefault(_scope, ox.Store())
            prepare_ground(self.beliefs, store, scope=None if _scope == UNSCOPED else _scope, scopes=scopes)
            #  THE PASS'S MEMO, one per world: the action templates, a rule text, the graph
            #  list per instant and the shapes cost more to re-read than a pass can afford
            #  and can change only by a write the search does not make.
            memo = Memo()
            #  EVERY WORLD OF THIS IMAGINARIUM IS HASHED WITHIN WHAT IS READ — the ground here, each
            #  child in `take` — so a reading's instant, which nothing reads, is not what the present
            #  differs by (`hash_named_graph`): the scope's members, and with them every predicate a
            #  text the pass evaluates reads, since a scope names what an action can CHANGE and a
            #  fact a met-test reads that no action writes must still tell two presents apart. A
            #  text that cannot be read reads anything, and then the world is hashed whole.
            within = None if read is None else read | frozenset(m for m, ss in scopes.items() if _scope in ss)
            #  AND A BOUNDARY WHERE EACH STEP IN FLIGHT OF THIS SCOPE LANDS: the ground in which it
            #  has landed is where a reconsideration's search starts, so the plan it finds begins
            #  after the step and never beside it.
            landings = [lands for f in flights.values() for action, lands in f["landings"] if only is None or action in only]
            #  WHETHER A BELIEF HAS ARRIVED THAT THE AGENT DID NOT FORESEE, which is the one sense in which
            #  a belief can touch a walking plan (#921): some ground laid now holds what no world the
            #  last pass left here held — no ground, and no possible world a search imagined — by the
            #  hash each is written with, within what is read. A prediction laid, a peer seen where
            #  nothing said it would be, are news; a step of the walking plan landing as its plan
            #  said is not, since the world it lands in is in the cone the plan was found in; and a
            #  belief no text reads moves no hash at all. Asked only where something is walked by a
            #  holder of a constraint, which is the only agent the answer is for.
            foreseen = frozenset(r["h"] for r in rows(store, _HASHES_Q, ()) if r.get("h")) if flights else frozenset()
            present, *_ = lay_ground(store, at, within, landings)
            arrived = bool(flights) and bool(frozenset(
                r["h"] for r in rows(store, _GROUND_HASHES_Q, (), cat=Raw(f"<{catalogue_of(store)}>"))) - foreseen)
            rerooting = reroot(store, present)
            if self.rerooted.connected:
                written += self.rerooted.emit(Rerooted(scope=local_of(_scope), present=rerooting.present,
                                                       kept=len(rerooting.kept), dropped=len(rerooting.dropped)))
            if lap:
                lap("ground")
            #  THE PRESENT IS VALIDATED, NOT REPAIRED. Every constraint the holder holds that this
            #  scope's actions could violate is weighed in the present ground; one that yields a row
            #  there is a contradiction between the world's state and its own word about what is
            #  possible — said, with its rows, and never minted: a constraint is no desire, so the
            #  derivation reads none, and what the search does with it is mark the worlds it reaches.
            constraints = remember(memo, ("constraints",), lambda: _constraints(store, _shapes(store, memo), self.uri, only, at))
            for constraint, broken in self._contradictions(store, present, constraints, memo):
                log.warning("%s: the present violates %s, a constraint of this world, and nothing repairs it: %s",
                            self.id, local_of(constraint), _said(broken))
            for pair in unweighed(store, memo=memo):
                #  GROUNDS ONLY. A candidate the budget left untaken in a world it cut is
                #  unweighed too, and weighed here it would never be offered to the expansion
                #  that takes it: its world would never be forked, and the search the passes
                #  after were to finish would empty its frontier short of the answer — the
                #  courier's corner delivery did, at sixteen candidates a pass.
                if not pair.get("from"):
                    weigh(store, pair["for"], pair["about"], memo=memo)  # every desire, every ground
            #  SOFT COMMITMENT'S SECOND TRIGGER (#921): where a belief has arrived, every walking plan
            #  of this scope is held to the grounds as now laid — its untaken steps replayed from where
            #  its step in flight lands, each world weighed for the constraints — and a walking want one
            #  of whose worlds is impossible is reopened. Asked only where a belief arrived, only of a
            #  holder that holds a constraint (`flights` is empty otherwise), and only of plans this
            #  scope's actions walk.
            reopen = self._impossible_ahead(store, flights, constraints, only, memo) \
                if arrived and flights and constraints else set()
            if lap:
                lap("weigh")
            #  A WANT MET IN THE PRESENT IS REACHED, and one-shot: it goes, from here and from the
            #  beliefs, where a want the world authored lives — unless a plan is still walking it,
            #  whose last step the executor has yet to see answered.
            met_now = {r["for"] for r in rows(store, _MET_NOW_Q, (), ground=present)}
            self.reached |= met_now & walking
            reached = met_now - walking
            #  THE DERIVATION IS TOLD WHAT IS WALKED, and from when — the instant each walking want's
            #  step in flight lands, the present where none is — since a cluster a constraint couples
            #  to a walking want reopens it, and is minted where that step has landed.
            #  AND WHICH WALKING WANTS A BELIEF REOPENED: what their searches wrote before goes, since
            #  it stood on grounds the belief has changed, and the derivation mints each again at the
            #  instant its step in flight lands, saying it reopens itself.
            opens = {w: flights[w]["landing"] if w in flights else at for w in walking}
            if reopen:
                withdraw(store, None, at, afresh=reopen)
            withdraw(store, derive_wants(store, at, opens, reopen) | walking, at, reached=reached)
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
            shapes = _shapes(store, memo)
            kept: dict[str, list[str]] = {}
            #  A WALKING WANT THAT REOPENS ITSELF is searched until its search has a plan: in the pass a
            #  belief reopened it, and in the passes after where the budget cut that search short.
            reopening = {r["w"] for r in rows(store, _REOPENING_Q, ())} & walking if flights else set()
            superseded = len(self.superseded)
            for want in _of_scope(store, shapes, self.uri, _scope, scopes, at):
                if want in walking and want not in reopening:
                    continue                # a want a plan is walking is not planned again
                self.search(store, want, budget=self.budget, only=only, elsewhere=elsewhere, memo=memo, scope=_scope,
                            within=within, at=at)
                searched.add(want)
                self._reconsider(store, want, flights, kept)
            if lap:
                lap("search")
            handed = publish_plan(store, self.beliefs, self.uri, walking - (reopening & searched), kept)
            self._mark_kept(handed)
            written += handed
            #  WHAT A RECONSIDERATION ENDS IS SAID BEFORE WHAT REPLACES IT IS: an intention ending after
            #  its step in flight absorbs no plan, so a plan for the very want it walks — a want a belief
            #  reopened — is adopted beside it rather than refused as a second plan for one want.
            for event in self.superseded[superseded:]:
                written += self.reconsidered.emit(event)
            #  SAID BEFORE ANYTHING ADOPTS IT, since whether an intention pursued the want before is
            #  what makes a replan, and the executor adopts as it hears.
            published = self._published(store, handed, present, _scope, memo)
            if lap:
                lap("publish")
            for event in published:
                self.handed.append((event.plan, event.want))
                written += self.plan_published.emit(event)
            if self.imagined.connected:
                written += self.imagined.emit(self._imagined(store, _scope))
            walking = self.walking()        # a want published from one scope is walked in the next
        #  A WANT NO LONGER SEARCHED — reached, withdrawn, or walked — takes its tally with it.
        self._searches = {w: s for w, s in self._searches.items() if w in searched}
        if lap:
            written += self.planned.emit(Planned(wants=len(searched), **lap.spent))
        for want in sorted(self.reached):
            written += self.want_reached.emit(WantReached(want))
        return written

    # --- a step kept one level down ----------------------------------------------------------

    def walking(self) -> set[str]:
        """Every want this agent is walking, off execution's rows in the belief base: pursued by a
        standing intention, or by a plan published and not yet adopted. Neither searched again
        nor withdrawn, whatever its desire reads, until a want a constraint couples to it, or a
        belief that makes a world of its plan impossible, reopens it
        (knowledge/domain/execution/commitment.md)."""
        cat = Raw(f"<{catalogue_of(self.beliefs)}>")
        return {r["want"] for r in rows(self.beliefs, _WALKING_Q, (), cat=cat)}

    def _keep_below(self, at: datetime) -> list[str]:
        """Give every step an intention stands at that is kept below and has fallen due the want
        that keeps it, one level down (`refine`), which the executor waits on. The want graphs."""
        minted = []
        for r in rows(self.beliefs, _KEPT_DUE_Q, (), now=instant(at)):
            want = refine(self.beliefs, self.uri, r["step"], at)
            if want is not None:
                minted += [g["g"] for g in rows(self.beliefs, _REFINED_Q, ()) if g["want"] == want]
        return minted

    def check(self, step: str, at: datetime) -> list[str]:
        """Check `step`, a head about to be handed to its taker at `at`, against the present: where
        its action's precondition, asked there with `$me` bound, answers no row carrying the step's
        own value for every parameter the action takes, the step is BLOCKED — said by `step_blocked`,
        for execution to end the intention before the step is taken, and planning plans again. The
        graphs the handlers wrote. A step kept below, or whose action states no precondition, is
        not checked.

        WHEN IT IS TAKEN, AND ONLY THEN (#916). This asked once a pass, of every head due at the
        pass's start, in the scope's present ground; a head that fell due inside a walk — the step
        before it answered, or a fictive step landing as it was taken — was handed over unasked, and
        a fictive one then wrote its own effect and landed, so the driver world walked van A with its
        driver aboard van B. A head due at a pass's start is taken by the walk that follows the pass,
        so asking at the taking asks of every head the pass would have, and of the rest.

        IN THE PRESENT THE BELIEFS HOLD, not a ground: between passes the beliefs are where a step
        just taken wrote, and the present is every reading as it stands (`world_at` with no world),
        which is what the present ground is laid from. Every scope's readings are there, so a step
        is judged by its own filling wherever it was admitted, and the scope that admitted it need
        not be found again."""
        head = rows(self.beliefs, _HEAD_Q, (), step=step)
        if not head:
            return []
        found = rows(self.beliefs, _PRECONDITION_Q, graphs_of(self.beliefs, ACTION), action=head[0]["action"])
        if not found:
            return []
        takes = {r["takes"] for r in found if r.get("takes")}
        filling = {local_of(r["p"]): r["v"] for r in rows(self.beliefs, _FILLING_Q, (), step=step) if r["p"] in takes}
        answers = bindings(query(self.beliefs, bind(found[0]["text"], me=self.uri), world_at(self.beliefs, None, now=at)))
        if any(all(row.get(k) == v for k, v in filling.items()) for row in answers):
            return []
        log.info("%s: %s is not taken — the present admits it no more", self.id, local_of(step))
        self.blocked.append(step)
        return self.step_blocked.emit(StepBlocked(step))

    # --- commitment: the step in flight, and the two triggers that reopen a walking want -------

    def _holds_a_constraint(self) -> bool:
        """Whether this agent holds any constraint — the one thing that can couple a want to a walking
        one or make a world of a walking plan impossible, and so the one thing a walking want can be
        reopened by."""
        return bool(rows(self.beliefs, _HOLDS_CONSTRAINT_Q, graphs_of(self.beliefs, CONSTRAINT_GRAPH), holder=self.uri))

    def _flights(self, at: datetime) -> dict[str, dict]:
        """Where every standing intention stands, by the want it pursues: the intention, the plan it
        adopts, its head and the action the head fills, whether the head is IN FLIGHT — taken, an act
        on record, and not yet answered — and the instant it lands. A step in flight lands as long
        after it was taken as its plan placed it after its opening, the executor's own reading
        (`Executor._landing`), at the earliest; a head not taken has nothing in flight, and lands now.
        `late` is how far behind its plan the intention runs — its step in flight taken late, or its
        head due and not yet taken — which every step after it inherits.

        AN INTENTION ENDING AFTER ITS STEP IN FLIGHT (`execution:endsAfter`) stands for its want only
        where nothing else does, and is said `ending`. Where a belief arriving reopened the want it
        walks (#921), the plan found for the same want is adopted beside it, and that one's steps are
        the want's untaken steps; the step in flight is still the ending one's, so where the want's
        plan opens is the latest landing among its intentions, and `landings` is every step in flight
        among them, each with its action."""
        held: dict[str, list[dict]] = {}
        for r in rows(self.beliefs, _STANDS_AT_Q, ()):
            landing, late = at, timedelta(0)
            if r.get("taken") and r.get("lands"):
                taken = (datetime.fromisoformat(r["taken"]) - datetime.fromisoformat(r["due"])) if r.get("due") else None
                late = taken if taken and taken.total_seconds() > 0 else timedelta(0)
                landing = datetime.fromisoformat(r["lands"]) + late
            elif not r.get("taken") and r.get("due"):
                late = max(timedelta(0), at - datetime.fromisoformat(r["due"]))
            held.setdefault(r["want"], []).append({
                "intention": r["intention"], "plan": r["plan"], "head": r["step"], "action": r["action"],
                "in_flight": bool(r.get("taken")), "ending": bool(r.get("ending")), "late": late,
                "landing": max(landing, at)})
        out: dict[str, dict] = {}
        for want, flights in held.items():
            flight = dict(next((f for f in flights if not f["ending"]), flights[0]))
            flight["landings"] = [(f["action"], f["landing"]) for f in flights if f["in_flight"]]
            flight["landing"] = max(f["landing"] for f in flights)
            out[want] = flight
        return out

    def _impossible_ahead(self, store: ox.Store, flights: dict, constraints: list[str], only, memo: Memo) -> set[str]:
        """The walking wants of this scope a world of whose plan is IMPOSSIBLE in the grounds as now
        laid — soft commitment's second trigger (#921). For each standing intention whose head's action
        is this scope's, and whose want the derivation minted here: its UNTAKEN steps — those after the
        step in flight, or from the head where nothing is — replayed in order, and each world they reach
        weighed for every constraint among `constraints`, stopping at the first that yields a row.

        THE WORLDS ARE THE PLAN'S OWN CLAIM, LAID ON THE NEW GROUNDS. A step published says what its
        effect changes, `execution:adds` and `execution:retracts` (#919), and when it lands,
        `execution:landsAt`; the world after the k-th untaken step is the ground holding at that landing
        — shifted by how far behind its plan the intention runs, and never before the step in flight
        lands — with the changes of the first k applied in order. Exactly what the executor holds the
        world to, so the question asked is the one that matters: will what this plan says will happen
        be possible, given what the agent now believes? Replaying the effects' RULES from the landing
        ground instead would be a search's take with no search, a second path to a world the step
        already describes; and the search's own worlds of the walking want are no use, since they
        were forked from grounds the belief has since changed. A diff applied on a ground that has
        moved under it is the plan's prediction, not the world's — that is the point: the van will be
        where its steps say, and the peer where the belief says.

        A WORLD FORESEEN IS NOBODY'S AND LASTS THE QUESTION: a graph with the instant it stands at and
        no kind, weighed by `weigh` as any world is, and forgotten with its weighings before this
        returns. Nothing compares it to its parent, as nothing does in the search: a world that keeps
        a violation is as impossible as one that enters it.

        A WANT THE WORLD RATIFIED IS NOT ASKED: its instant is the world's, and the derivation, which
        re-mints a reopened want at the instant its step in flight lands, did not mint it. An
        intention ending after its step in flight has given its untaken steps up and is not asked
        either."""
        derived = {r["w"] for r in rows(store, _DERIVED_Q, ())}
        out: set[str] = set()
        for want, flight in sorted(flights.items()):
            if flight["ending"] or want not in derived or (only is not None and flight["action"] not in only):
                continue
            chain = [step for step, _ in self._chain(self.beliefs, flight["plan"])]
            at = chain.index(flight["head"]) if flight["head"] in chain else len(chain)
            untaken = chain[at + (1 if flight["in_flight"] else 0):]
            if not untaken:
                continue
            said = {r["step"]: r for r in rows(self.beliefs, _PREDICTS_Q, (), plan=Raw(f"<{flight['plan']}>"))}
            foreseen, changes, before, world = [], [], None, None
            try:
                for step in untaken:
                    row = said.get(step, {})
                    lands = datetime.fromisoformat(row["lands"]) + flight["late"] if row.get("lands") else flight["landing"]
                    lands = max(lands, flight["landing"])
                    ground = next(iter(graphs_of(store, GROUND_GRAPH, at=lands)), None)
                    if ground is None:
                        break
                    change = (_quads_of(self.beliefs, row.get("retracts")), _quads_of(self.beliefs, row.get("adds")))
                    changes.append(change)
                    #  ON THE WORLD BEFORE IT where the step lands in the same ground; on the ground it
                    #  lands in, with every change so far, where that ground is a later one.
                    base, applying = (world, [change]) if ground == before and world else (ground, changes)
                    world = f"{step}.foreseen"
                    foreseen.append(world)
                    copy_graph(store, base, world)
                    target = ox.NamedNode(world)
                    for retracts, adds in applying:
                        for q in retracts:
                            store.remove(ox.Quad(q.subject, q.predicate, q.object, target))
                        add_quads(store, (ox.Quad(q.subject, q.predicate, q.object, target) for q in adds))
                    update(store, bind(_FORESEEN_U, world=world, start=instant(lands)))
                    before = ground
                    broken = next(((c, b) for c in constraints if (b := _broken(store, c, world, memo))), None)
                    if broken:
                        log.info("%s: %s would be impossible after %s — it violates %s: %s, so it is reopened",
                                 self.id, local_of(want), local_of(step), local_of(broken[0]), _said(broken[1]))
                        out.add(want)
                        break
                else:
                    log.debug("%s: %d world(s) of %s's untaken steps foreseen, none impossible",
                              self.id, len(foreseen), local_of(want))
            finally:
                for world in foreseen:
                    update(store, bind(_UNWEIGH_U, world=world))
                    forget_graph(store, world)
        return out

    def _reconsider(self, store: ox.Store, want: str, flights: dict, kept: dict) -> None:
        """Hold the plan `want`'s search just wrote against the walking intentions it reopens, where
        the derivation said it reopens any (`planning:reopens`) — either trigger of soft commitment,
        which meet here: a want a constraint coupled reopening a walking want (#905), or a walking
        want a belief reopened reopening itself (#921).

        THE JOINT PLAN AGREES WHERE IT BEGINS WITH THEIR UNTAKEN STEPS, compared by the action each
        fills and the values it is filled with, never by node: the steps after the one in flight, or
        from the head where nothing is. Then the intentions stand untouched and the steps they
        already walk are `kept` out of what is published, so the part that is new is adopted beside
        them, opening where the joint plan put it — after the kept steps. A joint plan that walks the
        same steps LATER does not agree: two intentions are walked side by side and nothing holds a
        step of one after a step of the other, so the order the joint plan was found safe in would
        not be the order walked. ANYTHING ELSE disagrees, and each reopened intention is said to end
        after its step in flight — planning decides, execution ends, as for a step blocked — while
        the joint plan is published whole. A search that found no plan publishes nothing and
        reconsiders nothing: the walking intentions walk on, and the passes after continue it."""
        reopened = [r["w"] for r in rows(store, _REOPENS_Q, (), want=want)]
        if not reopened:
            return
        found = next(iter(rows(store, _PLAN_FOR_Q, (), want=want)), None)
        joint = self._chain(store, found["plan"]) if found and found["outcome"] == SATISFIED else []
        if not joint:
            return
        queues: dict[str, list] = {}
        for walked in reopened:
            flight = flights.get(walked)
            if flight is None:
                continue                    # walked by a plan nothing has adopted yet: nothing stands to keep
            steps = self._chain(self.beliefs, flight["plan"])
            at = next((i for i, (step, _) in enumerate(steps) if step == flight["head"]), len(steps))
            queues[walked] = [said for _, said in steps[at + (1 if flight["in_flight"] else 0):]]
        prefix = joint[:sum(len(q) for q in queues.values())]
        pending = {w: list(q) for w, q in queues.items()}
        agrees = len(prefix) == sum(len(q) for q in queues.values())
        for _, said in prefix:
            owner = next((w for w, q in pending.items() if q and q[0] == said), None)
            if owner is None:
                agrees = False
                break
            pending[owner].pop(0)
        #  A WANT THAT REOPENS ITSELF has one intention or none: its new part would be a second plan for
        #  the want the standing intention walks, so a plan that begins with the untaken steps and goes
        #  on agrees only where it IS them, and otherwise replaces them as a plan that differs does.
        if agrees and want in queues and len(joint) > len(prefix):
            agrees = False
        if agrees:
            kept[want] = [step for step, _ in prefix]
            log.info("%s: %s agrees with what %s already walks — the intention stands, and %d new step(s) are adopted beside it",
                     self.id, local_of(want), ", ".join(local_of(w) for w in queues), len(joint) - len(prefix))
            return
        for walked in queues:
            flight = flights[walked]
            log.info("%s: %s replaces the untaken steps of %s — it ends after %s", self.id, local_of(want),
                     local_of(walked), local_of(flight["head"]))
            self.superseded.append(Reconsidered(flight["head"], walked, want))

    def _chain(self, store: ox.Store, plan: str) -> list[tuple[str, tuple]]:
        """The steps of `plan` in `store`, in the order they are walked, each with what it says: the
        action it fills and the values of the parameters that action takes. Read the same way in the
        imaginarium and in the beliefs, so a step of a joint plan and a step an intention walks are
        compared by what they do and not by the node either is."""
        actions = graphs_of(self.beliefs, ACTION)
        said: dict[str, dict] = {}
        after: dict[str, str] = {}
        for r in rows(store, _CHAIN_Q, (), plan=Raw(f"<{plan}>")):
            step = said.setdefault(r["step"], {"action": r["action"], "values": {}})
            step["values"][r["p"]] = r["v"]
            if r.get("next"):
                after[r["step"]] = r["next"]
        takes = {a: {t["takes"] for t in rows(self.beliefs, _TAKES_Q, actions, action=a)}
                 for a in {s["action"] for s in said.values()}}
        head = next((s for s in said if s not in after.values()), None)
        out = []
        while head is not None and head in said:
            s = said[head]
            out.append((head, (s["action"], tuple(sorted((p, v) for p, v in s["values"].items() if p in takes[s["action"]])))))
            head = after.get(head)
        return out

    def _mark_kept(self, handed: list[str]) -> None:
        """Say of every step of a plan published that a bridge keeps below — one taken
        fictively whose predicted fact a rule the store holds concludes — that it is
        `execution:keptBelow`: not the executor's to take fictively."""
        actions = graphs_of(self.beliefs, ACTION)
        for plan in handed:
            for r in rows(self.beliefs, _FICTIVE_STEPS_Q, actions, plan=Raw(f"<{plan}>")):
                if keeps(self.beliefs, r["step"]):
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
               elsewhere=frozenset(), memo: Memo | None = None, scope: str | None = None,
               within: frozenset | None = None, at: datetime | None = None) -> None:
        """Plan for `want` from the ground holding at its instant — the present, or the one a want
        minted for a foreseen instant names (#858) — spending at most `budget` candidates, and
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

        THE SEARCH IS SAID AS IT ENDS, where anybody hears it — how long it took in real seconds,
        the budget, the candidates it weighed and how it ended — one event per want per pass, never
        one per weighing; and the want's tally of searches is kept for its plan's publishing.
        """
        memo = Memo() if memo is None else memo
        started = time.perf_counter()
        for pair in unweighed(store, for_=want, memo=memo):
            if not pair.get("from"):
                weigh(store, want, pair["about"], memo=memo)             # the root: the ground at its instant
        ceiling = _spent(store, want, memo) + budget
        while (spent := self.expand(store, want, budget=ceiling, only=only, elsewhere=elsewhere, memo=memo,
                                    within=within, at=at)) is not None \
                and spent < ceiling:
            pass
        extract_plan(store, want)
        tally = self._searches.setdefault(want, [started, 0])
        tally[1] += 1
        if self.searched.connected:
            plan = next(iter(rows(store, _PLAN_OF_Q, (), want=want)), {})
            self.searched.emit(SearchEnded(
                want=want, desire=_desire_of(store, want), scope=local_of(scope) if scope else None,
                outcome=local_of(plan["outcome"]) if plan.get("outcome") else None,
                duration_s=round(time.perf_counter() - started, 6), budget=budget,
                weighed=_spent(store, want, memo) - (ceiling - budget)))

    def _published(self, store: ox.Store, handed: list[str], present: str, scope: str,
                   memo: Memo) -> list[PlanPublished]:
        """What is said of each plan this pass published from `store`: the want it pursues, the tally
        of the want's searches, which goes with it, what the want's estimate said was left at the
        `present` ground against what the plan spent, and whether an intention pursued the want
        before — a replan."""
        out = []
        for plan in handed:
            found = rows(self.beliefs, _PURSUES_Q, (), plan=plan)
            if not found:
                continue
            want = found[0]["want"]
            first, passes = self._searches.pop(want, (None, 0))
            spent = next(iter(rows(store, _PLAN_OF_Q, (), want=want)), {}).get("spent")
            root = next(iter(rows(store, _ESTIMATE_Q, (), want=want, ground=present,
                                  cat=Raw(f"<{catalogue_of(store)}>"))), {})
            pursued = int(rows(self.beliefs, _PURSUERS_Q, (), want=want)[0]["n"])
            out.append(PlanPublished(
                plan=plan, want=want, desire=_desire_of(store, want), scope=local_of(scope),
                passes=passes, weighed=_spent(store, want, memo),
                wall_s=round(time.perf_counter() - first, 6) if first is not None else None,
                estimate=float(root["remaining"]) if root.get("remaining") is not None else None,
                cost=float(spent) if spent is not None else None, replan=pursued > 0))
        return out

    def _imagined(self, store: ox.Store, scope: str) -> Imagined:
        """What the imaginarium of `scope` holds now: the one store a plan, a world and a weighing
        are written in, and never the belief base, whose readings it copies."""
        cone = rows(store, _CONE_Q, (), cat=Raw(f"<{catalogue_of(store)}>"))[0]
        held = next(iter(rows(store, _PLANS_HELD_Q, ())), {})
        number = lambda row, key: int(row[key]) if row.get(key) is not None else 0
        return Imagined(scope=local_of(scope), worlds=number(cone, "worlds"), weighings=number(cone, "weighings"),
                        open=number(cone, "open"), met=number(cone, "met"), satisfied=number(held, "satisfied"),
                        exhausted=number(held, "exhausted"), no_candidate=number(held, "noCandidate"))

    def unreachable(self, wants) -> list[str]:
        """Say that nothing this agent holds reaches `wants`, each by the desire it was derived under."""
        written = []
        for want in wants:
            desire = next((d for store in self.imaginaria.values() if (d := _desire_of(store, want))), None)
            written += self.want_unreachable.emit(WantUnreachable(want, desire=desire))
        return written

    # --- one iteration -------------------------------------------------------------------

    def expand(self, store: ox.Store, want: str, *, budget: int = BUDGET, only=None,
               elsewhere=frozenset(), memo: Memo | None = None, within: frozenset | None = None,
               at: datetime | None = None) -> int | None:
        """Open the top of `want`'s frontier: admit what it admits, take each candidate this
        want has not yet weighed, weigh what it reached — for the want, and for every constraint
        the holder holds that the scope's actions can write — close the world's weighing. What
        the want's search has spent afterwards, in candidates weighed — or None where there was
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

        AND A WORLD THAT VIOLATES A CONSTRAINT IS IMPOSSIBLE: every constraint the holder holds
        whose footprint the scope's actions write is weighed in each new world the want is
        weighed in, by the same `weigh`, and a world where any yields a row is marked
        `planning:impossible` on its own row and the want's weighing of it made bare — no
        `planning:open`, no `planning:met` — so the frontier never picks it and the achiever read
        never finds it, whatever the want's own test said there. A verdict taken back rather than
        filtered, since a filter on the frontier's read cost every holder a quarter of its pass
        (#902). No parent is compared: possibility is a fact about the world, not about the step
        that reached it, so a world that keeps a violation the present already has is as impossible
        as one that enters it, and the present itself is validated and said, never marked
        (`constraint.md`). A holder with no constraint pays one query a pass.
        """
        memo = Memo() if memo is None else memo
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        top = next(iter(rows(store, _FRONTIER_Q, (), want=want, cat=cat)), None)
        if top is None or (top.get("best") is not None
                           and float(top["spent"]) + float(top["remaining"]) >= float(top["best"])):
            return None
        world = top["w"]
        constraints = remember(memo, ("constraints",),
                               lambda: _constraints(store, _shapes(store, memo), self.uri, only, at or clock.now()))
        admit(store, world, self.uri, only=only, elsewhere=elsewhere, memo=memo)
        spent = int(top.get("used") or 0)
        for pair in unweighed(store, for_=want, leaving=world, memo=memo):
            if spent >= budget:
                return spent            # cut: the world stays open, to be taken up next time
            if not pair.get("child"):
                take(store, pair["about"], self.uri, memo=memo, within=within)
            weighing = weigh(store, want, pair["about"], memo=memo)
            if constraints:
                self._mark(store, weighing, constraints, memo)
            spent += 1
        update(store, bind(_CLOSE_U, weighing=Raw(f"<{top['weighing']}>")))
        return spent

    def _mark(self, store: ox.Store, weighing: str, constraints: list[str], memo: Memo) -> None:
        """Mark the world `weighing` is of impossible where some constraint among `constraints`
        yields a row there. Each constraint is weighed in the world by `weigh`, the one judge, and
        its weighing stands beside the want's with its rows, so a reader can see what the world
        violates; a world another want's search already marked is left as it is, its weighing
        already bare. Every violated constraint is named, since a world may fail more than one."""
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        reached = rows(store, _REACHED_Q, (), x=Raw(f"<{weighing}>"), cat=cat)
        if not reached or reached[0].get("marked"):
            return                      # a candidate passed over reaches nothing; a marked world is settled
        world = reached[0]["w"]
        for constraint in constraints:
            broken = _broken(store, constraint, world, memo)
            if broken:
                update(store, bind(_MARK_U, weighing=Raw(f"<{weighing}>"), world=world, by=constraint))
                log.info("%s: %s is impossible — it violates %s: %s", self.id,
                         world.rsplit("/", 1)[-1], local_of(constraint), _said(broken))

    def _contradictions(self, store: ox.Store, present: str, constraints: list[str], memo: Memo) -> list[tuple]:
        """Every constraint among `constraints` the `present` ground of `store` violates, with the
        rows it violates it by — each constraint weighed there once, by `weigh`."""
        return [(c, broken) for c in constraints if (broken := _broken(store, c, present, memo))]

    def contradictions(self, at: datetime | None = None) -> list[tuple[str, frozenset]]:
        """Every constraint this agent holds that its present violates, as (constraint, rows) — the
        question `orexis-onboard` asks of a world as posed, since a world whose asserted state
        contradicts its own word about what is possible is refused before anything is granted.
        Asked of a throwaway imaginarium over the whole store, so a constraint reading what no
        action writes is validated here though no scope's pass weighs it. Writes nothing to the beliefs."""
        at = at or clock.now()
        scopes = find_scopes(self.beliefs)
        if scopes is None:
            raise RuntimeError("the store holds no scope graph — scope_actions has not run")
        store, memo = ox.Store(), Memo()
        prepare_ground(self.beliefs, store, scope=None, scopes=scopes)
        present, *_ = lay_ground(store, at, None)
        held = [r["c"] for r in rows(store, _CONSTRAINTS_Q, graphs_of(store, CONSTRAINT_GRAPH), holder=self.uri)]
        return self._contradictions(store, present, held, memo)


#  WHAT A WANT'S SEARCH HAS SPENT — every weighing for it but a ground's — before this call.
def _desire_of(store: ox.Store, want: str) -> str | None:
    """The local name of the desire `want` was derived under in `store`, or None — for a want the
    world authored, or a step kept below."""
    found = rows(store, _DESIRE_OF_Q, (), want=want)
    return local_of(found[0]["d"]) if found else None


_SPENT_Q = """
SELECT (COUNT(?x) AS ?used) WHERE {
  GRAPH $cat { ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
               FILTER NOT EXISTS { ?u a planning:GroundGraph } } }"""


def _spent(store: ox.Store, want: str, memo: Memo) -> int:
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    return int(next(iter(rows(store, _SPENT_Q, (), want=want, cat=cat)), {}).get("used") or 0)


def _read_anywhere(beliefs: ox.Store, at: datetime) -> frozenset | None:
    """Every predicate — and every class a type pattern names — that a text a pass evaluates
    reads or writes: each action's precondition and effect, and each desire's and want's
    met-test, avoided state and estimate. What two worlds of this store can be told apart by,
    and so what a world is hashed within. None where any of them cannot be read, which reads
    anything.

    OFF THE BELIEFS, ONCE A PASS, before any imaginarium is filled: a want the derivation mints
    carries its desire's texts with an instance bound, so the desires say what the wants read.
    WHAT IS LEFT OUT is what the hash was scoped to leave out — the instant a reading arrived
    at, the number it gave inside its band, who made it — and what an action's IMPLEMENTATION
    reads when a step is taken, which is asked of the beliefs then and of no possible world.
    """
    out: set[str] = set()
    for reads, writes in footprint.actions_of(beliefs, at).values():
        if reads is footprint.ANYTHING or writes is footprint.ANYTHING:
            return None
        out |= {str(p) for p in reads} | {str(p) for p in writes}
    shapes = rdflib_view(beliefs, *graphs_of(beliefs, DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH))
    for term in ("metWhen", "unmetWhen", "estimates"):
        for node in set(shapes.objects(None, rdflib.URIRef(PLANNING + term))):
            reads = footprint.reads_of_shape(shapes, node)
            if reads is footprint.ANYTHING:
                return None
            out |= {str(p) for p in reads}
    return frozenset(out)


def _shapes(store: ox.Store, memo: Memo) -> rdflib.Graph:
    """The shapes a text is read off, crossed once for the pass under the key `weigh` reads them
    by: the desires, the wants, the records, a domain's shapes and the world's constraints."""
    return remember(memo, ("shapes",), lambda: rdflib_view(store, *graphs_of(store, DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH)))


def _constraints(store: ox.Store, shapes: rdflib.Graph, holder: str, only, at: datetime) -> list[str]:
    """The constraints `holder` holds that a search among the actions `only` must hold its worlds
    to: every `planning:Constraint` whose shape or avoided state reads a predicate some action of
    the scope can write — all actions where `only` is None, a store that scoped nothing. A
    constraint that reads nothing the scope's actions write is kept by every world the scope
    makes, and is not weighed in any; one whose text or whose actions' writes cannot be read is
    weighed, the safe side, as a footprint that cannot be read joins everything. A holder with no
    constraint pays this one query. Either polarity, read as `footprint.reads_of_shape` reads a
    want's: a shape's paths, or the one select an avoided state carries."""
    found = rows(store, _CONSTRAINTS_Q, graphs_of(store, CONSTRAINT_GRAPH), holder=holder)
    if not found:
        return []
    writes: set[str] | None = set()
    for action, (_, written) in footprint.actions_of(store, at).items():
        if only is not None and action not in only:
            continue
        if written is footprint.ANYTHING:
            writes = None
            break
        writes |= {str(p) for p in written}
    out = []
    for r in found:
        node = rdflib.URIRef(r["c"])
        test = shapes.value(node, rdflib.URIRef(PLANNING + "metWhen")) or shapes.value(node, rdflib.URIRef(PLANNING + "unmetWhen"))
        reads = footprint.reads_of_shape(shapes, test) if test is not None else frozenset()
        if writes is None or reads is footprint.ANYTHING or any(str(p) in writes for p in reads):
            out.append(r["c"])
    return out


def _broken(store: ox.Store, constraint: str, world: str, memo: Memo) -> frozenset[tuple]:
    """The ways `world` violates `constraint`, off its weighing there — each row as (instance,
    constraint, about, offending) — weighing it first where no pass has. Once per pass per world,
    since a world's rows do not move. A constraint that could not be judged there wrote no row and
    marks nothing, which `weigh` says in the log: one that marked every world over a text nobody
    can read would end every search of the scope."""
    def read():
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        found = rows(store, _WEIGHED_IN_Q, (), world=world, cat=cat, **{"for": constraint})
        node = found[0]["x"] if found else weigh(store, constraint, world, memo=memo)
        return frozenset((r["i"], r.get("c"), r.get("a"), r.get("o"))
                         for r in rows(store, _ROWS_Q, (), x=Raw(f"<{node}>"), cat=cat))
    return remember(memo, ("broken", constraint, world), read)


def _quads_of(store: ox.Store, graph: str | None) -> list:
    """Every quad of `graph` in `store` — none where no graph is named."""
    return list(store.quads_for_pattern(None, None, None, ox.NamedNode(graph))) if graph else []


def _said(broken: frozenset[tuple]) -> str:
    """The rows of a violated constraint as one line of the log: (instance, constraint, offending)."""
    return ", ".join(f"({local_of(i)}, {c}, {local_of(o) if isinstance(o, str) and '#' in o else o})"
                     for i, c, _, o in sorted(broken, key=str))


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

    AND BY THE TERMS IT NAMES. A scope is over keys (#593), so a predicate two scopes' actions
    both write — a reading's side, written by the pump and the heater alike — is in both and
    places a want nowhere, while the TERMS that key the writes apart narrow it: a want's met-test
    names what it is about in those terms (`planning:about` on its blocks, a `sh:hasValue`),
    parsed off the shape as its predicates are, and a want the derivation keyed (`planning:keyedBy`,
    the bed whose reading it was minted from) names that too. The want is placed where the
    predicates' scopes MEET — every scope all of them are in — and, where that leaves more than
    one, where the terms' scopes meet within it: a want about the soil is placed by the soil where
    its predicates place it nowhere, and a want about one bed's soil, the property being two
    pumps' and the bed the pump's and the heater's, by the two together — and only after the
    predicates: the puzzle's want names the peg it wants the disks on, a cell the courier drives
    to, and placed by the term it was searched among the van's actions.

    A WANT SPANNING SCOPES IS SEARCHED IN THE FIRST OF THEM, and that is a LOSS this
    ordering bought. The grouping it replaced was keyed by every scope a want reached, so
    two wants that could interfere through it shared a world; scopes are the store's now
    and a want cannot join two of them after the worlds are made. What it costs is that
    the third want's step is invisible to the other two, not that anything is done twice:
    one world is picked, deterministically, so a want has one plan.
    """
    first = (sorted(scopes.all()) or [UNSCOPED])[0]
    keyed_by = rdflib.URIRef(PLANNING + "keyedBy")
    mine = []
    written = footprint.written(store, at)       # at the pass's instant: a read of the clock is a tick
    #  THE WANTS HOLDING AT ANY INSTANT THE AGENT CAN SEE: those holding now, and those minted for
    #  a foreseen instant, which hold from then and are searched from the ground holding then
    #  (#858) — the grounds' starts are every instant there is.
    instants = [at, *(datetime.fromisoformat(r["s"]) for r in rows(store, _GROUND_STARTS_Q, ()))]
    found: list[str] = []
    for instant in instants:
        found += [w for w in find_wants(store, instant, holder=holder) if w not in found]
    for want in found:
        #  WHAT ITS MET-TEST READS, off the shape it is met when or the avoided state it is
        #  unmet when (#892) — the want node itself is no shape and reads nothing, which placed
        #  every want in the first scope and went unseen while every world was one scope.
        met = shapes.value(rdflib.URIRef(want), rdflib.URIRef(PLANNING + "metWhen"))
        if met is None:
            met = shapes.value(rdflib.URIRef(want), rdflib.URIRef(PLANNING + "unmetWhen"))
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
        placed = scopes.meet(str(p) for p in changeable)
        if len(placed) != 1:
            #  THE TERMS BREAK THE TIE THE PREDICATES LEAVE, and never overrule them: among the
            #  scopes the predicates left, those the terms meet in; the terms alone where the
            #  predicates placed it nowhere.
            terms = {str(t) for t in footprint.terms_of_shape(shapes, met)} | {str(t) for t in shapes.objects(rdflib.URIRef(want), keyed_by)}
            narrowed = scopes.meet(terms)
            placed = (placed & narrowed) or placed or narrowed
        reached = sorted(placed)
        if reached[:1] == [scope] or (not reached and scope == first):
            mine.append(want)
    return mine
