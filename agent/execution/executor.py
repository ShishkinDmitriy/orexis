"""The executor: the intentions this agent is committed to, and the two threads that carry
a commitment out.

**IT OWNS THE INTENTIONS, AND NOTHING ELSE WRITES THEM.** They are a graph of the belief base, of
its own kind (`execution:IntentionGraph`), the agent's and not public, so a restart on a lived-in
volume finds them (#842) and planning reads what is walked there, by pattern. A plan found above
is PUBLISHED into the store — planning writes it into the beliefs once, as an `orexis:PlanGraph`
it owns — and the executor adopts it BY REFERENCE, an intention that `execution:adopts` it and
holds only its own rows; neither side calls the other (planning-and-execution-meet-at-the-store).
From that moment the commitment is the executor's: any plan among the intentions is scheduled, and every adoption wakes
the timekeeper. The intentions are rows — an intention adopted
at an instant, standing at a step, resolved at another instant with an outcome — and every act
here is a read of those rows and a write of a few more, so a restart finds the intentions where they
were and carries on from the head of every standing intention.

**TWO THREADS, AND WHICH DOES WHAT** (layered-by-timescale-and-interruptibility). One EXECUTES:
it drains a queue and takes each step handed to it, and it waits on nothing but that queue,
so a step that blocks blocks only the steps behind it and never the clock. One KEEPS TIME: it
asks which standing intention has a head step due — `execution:notBefore` past,
or none stated — hands each to the queue, and sleeps until the earliest one not yet due or the
poll cadence, whichever comes first. It runs no step. The predecessor had the same two, the
reactive loop and progression's scheduler, and this is them without the packages.

**THE PASS IS TWO DOORS, CALLABLE WITHOUT A THREAD.** `tick(now)` is one pass of the timekeeper
and `drain()` one pass of the executor, so a test drives a plan through its steps at an instant
of its choosing and asserts between them; the threads call the same two, which is what keeps a
threaded run and a tested run the same run.

**WHAT TAKING A STEP IS, TODAY: SAYING ITS NAME.** The step's rows — the action it fills and
the filling, in the layer above's and the package's words, which this layer repeats and does
not read — go to the log, an `execution:Act` row records that the step was taken, when the
taker was handed it and when it returned (the step's `notBefore` and `landsAt` are the plan's
requirement and prediction, and the act is what actually happened),
and then the WORLD moves the intention: a step that predicts something waits at its
`landsAt` for the present to hold what it predicted — every fact of the graph it `execution:adds`
present and every fact of the one it `execution:retracts` gone over the agent's readings, asked
as one pattern — and `execution:by` moves to the next step when it
does, the last step resolving the intention `done`; past the landing by the patience with no
answer, the intention resolves `failed`. A step that predicts nothing moves as soon as it is
taken. A FICTIVE ACTION — an `execution:Fictive` operation in its implementation — is taken by writing the step's own prediction into the readings, so the
present answers because nothing else could have; an executor built `fictive` takes every
step so, the shorthand for a pure simulation. The one seam is `take`, a callable handed the step's rows: it is where a step will reach real
code — an actuator, a message on the bus — and how an action names its taker is not
decided here. A `take` that raises records the act as not taken and resolves the intention
`failed`, and the executing thread outlives it.

**A COMMITTED STEP IS A BELIEF OVER ITS LANDING WINDOW** (#849). At adoption every step of the plan
is written into the beliefs as a graph of its own, `execution:CommittedStepGraph`, holding from the
step's `notBefore` to its `landsAt` plus the patience and carrying the step's filling and the window's
two lengths in seconds; a drift reads it at an instant inside the window, so a prediction made after
the adoption contains the plan and the window's ends are its happenings. The window closes when the
world answers the step or the intention ends, which is a write whoever hears a belief written hears,
and `tick` forgets what has ended (knowledge/domain/execution/committed-step.md).

**A STEP IN FLIGHT IS NEVER CANCELLED** (#905, knowledge/domain/execution/commitment.md). Planning ends
an intention early by three doors and none of them reaches a step handed to its taker and unanswered:
`end_for` ends one none of whose steps was taken, `end_at` one whose head is due and untaken, and
`supersede_after` — a reconsideration replaced the untaken steps — marks the intention to end after its
step in flight, `execution:endsAfter`, which `_advance` reads when the world answers that step.

**THE PATIENCE IS STILL HERE**, unchanged from the keeper this was: a second plan for a want
already standing is absorbed inside the patience and supersedes past it, which is the
amortisation (an-intention-is-an-amortised-deliberation). The planner does not go through
this door — it never plans for a want being walked — but a caller that wants the absorption
asks here.

**A STEP IS CHECKED WHEN IT IS TAKEN, AND NOT BY THIS LAYER** (#916). Before a head is handed to its
taker the executor says it is about to be, `taking`; whether the present still admits it is the
precondition's question, a word of the layer above that this one does not speak, and the answer
comes back through the door a step blocked always came by — `end_at` — so a head whose intention
ended as it was about to be taken is not taken.

**AND WHAT HAPPENED IS SAID**, by the executor's own signals, each carrying an event of
`events.py`: an intention resolved, a head about to be taken, a command, a saying, and — made only
where heard — a step taken when its act is recorded, the verdict on it, and how many stand after a
walk. The executor decides each, so it says each; whoever writes history and metrics hears them.
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent import clock
from agent.lifecycle import Signal
from agent.ontology import ACTION, OREXIS, STATE, local_of
from agent.stance import stance
from agent.store import (NAMESPACES, Raw, add_quads, bind, catalogue_of, entry, forget_graph, graphs_of, instant,
                         quads, quads_for_pattern, revisions_of, rows, update)

from .events import Commanded, IntentionResolved, Said, StepAnswered, StepTaken, Taking, Walked  # noqa: F401 — the events it says
from .implementation import FICTIVE, operations
from .ontology import (ADDS_GRAPH, ANSWERED_WITHIN_S, COMMITTED_STEP_GRAPH, EXECUTION, LANDS_WITHIN_S, PATIENCE_S,
                       RETRACTS_GRAPH, committed_graph, intentions_graph)

log = logging.getLogger("executor")

#  THE PATIENCE, in seconds, where the agent's self graph states no `execution:patienceS`.
DEFAULT_PATIENCE_S = 60.0

INTENTION = EXECUTION + "Intention"
ADOPTS = EXECUTION + "adopts"
INTENTION_GRAPH = EXECUTION + "IntentionGraph"
RECORDED = OREXIS + "Recorded"
#  The head a standing intention is AT — not the whole plan, which `execution:step` names, and
#  not the first step for ever: what `by` points at moves as the world answers each step.
BY = EXECUTION + "by"
STEP = EXECUTION + "step"
PURSUES = EXECUTION + "pursues"
ADOPTED_AT = EXECUTION + "adoptedAt"
RESOLVED_AT = EXECUTION + "resolvedAt"
OUTCOME = EXECUTION + "outcome"
ENDS_AFTER = EXECUTION + "endsAfter"
_TAKES_Q = """SELECT ?takes WHERE { $action orexis:takes ?takes }"""
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  HOW OFTEN THE TIMEKEEPER LOOKS WHEN NOTHING IS DUE, in the agent's seconds: a plan another
#  hand wrote into the intentions is found within this, and a `wake` finds it at once.
POLL_S = 1.0

#  THE HEAD OF A PLAN is the step nothing else points `execution:then` at — read rather than
#  written, since the chain already says it and a second statement of the same fact is a
#  second thing to keep true.
_HEAD_Q = """
SELECT ?step WHERE {
  GRAPH $plan {
    ?step a execution:Step ; execution:partOf $root .
    FILTER NOT EXISTS { ?other execution:then ?step } } }"""

_STEPS_Q = """
SELECT ?step WHERE { GRAPH $plan { ?step a execution:Step ; execution:partOf $root } }"""

#  WHAT THIS AGENT IS WALKING: every want an intention adopted and not resolved pursues. Asked
#  by pattern and not by graph, because a case may hold the intentions under a name of its own.
_WALKING_Q = """
SELECT DISTINCT ?want WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
ORDER BY ?want"""

_STANDING_Q = """
SELECT ?intention ?want ?at ?adopted WHERE {
  GRAPH $intentions {
    ?intention a execution:Intention ;
               execution:pursues ?want ;
               execution:adoptedAt ?adopted .
    OPTIONAL { ?intention execution:by ?at }
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done } } }
ORDER BY ?adopted"""

#  THE HEAD OF EVERY STANDING INTENTION: when it may be taken — `execution:notBefore` where the
#  plan says, at once where it says nothing — whether it has been taken (an act saying so), and
#  where it has, the two graphs it predicts in and when that should show, at the earliest and at
#  the latest.
_HEADS_Q = """
SELECT ?intention ?step ?due ?kept ?act ?taken ?lands ?after ?adds ?retracts WHERE {
  GRAPH $intentions {
    ?intention a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
    OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken } }
  OPTIONAL { GRAPH ?plan { ?step execution:notBefore ?due } }
  OPTIONAL { GRAPH ?plan { ?step execution:keptBelow ?kept } }
  OPTIONAL { GRAPH ?plan { ?step execution:landsAt ?lands } }
  OPTIONAL { GRAPH ?plan { ?step execution:notAfter ?after } }
  OPTIONAL { GRAPH ?plan { ?step execution:adds ?adds } }
  OPTIONAL { GRAPH ?plan { ?step execution:retracts ?retracts } } }
ORDER BY ?due ?intention"""

#  WHAT A STEP PREDICTS: the two graphs it names, wherever it names them — each side its own
#  OPTIONAL over any graph, since the step is typed in its plan AND in its committed-step graph,
#  and a read anchored on the type in one graph was handed the committed step's row, which names
#  neither, and called the step one that predicts nothing (measured on the tower).
_PREDICTED_Q = """
SELECT ?adds ?retracts WHERE {
  OPTIONAL { GRAPH ?a { $step execution:adds ?adds } }
  OPTIONAL { GRAPH ?r { $step execution:retracts ?retracts } } } LIMIT 1"""

#  THE GRAPHS A PLAN'S STEPS PREDICT IN, each with which side it is — what crosses with a plan
#  handed in from another store.
_STEP_GRAPHS_Q = """SELECT ?g ?side WHERE { GRAPH $plan { ?step ?side ?g . VALUES ?side { execution:adds execution:retracts } } }"""

#  DOES THE PRESENT FAIL THE STEP — a fact it adds with no equal in the present, or a fact it
#  retracts with one. Asked over the readings and their revisions as the default graph, the two
#  graphs the step names reached by name; the step is answered where this is false. Equality is
#  SPARQL's own, so `5` and `5.0` are one value as they were under the rounded canonical form,
#  and a literal of another type is not equal (a-steps-prediction-is-two-graphs-it-names).
_ADDS_MISSING = """{ GRAPH $adds { ?s ?p ?o } FILTER NOT EXISTS { ?s ?p ?x . FILTER(?x = ?o) } }"""
_RETRACTS_STANDING = """{ GRAPH $retracts { ?s ?p ?o } ?s ?p ?x . FILTER(?x = ?o) }"""

#  A FICTIVE STEP'S WRITE: what it retracts leaves the state and what it adds enters it, the two
#  graphs read where they stand and the terms carried over as they are.
_RETRACT_U = """DELETE { GRAPH $state { ?s ?p ?o } } WHERE { GRAPH $retracts { ?s ?p ?o } }"""
_ADD_U = """INSERT { GRAPH $state { ?s ?p ?o } } WHERE { GRAPH $adds { ?s ?p ?o } }"""

#  WHETHER THE INTENTIONS GRAPH IS CLASSIFIED YET, and every plan published and adopted by none, with its want.
_CLASSIFIED_Q = """SELECT ?k WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph a ?k } } LIMIT 1"""
_PLANS_Q = """
SELECT ?plan ?want WHERE { GRAPH $cat { ?plan a orexis:PlanGraph } GRAPH ?plan { ?plan execution:pursues ?want }
  FILTER NOT EXISTS { GRAPH ?g { ?i execution:adopts ?plan } } }
ORDER BY ?plan"""

#  EVERY INTENTION ONE OF WHOSE STEPS HAS BEEN TAKEN.
_BEGUN_Q = """SELECT DISTINCT ?intention WHERE { GRAPH $intentions {
  ?intention a execution:Intention ; execution:step ?step . ?act execution:of ?step } }"""

#  THE WANT THAT KEEPS A STEP BELOW, wherever planning wrote it, and the agent a store is told of.
_KEPT_BY_Q = """SELECT ?want WHERE { GRAPH ?g { $step execution:keptBy ?want } } LIMIT 1"""
_ME_Q = """SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id } LIMIT 1"""

_PURSUES_Q = """SELECT ?want WHERE { GRAPH $intentions { $intention execution:pursues ?want } }"""

#  WHAT A STEP KEPT BELOW WAITS ON: the intentions walking the want it was refined into — standing,
#  or ended and how.
_REFINED_Q = """
SELECT ?outcome WHERE { GRAPH $intentions { $act execution:refinedBy ?want .
  ?below a execution:Intention ; execution:pursues ?want .
  OPTIONAL { ?below execution:outcome ?outcome } } }"""

#  WHAT HANGS BELOW AN INTENTION: every standing intention walking a want one of its steps' acts
#  was refined into.
_BELOW_Q = """
SELECT DISTINCT ?below WHERE { GRAPH $intentions {
  $intention execution:step ?step . ?act execution:of ?step ; execution:refinedBy ?want .
  ?below a execution:Intention ; execution:pursues ?want .
  FILTER NOT EXISTS { ?below execution:resolvedAt ?at } } }"""


#  WHAT A STEP SAYS OF ITSELF IN WORDS OTHER THAN THIS LAYER'S: the action and the filling are
#  the layer above's and the package's to spell, and this layer repeats them without reading.
_STEP_Q = """
SELECT ?p ?o WHERE {
  GRAPH ?plan { $step ?p ?o . FILTER(!STRSTARTS(STR(?p), STR(execution:)) && ?p != rdf:type) } }
ORDER BY ?p"""

_NEXT_Q = """SELECT ?next WHERE { GRAPH ?plan { $step execution:then ?next } } LIMIT 1"""

#  A COMMITTED STEP'S LANDING WINDOW, off the plan it is in: when it may be taken and when its change
#  lands at the earliest and at the latest, each where the plan says one.
_PLACED_Q = """
SELECT ?opens ?lands ?after WHERE { GRAPH $plan {
  OPTIONAL { $step execution:notBefore ?opens } OPTIONAL { $step execution:landsAt ?lands }
  OPTIONAL { $step execution:notAfter ?after } } }"""

#  EVERY STEP AN INTENTION COMMITTED TO.
_COMMITTED_Q = """SELECT ?step WHERE { GRAPH $intentions { $intention execution:step ?step } }"""

#  WHETHER A STEP HAS BEEN TAKEN — an act on record saying so; at an intention's head, a step in flight.
_IN_FLIGHT_Q = """SELECT ?act WHERE { GRAPH $intentions { ?act execution:of $step ; execution:taken true } } LIMIT 1"""

#  WHETHER AN INTENTION HAS ENDED — asked of a head's intention once `taking` has been heard.
_RESOLVED_Q = """SELECT ?at WHERE { GRAPH $intentions { $intention execution:resolvedAt ?at } } LIMIT 1"""

#  WHETHER AN INTENTION ENDS AFTER A STEP — planning reconsidered the want it pursues (#905).
_ENDS_AFTER_Q = """SELECT ?i WHERE { GRAPH $intentions { $intention execution:endsAfter $step . BIND($intention AS ?i) } } LIMIT 1"""
#  WHETHER AN INTENTION ENDS AFTER ANY STEP — given up but for its step in flight (#921).
_ENDING_Q = """SELECT ?step WHERE { GRAPH $intentions { $intention execution:endsAfter ?step } } LIMIT 1"""

#  WHEN A COMMITTED STEP'S WINDOW CLOSES, on the catalogue row of the graph this executor wrote for it.
_WINDOW_Q = """SELECT ?end WHERE { GRAPH $cat { $g a $kind ; dcterms:temporal ?p . OPTIONAL { ?p orexis:end ?end } } }"""

#  CLOSE A WINDOW AT AN INSTANT: the period's end becomes $now, whatever it was.
_CLOSE_U = """
DELETE { GRAPH $cat { ?p orexis:end ?old } }
INSERT { GRAPH $cat { ?p orexis:end $now } }
WHERE  { GRAPH $cat { $g dcterms:temporal ?p . OPTIONAL { ?p orexis:end ?old } } }"""

#  EVERY COMMITTED STEP WHOSE WINDOW HAS ENDED by $now — this agent's where the store says whose.
_ENDED_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a $kind $owned ; dcterms:temporal ?p . ?p orexis:end ?end . FILTER(?end <= $now) } }
ORDER BY ?g"""

#  THE RECORD THAT A STEP WAS TAKEN — history, and only history.
_ACT_U = """
INSERT DATA { GRAPH $intentions { $act a execution:Act ; execution:of $step ;
                              execution:takenAt $taken_at ; execution:doneAt $done_at ;
                              execution:taken $taken } }"""

_ADVANCE_U = """
DELETE { GRAPH $intentions { $intention execution:by $step } }
INSERT { GRAPH $intentions { $intention execution:by $next } }
WHERE  { GRAPH $intentions { $intention execution:by $step } }"""


_XSD = "http://www.w3.org/2001/XMLSchema#"


def _decimal(seconds: float) -> ox.Literal:
    """A stretch in seconds as the decimal a rule divides by."""
    return ox.Literal(f"{seconds:.3f}".rstrip("0").rstrip(".") or "0", datatype=ox.NamedNode(_XSD + "decimal"))


class Standing:
    """One commitment that has not been resolved: what it pursues, where it has got to, and
    when it was adopted."""

    __slots__ = ("uri", "want", "at", "adopted")

    def __init__(self, uri: str, want: str, at: str | None, adopted: datetime):
        self.uri, self.want, self.at, self.adopted = uri, want, at, adopted

    def age_s(self, now: datetime | None = None) -> float:
        """How long this has been standing, in the agent's seconds."""
        return ((now or clock.now()) - self.adopted).total_seconds()

    def __repr__(self) -> str:
        return f"Standing({self.uri.rsplit('#', 1)[-1]} for {self.want.rsplit('#', 1)[-1]})"


class Executor:
    """One agent's intentions, and what carries them out.

    Handed the beliefs engine and the one identifier a process is told. The intentions are a graph
    of the belief base unless another store is handed in, as a case may; a plan arrives through
    the beliefs, never through a call. It holds no beliefs of its own: the patience is a
    STANCE, `execution:patienceS` read off the agent's self graph when the executor is made,
    because how stubborn to be is the agent's own word about itself and not the executor's
    constant — `DEFAULT_PATIENCE_S` is what holds where the agent states none. Read once, since
    the self graph is authored at birth and nothing revises a stance.
    """

    def __init__(self, beliefs: ox.Store, agent_id: str, intentions: ox.Store | None = None,
                 holder: str | None = None, *, take=None, fictive: bool = False,
                 poll_s: float = POLL_S, on_write=None):
        self.intentions = intentions if intentions is not None else beliefs
        self.beliefs = beliefs
        self.id = agent_id
        self.holder = holder
        self.graph = intentions_graph(agent_id)
        self.take = take if take is not None else self.say
        self.all_fictive = fictive
        self.poll_s = poll_s
        #  HOW LONG A STANDING COMMITMENT ABSORBS ANOTHER FOR ITS WANT, and how long past its latest
        #  landing a step may go unanswered: the agent's stance, the default where it states none.
        self.patience_s = stance(beliefs, PATIENCE_S, DEFAULT_PATIENCE_S)
        #  `on_write(graph)`, told of every graph the executor writes as the world, so what the rules
        #  conclude of it is concluded.
        self.on_write = on_write
        #  WHAT THE EXECUTOR SAYS HAPPENED, its own words for whoever connects, each carrying an event
        #  of `events.py`: an intention ended, with the want it pursued and how; a head about to be
        #  taken; a step's command,
        #  sized from the present, for whatever reaches the device; a document a step said, and the
        #  agents it is to; and, made only where heard, a step taken, the verdict on one, a walk.
        self.intention_resolved = Signal("intention_resolved")
        #  AND BEFORE A HEAD IS HANDED TO ITS TAKER, that it is about to be: whoever judges whether the
        #  present still admits it hears this, and ends the intention through a door below if not.
        self.taking = Signal("taking")
        self.commanded = Signal("commanded")
        self.said = Signal("said")
        self.step_taken = Signal("step_taken")
        self.step_answered = Signal("step_answered")
        self.walked = Signal("walked")

        #  TELEMETRY AND NOT A ROW: the desire each adopted plan's want was derived under, as
        #  planning said it when it published the plan, so what happens to it can be told by
        #  desire. The intentions keep commitments, not the reasoning behind them.
        self._desires: dict[str, str] = {}
        self._work: queue.SimpleQueue = queue.SimpleQueue()
        self._inflight: set[str] = set()
        self._next_due: datetime | None = None
        self._cv = threading.Condition()
        self._threads: list[threading.Thread] = []
        self._stopped = False

    # --- committing ---------------------------------------------------------------------------

    def commit_plans(self) -> list[str]:
        """Adopt every plan published and adopted by no intention yet — an `orexis:PlanGraph` in the
        beliefs, its root saying the want it pursues — as a caller with no runtime to hear the
        publishing would. The intentions graph where anything was committed."""
        committed = False
        cat = Raw(f"<{catalogue_of(self.beliefs)}>")
        for r in rows(self.beliefs, _PLANS_Q, (), cat=cat):
            committed = self.commit(self.beliefs, r["plan"], r["want"]) is not None or committed
        return [self.graph] if committed else []

    def adopt(self, plan: str, want: str, *, desire: str | None = None) -> list[str]:
        """Adopt the plan `plan` published for `want`, heard as planning publishes it, with the
        `desire` the want was derived under where it says one. The intentions graph where anything
        was committed."""
        if desire is not None:
            self._desires[want] = desire
        return [self.graph] if self.commit(self.beliefs, plan, want) is not None else []

    def end_for(self, want: str, outcome: str) -> list[str]:
        """End every standing intention pursuing `want` that has taken no step yet, with `outcome` —
        its want reached before its plan began: rain before the dose. A plan that has begun is walked
        to its end, since a want met partway says nothing of what its later steps are for — a round
        opened answers a call, and the round must still be cleared."""
        begun = {r["intention"] for r in rows(self.intentions, bind(_BEGUN_Q, intentions=Raw(f"<{self.graph}>")))}
        ended = [s.uri for s in self.standing() if s.want == want and s.uri not in begun]
        for intention in ended:
            self.resolve(intention, outcome)
        return [self.graph] if ended else []

    def end_at(self, step: str, outcome: str) -> list[str]:
        """End the standing intention that stands at `step`, with `outcome` — its next step can no
        longer be taken."""
        ended = [s.uri for s in self.standing() if s.at == step]
        for intention in ended:
            self.resolve(intention, outcome)
        return [self.graph] if ended else []

    def supersede_after(self, step: str) -> list[str]:
        """End the standing intention that stands at `step` AFTER it, `superseded` — planning has
        reconsidered the want it pursues and a joint plan replaces its untaken steps (#905).

        COMMITMENT HAS TWO GRAINS, and this is where they part (knowledge/domain/execution/commitment.md).
        A step IN FLIGHT — handed to its taker, an act on record, and not yet answered — is never
        cancelled: the intention is marked to end after it, `execution:endsAfter`, and the step is
        held to its prediction as any taken step is, so it lands, or fails by the patience, and only
        then does the intention resolve. The untaken steps are the plan's and go now: their committed
        windows close, since a committed step not yet started is a prediction and not a commitment,
        and a replaced plan takes it with it. An intention whose head has not been taken has nothing
        in flight, and resolves at once."""
        mine = Raw(f"<{self.graph}>")
        for held in self.standing():
            if held.at != step:
                continue
            taken = rows(self.intentions, bind(_IN_FLIGHT_Q, intentions=mine, step=step))
            if not taken:
                self.resolve(held.uri, "superseded")
                continue
            update(self.intentions, f"INSERT DATA {{ GRAPH <{self.graph}> {{ <{held.uri}> <{ENDS_AFTER}> <{step}> }} }}")
            now = clock.now()
            for r in rows(self.intentions, bind(_COMMITTED_Q, intentions=mine, intention=held.uri)):
                if r["step"] != step and not rows(self.intentions, bind(_IN_FLIGHT_Q, intentions=mine, step=r["step"])):
                    self._close_window(r["step"], now)
            log.info("%s: %s ends after %s, its untaken steps replaced", self.id,
                     held.uri.rsplit("#", 1)[-1], local_of(step))
        return [self.graph]

    def commit(self, source: ox.Store, graph: str, want: str) -> str | None:
        """Copy a found plan into the intentions — unless one for this want is already standing
        and younger than the patience, which is the absorption this class exists for.

        None means nothing was committed, and the two reasons are told apart in the log: an
        empty plan (nothing to do) and an absorbed one (already doing it).
        """
        if (held := self.standing_for(want)) is not None:
            age = held.age_s()
            if age < self.patience_s:
                log.debug("%s: absorbed a second plan for %s — %s stands, %.0fs of %.0fs",
                          self.id, want.rsplit("#", 1)[-1], held, age, self.patience_s)
                return None
            #  PAST THE PATIENCE, a new adoption SUPERSEDES the old, and the old is recorded
            #  as dropped with the reason. A commitment abandoned without a reason is
            #  indistinguishable from one forgotten.
            self.resolve(held.uri, "superseded")
        intention = self._adopt(source, graph, want)
        if intention is not None:
            self.wake()
        return intention

    def _adopt(self, source: ox.Store, graph: str, want: str) -> str | None:
        """Adopt the plan in `graph` as an intention. The intention, or None.

        None for an empty plan, which is an answer and not a commitment: the search reached the
        want's met state in no steps, so there is nothing to carry out and nothing to stand. The
        intention is adopted at the clock's instant, stands at the plan's HEAD, names the want it
        pursues and the plan it ADOPTS, and lists the plan's steps. Nothing decides here — whoever
        found the plan decided, and this keeps the record honest (an-intention-is-a-plan-committed-to).

        BY REFERENCE, NOT BY COPY. The plan is planning's, published once under a name of its own, and
        stays; what is written here is the intention's own rows (planning-and-execution-meet-at-the-store).
        A plan found in another store — a case handing the executor one of its own — is brought in whole
        first, under its own name, since a reference must reach it; and the two graphs each of its
        steps predicts in are brought to where the PRESENT is, the beliefs, since that is what they
        are compared with — in the runtime the plan already stands there, published.
        """
        named = Raw(f"<{graph}>")
        node = ox.NamedNode(self.graph)
        steps = [r["step"] for r in rows(source, bind(_STEPS_Q, plan=named, root=named))]
        if not steps:
            log.debug("%s: the plan for %s has no steps — nothing to commit", self.id, want)
            return None
        head = [r["step"] for r in rows(source, bind(_HEAD_Q, plan=named, root=named))]
        if len(head) != 1:
            raise RuntimeError(
                f"the plan in <{graph}> has {len(head)} heads — a plan is a chain, and a chain "
                "has one step nothing follows")
        if source is not self.intentions:
            plan = ox.NamedNode(graph)
            add_quads(self.intentions, (ox.Quad(q.subject, q.predicate, q.object, plan) for q in quads(source, graph)))
        if source is not self.beliefs:
            described = catalogue_of(self.beliefs) is not None
            owner = (self.holder or _me_of(self.beliefs, self.id)) if described else None
            for g in rows(source, bind(_STEP_GRAPHS_Q, plan=named)):
                into = ox.NamedNode(g["g"])
                add_quads(self.beliefs, (ox.Quad(q.subject, q.predicate, q.object, into) for q in quads(source, g["g"])))
                if described:
                    kind = ADDS_GRAPH if g["side"].endswith("adds") else RETRACTS_GRAPH
                    update(self.beliefs, f"INSERT DATA {{ {entry(self.beliefs, g['g'], kind, RECORDED, owner)} }}")
        #  THE INTENTIONS ARE A GRAPH OF THE AGENT'S OWN, classified when first kept, so a lived-in
        #  volume keeps them and a reader asks for them by kind.
        if catalogue_of(self.intentions) is not None and not rows(self.intentions, _CLASSIFIED_Q, (), graph=self.graph):
            update(self.intentions, f"INSERT DATA {{ {entry(self.intentions, self.graph, INTENTION_GRAPH, RECORDED, self.holder or _me_of(self.beliefs, self.id))} }}")
        intention = ox.NamedNode(f"{OREXIS}intention_{self.id}_{uuid.uuid4().hex[:8]}")
        now = clock.now()                       # read once: a read of the clock is a tick in a test
        own = [ox.Quad(intention, _RDF_TYPE, ox.NamedNode(INTENTION), node),
               ox.Quad(intention, ox.NamedNode(PURSUES), ox.NamedNode(want), node),
               ox.Quad(intention, ox.NamedNode(ADOPTED_AT), instant(now), node),
               ox.Quad(intention, ox.NamedNode(ADOPTS), ox.NamedNode(graph), node),
               ox.Quad(intention, ox.NamedNode(BY), ox.NamedNode(head[0]), node)]
        own += [ox.Quad(intention, ox.NamedNode(STEP), ox.NamedNode(s), node) for s in sorted(steps)]
        add_quads(self.intentions, own)
        log.info("%s: committed a plan of %d step(s) for %s", self.id, len(steps),
                 want.rsplit("#", 1)[-1])
        self._commit_windows(graph, sorted(steps), now)
        return intention.value

    # --- the committed steps, as beliefs over their landing windows ------------------------------

    def _commit_windows(self, plan: str, steps: list[str], now: datetime) -> None:
        """Write every step of the adopted plan into the beliefs as a graph of its own, an
        `execution:CommittedStepGraph` holding over the step's LANDING WINDOW — from its
        `execution:notBefore` to its `execution:notAfter`, the latest landing, plus the patience — so that a prediction
        made from now on sees the intention: the window's two ends are happenings, and a drift reads
        the step at any instant inside it (a-prediction-accumulates-rates-between-happenings, the seam
        "committed steps are not yet flows", closed by #849).

        WHAT THE GRAPH HOLDS is the step's filling as the plan states it — the action and a triple per
        parameter, copied as terms and never read, since they are the layer above's and the domain's
        words — its type, and the window's two lengths in seconds (`execution:landsWithinS`, to the
        earliest landing; `execution:answeredWithinS`, to the latest and the patience past it), stated
        as numbers because no rule can measure the stretch between the plan's instants. A step placed
        at no instant opens at the adoption and lands as it is taken; its window is the patience alone. Nothing is written where the beliefs describe no
        graphs, as a bare store a case hands in does not.
        """
        if catalogue_of(self.beliefs) is None:
            return
        owner = self.holder or _me_of(self.beliefs, self.id)
        named = Raw(f"<{plan}>")
        for step in steps:
            placed = next(iter(rows(self.intentions, bind(_PLACED_Q, plan=named, step=step))), {})
            opens = datetime.fromisoformat(placed["opens"]) if placed.get("opens") else now
            lands = max(opens, datetime.fromisoformat(placed["lands"])) if placed.get("lands") else opens
            latest = max(lands, datetime.fromisoformat(placed["after"])) if placed.get("after") else lands
            within, by = (lands - opens).total_seconds(), (latest - opens).total_seconds() + self.patience_s
            graph = committed_graph(self.id, step)
            forget_graph(self.beliefs, graph)
            update(self.beliefs, f"INSERT DATA {{ {entry(self.beliefs, graph, COMMITTED_STEP_GRAPH, RECORDED, owner, start=opens, end=latest + timedelta(seconds=self.patience_s))} }}")
            subject, into = ox.NamedNode(step), ox.NamedNode(graph)
            held = [ox.Quad(subject, _RDF_TYPE, ox.NamedNode(EXECUTION + "Step"), into),
                    ox.Quad(subject, ox.NamedNode(LANDS_WITHIN_S), _decimal(within), into),
                    ox.Quad(subject, ox.NamedNode(ANSWERED_WITHIN_S), _decimal(by), into)]
            held += [ox.Quad(q.subject, q.predicate, q.object, into)
                     for q in quads_for_pattern(self.intentions, subject, graph=plan)
                     if not q.predicate.value.startswith(EXECUTION) and q.predicate != _RDF_TYPE]
            add_quads(self.beliefs, held)
            log.debug("%s: %s is committed from %s, landing within %.0fs and answered within %.0fs",
                      self.id, local_of(step), opens.isoformat(timespec="seconds"), within, by)
            if self.on_write is not None:
                self.on_write(graph)

    def _close_window(self, step: str, now: datetime) -> None:
        """Close the committed step's window at `now`: the world answered the step, or the intention
        ended, so nothing of the step flows past this instant. A window already ended by the clock
        is left as it stands — the sweep takes it — and one closed is said to whoever hears a belief
        written, since what a drift reads changed."""
        if catalogue_of(self.beliefs) is None:
            return
        cat, graph = Raw(f"<{catalogue_of(self.beliefs)}>"), committed_graph(self.id, step)
        found = rows(self.beliefs, _WINDOW_Q, (), cat=cat, g=graph, kind=Raw(f"<{COMMITTED_STEP_GRAPH}>"))
        if not found or (found[0].get("end") and datetime.fromisoformat(found[0]["end"]) <= now):
            return
        update(self.beliefs, bind(_CLOSE_U, cat=cat, g=graph, now=instant(now)))
        if self.on_write is not None:
            self.on_write(graph)

    def _sweep(self, now: datetime) -> None:
        """Forget every committed step whose window has ended by `now`: what ends by the clock is a
        graph with a period, and one sweep drops it. Nobody is told — a graph past its end is handed
        to no reader asking at a later instant, so dropping it changes nothing anyone reads."""
        if catalogue_of(self.beliefs) is None:
            return
        owner = self.holder or _me_of(self.beliefs, self.id)
        ended = rows(self.beliefs, _ENDED_Q, (), cat=Raw(f"<{catalogue_of(self.beliefs)}>"),
                     kind=Raw(f"<{COMMITTED_STEP_GRAPH}>"), now=instant(now),
                     owned=Raw(f"; orexis:beliefsOf <{owner}>" if owner else ""))
        for r in ended:
            forget_graph(self.beliefs, r["g"])

    # --- what stands --------------------------------------------------------------------------

    def standing(self) -> list[Standing]:
        """Every commitment adopted and not resolved, oldest first."""
        return [Standing(r["intention"], r["want"], r.get("at"),
                         datetime.fromisoformat(r["adopted"]))
                for r in rows(self.intentions, bind(_STANDING_Q, intentions=Raw(f"<{self.graph}>")))]

    def walking(self) -> list[str]:
        """Every want a standing commitment pursues — one this agent is WALKING. A search does
        not plan again for one of these, and the derivation does not withdraw one whatever
        its desire now reads: the world has not answered yet, and a plan in flight with
        nothing it was for is worse than a want nothing implies."""
        return [r["want"] for r in rows(self.intentions, _WALKING_Q)]

    def standing_for(self, want: str) -> Standing | None:
        """The commitment standing for this want, or None. One or none: a second plan for one
        want while the first stands is the thing `commit` absorbs.

        AN INTENTION ENDING AFTER ITS STEP IN FLIGHT IS NOT IT (#921). Marked so (`supersede_after`),
        it has given its untaken steps up and stands only until the world answers the step it took,
        so it absorbs nothing: where a belief arriving reopened the want it walks, the plan planning
        then publishes for the same want is its replacement, and is adopted beside it, opening where
        the step in flight lands."""
        mine = Raw(f"<{self.graph}>")
        return next((s for s in self.standing() if s.want == want
                     and not rows(self.intentions, bind(_ENDING_Q, intentions=mine, intention=s.uri))), None)

    # --- resolving ----------------------------------------------------------------------------

    def resolve(self, intention: str, outcome: str) -> None:
        """Say this commitment has ended, and how.

        THE LIFECYCLE IS TWO TIMESTAMPS AND AN OUTCOME, not a state machine: standing is an
        adoption with no resolution, and how it ended is a word. A resolved intention STAYS —
        every one does, with its outcome — because intentions that forgot their resolutions could
        not answer the only question an operator brings to it, which is what this agent
        thought it was doing and why it stopped.
        """
        now = clock.now()
        update(self.intentions, f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention}> <{RESOLVED_AT}> "{now.isoformat()}"^^xsd:dateTime ;
                <{OUTCOME}> "{outcome}" . }} }}""")
        log.info("%s: %s — %s", self.id, intention.rsplit("#", 1)[-1], outcome)
        #  NOTHING OF AN ENDED INTENTION FLOWS ON: every step it committed to closes now, the ones
        #  taken and answered with nothing left to close, the ones never taken with their whole window.
        for r in rows(self.intentions, bind(_COMMITTED_Q, intentions=Raw(f"<{self.graph}>"), intention=intention)):
            self._close_window(r["step"], now)
        want = next(iter(rows(self.intentions, bind(_PURSUES_Q, intentions=Raw(f"<{self.graph}>"), intention=intention))), {})
        self.intention_resolved.emit(IntentionResolved(intention, want.get("want"), outcome,
                                                       desire=self._desires.get(want.get("want"))))
        if outcome not in ("done", "reached"):
            #  NOTHING HANGS BELOW WHAT ENDED UNDONE: an intention walking the want one of this
            #  intention's steps is kept below by is abandoned with it.
            for r in rows(self.intentions, bind(_BELOW_Q, intentions=Raw(f"<{self.graph}>"), intention=intention)):
                self.resolve(r["below"], "abandoned")

    # --- keeping time: one pass -----------------------------------------------------------------

    def tick(self, now: datetime | None = None) -> list[str]:
        """One pass of the timekeeper: hand every head step due at `now` to the queue, and
        hold every head already taken to what it predicted. The steps handed over. Whatever
        is not yet due — a step's opening, a landing, a deadline — is remembered as the
        instant to wake at.

        THE WORLD ANSWERS OR IT DOES NOT. A taken head that predicts something waits at its
        `landsAt`, the earliest its change can show; from then on, every pass asks the present
        whether what the step predicted holds, and moves the intention along when it does. Past
        its `notAfter`, the latest, by the patience with no answer, the step is unmet, the tail is
        dropped with it and the intention resolves `failed` — the search will see the want again
        on its next pass, standing in a present that surprised it. The executor never replans; it
        says what happened.
        """
        now = now or clock.now()
        self._sweep(now)
        due, soonest = [], None
        def wake_at(when):
            nonlocal soonest
            if soonest is None or when < soonest:
                soonest = when
        for r in rows(self.intentions, bind(_HEADS_Q, intentions=Raw(f"<{self.graph}>"))):
            intention, step = r["intention"], r["step"]
            if step in self._inflight:
                continue
            if r.get("act") is None:
                when = datetime.fromisoformat(r["due"]) if r.get("due") else None
                if (when is None or when <= now) and r.get("kept") and not self._kept_by(step):
                    continue                    # kept below: the want that keeps it is planning's to mint
                if when is None or when <= now:
                    self._inflight.add(step)
                    self._work.put((intention, step))
                    due.append(step)
                else:
                    wake_at(when)
                continue
            if not r.get("adds") and not r.get("retracts"):
                continue                        # advanced when it was taken; nothing to hold it to
            lands, latest = self._landing(r, now)
            below = [b.get("outcome") for b in rows(self.intentions, bind(
                _REFINED_Q, intentions=Raw(f"<{self.graph}>"), act=r["act"]))]
            if now < lands:
                wake_at(lands)
            elif self._answered(r.get("adds"), r.get("retracts")):
                self._verdict(intention, step, r, now, landed=True)
                self._advance(intention, step, now)
            elif None in below:
                continue                        # kept below: a plan for it stands, and waits on no clock
            elif below and "done" not in below:
                log.warning("%s: %s could not be kept below — %s fails", self.id, local_of(step),
                            intention.rsplit("#", 1)[-1])
                self._verdict(intention, step, r, now, landed=False)
                self.resolve(intention, "failed")
            elif now >= latest + timedelta(seconds=self.patience_s):
                log.warning("%s: the world did not answer %s by %s — %s fails",
                            self.id, local_of(step), latest.isoformat(), intention.rsplit("#", 1)[-1])
                self._verdict(intention, step, r, now, landed=False, timed_out=True)
                self.resolve(intention, "failed")
            else:
                wake_at(latest + timedelta(seconds=self.patience_s))
        self._next_due = soonest
        return due

    @staticmethod
    def _landing(head: dict, now: datetime) -> tuple[datetime, datetime]:
        """When a taken head should show what it predicted — at the earliest (`landsAt`) and at the
        latest (`notAfter`, the earliest where the plan states none) — each as long after it was
        TAKEN as the plan placed it after its opening. A plan places every step at the instants
        of the worlds it searched, and a step taken late — the step before it waited on a round
        that cleared late, or on a peer — lands late by as much; held to the placed instant, it
        would fail before the world could answer it."""
        if not head.get("lands"):
            return now, now
        lands = datetime.fromisoformat(head["lands"])
        latest = max(lands, datetime.fromisoformat(head["after"])) if head.get("after") else lands
        if head.get("taken") and head.get("due"):
            late = max(timedelta(0), datetime.fromisoformat(head["taken"]) - datetime.fromisoformat(head["due"]))
            lands, latest = lands + late, latest + late
        return lands, latest

    def _answered(self, adds: str | None, retracts: str | None) -> bool:
        """Does the present hold what a step predicted — every fact of its `adds` graph present,
        every fact of its `retracts` graph gone — over the agent's readings as they stand and what
        the rules concluded of them? One ASK, the two graphs reached by name and the present as its
        default graph; a side the step does not name is asked of an empty graph."""
        #  THE READINGS AND THEIR REVISIONS: a step predicts in the concepts the rules conclude —
        #  a dose, that the soil comes to be inside its range — so it is answered when the next
        #  reading is revised to that, and the side lives in the graph derived from the reading's.
        states = graphs_of(self.beliefs, STATE)
        present = [ox.NamedNode(g) for g in (*states, *revisions_of(self.beliefs, *states))]
        failing = ([bind(_ADDS_MISSING, adds=adds)] if adds else []) \
            + ([bind(_RETRACTS_STANDING, retracts=retracts)] if retracts else [])
        return not bool(self.beliefs.query("ASK { " + " UNION ".join(failing) + " }",
                                           prefixes=NAMESPACES, default_graph=present))

    def _advance(self, intention: str, step: str, now: datetime | None = None) -> None:
        """Move the intention to the step after `step`, or resolve it `done` at the last — or
        `superseded`, where it ends after `step` (`supersede_after`): the step in flight was
        answered, and what came after it was replaced. The step's window closes at `now`, since
        the world has answered it. The timekeeper is woken either way: a new head may be due at
        once."""
        if rows(self.intentions, bind(_ENDS_AFTER_Q, intentions=Raw(f"<{self.graph}>"), intention=intention, step=step)):
            self._close_window(step, now or clock.now())
            self.resolve(intention, "superseded")
            self.wake()
            return
        following = next(iter(rows(self.intentions, bind(_NEXT_Q, intentions=Raw(f"<{self.graph}>"), step=step))), None)
        if following is None:
            self.resolve(intention, "done")
        else:
            update(self.intentions, bind(_ADVANCE_U, intentions=Raw(f"<{self.graph}>"),
                                         intention=intention, step=step, next=following["next"]))
            self._close_window(step, now or clock.now())
        self.wake()

    def walk(self, now: datetime | None = None) -> int:
        """Tick and drain until nothing more happens at this instant: how many steps were taken. One
        tick hands the due heads over and holds the taken ones to what they predicted, and a head
        moved along in one tick is handed over only by the next, so the walk ends on two ticks in a
        row that hand nothing over."""
        taken, idle = 0, 0
        while idle < 2:
            if self.tick(now):
                taken += self.drain()
                idle = 0
            else:
                idle += 1
            now = clock.now()
        if self.walked.connected:
            self.walked.emit(Walked(standing=len(self.walking())))
        return taken

    # --- executing: one pass ----------------------------------------------------------------------

    def drain(self) -> int:
        """One pass of the executor, on the calling thread: take every step in the queue. How
        many were taken — a head whose intention ended as it was about to be taken is not."""
        taken = 0
        while True:
            try:
                item = self._work.get_nowait()
            except queue.Empty:
                return taken
            if item is not None and self._take(*item):
                taken += 1

    def _take(self, intention: str, step: str) -> bool:
        """Take one step: say it is about to be taken, hand its rows to `take`, record the act, and
        move the intention along — to the next step, or to `done`; to `failed` where the taking
        raised. False where the step was not handed over at all: its intention ended as it was
        about to be.

        EVERY STEP IS CHECKED WHEN IT IS TAKEN (#916), and not here. `taking` says the head is about
        to be handed over, at the instant it is; whoever judges whether the present still admits it
        — planning, whose word the precondition is — hears that, and where the present does not,
        ends the intention through the door a step blocked always came by (`end_at`). So the
        intention is asked again after it is said: one ended takes no step, records no act and
        writes nothing, and the want is planning's again. Asked only where somebody hears, since a
        case driving the executor alone has nobody to judge."""
        #  THE RECORD IS THE ACT'S, NOT THE STEP'S: when the taker was handed the step and
        #  when it returned, in the one timeline. The step's own instants are the plan's
        #  requirement (`notBefore`) and prediction (`landsAt`), and stay what they were.
        taken_at = clock.now()
        if self.taking.connected:
            self.taking.emit(Taking(step, taken_at))
            if rows(self.intentions, bind(_RESOLVED_Q, intentions=Raw(f"<{self.graph}>"), intention=intention)):
                log.info("%s: %s was not taken — %s ended as it was about to be", self.id, local_of(step),
                         intention.rsplit("#", 1)[-1])
                self._inflight.discard(step)
                self.wake()
                return False
        said = self.step_of(step)
        refined = None
        try:
            #  THE ORDER THE CORE DECIDES IN: an implementation that reaches the world is taken —
            #  a dose predicts the soil inside its range, which sensing's rules conclude, and is
            #  still a command; only a step that would be taken fictively is asked whether a
            #  level beneath keeps it, and is fictive where none does.
            refined = self._kept_by(step)
            if refined is None:
                self._taker_for(step)(said, intention)
            taken = True
        except Exception as exc:                                        # noqa: BLE001
            log.error("%s: step %s could not be taken: %s", self.id, local_of(step), exc)
            taken = False
        done_at = clock.now()
        act = f"{step}.act.{taken_at.strftime('%Y%m%dT%H%M%S%f')}"
        update(self.intentions, bind(_ACT_U, intentions=Raw(f"<{self.graph}>"), act=act, step=step,
                                     taken_at=instant(taken_at), done_at=instant(done_at),
                                     taken=Raw("true" if taken else "false")))
        if refined is not None:
            #  KEPT BELOW: the act says which want, and the step waits on it and not on the clock.
            update(self.intentions, f"INSERT DATA {{ GRAPH <{self.graph}> {{ <{act}> <{EXECUTION}refinedBy> <{refined}> }} }}")
        if self.step_taken.connected:
            self.step_taken.emit(StepTaken(step, taken_at, taken=taken, **self._about(intention, step)))
        #  THE INTENTION MOVES BEFORE THE STEP LEAVES FLIGHT: a tick between the two would
        #  find the old head and hand it over twice. A step that predicts something does not
        #  move here at all — the act on record is what the next tick reads, and the world's
        #  answer is what moves it.
        if not taken:
            self.resolve(intention, "failed")
        elif not any(next(iter(rows(self.intentions, bind(_PREDICTED_Q, step=step))), {}).values()):
            self._advance(intention, step, done_at)
        self._inflight.discard(step)
        self.wake()
        return True

    def _kept_by(self, step: str) -> str | None:
        """The want that keeps `step` one level down, where planning has minted one, or None."""
        found = rows(self.beliefs, _KEPT_BY_Q, (), step=step)
        return found[0]["want"] if found else None

    def _taker_for(self, step: str):
        """Who takes this step: the fictive taker where the step's action is fictive, or the
        executor is fictive throughout; otherwise `take`, the seam to real code."""
        if self.all_fictive:
            return self.fictive
        action = self.step_of(step).get("fills")
        fictive = action is not None and any(op.kind == FICTIVE for op in operations(self.beliefs, action))
        return self.fictive if fictive else self.take

    def step_of(self, step: str) -> dict:
        """A step's rows in words other than this layer's, keyed by the local part of each
        predicate — what `take` is handed, with the step's own IRI under `step`."""
        said = {"step": step}
        for r in rows(self.intentions, bind(_STEP_Q, intentions=Raw(f"<{self.graph}>"), step=step)):
            said[local_of(r["p"])] = r["o"]
        return said

    def _about(self, intention: str, step: str) -> dict:
        """What an event about `step` of `intention` carries: the want the intention pursues, the
        desire it was derived under, the action the step fills and the values it takes, by the local
        name of each parameter — an IRI's local name, a literal's text."""
        pursued = rows(self.intentions, bind(_PURSUES_Q, intentions=Raw(f"<{self.graph}>"), intention=intention))
        want = pursued[0]["want"] if pursued else None
        said = self.step_of(step)
        action, parameters = said.get("fills"), []
        if action:
            for r in rows(self.beliefs, _TAKES_Q, graphs_of(self.beliefs, ACTION), action=action):
                parameter = local_of(r["takes"])
                if parameter in said:
                    value = said[parameter]
                    parameters.append((parameter, local_of(value) if "://" in value else value))
        return {"want": want, "desire": self._desires.get(want), "action": local_of(action) if action else None,
                "parameters": tuple(parameters)}

    def _verdict(self, intention: str, step: str, head: dict, now: datetime, *, landed: bool,
                 timed_out: bool = False) -> None:
        """Say the verdict on `step` at `now`, where anybody hears it: landed or not, and how late the
        world answered it — `now`, when it was seen to, less the `landsAt` the plan placed — in the
        agent's own seconds, since both instants are its timeline's."""
        if not self.step_answered.connected:
            return
        late = (round((now - datetime.fromisoformat(head["lands"])).total_seconds(), 3)
                if head.get("lands") and (landed or timed_out) else None)
        self.step_answered.emit(StepAnswered(step, now, landed=landed, late_s=late, timed_out=timed_out,
                                             **self._about(intention, step)))

    def say(self, said: dict, intention: str) -> None:
        """The default taking: the step's name, and what fills it, in the log."""
        filling = " ".join(f"{k}={local_of(v) if '://' in v else v}"
                           for k, v in sorted(said.items()) if k != "step")
        log.info("%s: taking %s of %s — %s", self.id, local_of(said["step"]),
                 intention.rsplit("#", 1)[-1], filling or "nothing filled")

    def fictive(self, said: dict, intention: str) -> None:
        """The taking of a step whose action is FICTIVE: say the step's name, then write what
        it predicted into the agent's readings, so the present answers because the executor
        was the world.

        AN ACTION IS FICTIVE where its implementation says so (`execution:Fictive`), read off
        the action a step fills when the step is taken: a hanoi move and a courier's drive have no instrument to report
        what taking them did, so a step held to the world would wait out the patience and
        fail for ever. Its world is the belief base, and the step's own prediction is the
        physics. An executor built `fictive` takes every step so, the shorthand for a world
        that exists only in the store. The write is one update over the two graphs the step
        names, the terms carried as they are — it rebuilt each fact from a canonical form that
        kept an IRI and a text, rounded a number and refused a blank node, while the form was a
        string's (a-steps-prediction-is-two-graphs-it-names).
        """
        self.say(said, intention)
        predicted = next(iter(rows(self.intentions, bind(_PREDICTED_Q, step=said["step"]))), {})
        if not any(predicted.values()):
            return
        (state, *_) = graphs_of(self.beliefs, STATE) or [None]
        if state is None:
            raise RuntimeError(f"{self.id}: a fictive step has no state graph to write into")
        writes = ([bind(_RETRACT_U, state=state, retracts=predicted["retracts"])] if predicted.get("retracts") else []) \
            + ([bind(_ADD_U, state=state, adds=predicted["adds"])] if predicted.get("adds") else [])
        update(self.beliefs, " ;\n".join(writes))
        if self.on_write is not None:
            self.on_write(state)                # the rules conclude of the world the step moved

    # --- the threads -------------------------------------------------------------------------------

    def start(self) -> None:
        """Start the two threads. Idempotent."""
        with self._cv:
            if self._threads or self._stopped:
                return
            self._threads = [threading.Thread(target=self._run, name=f"{self.id}-executes", daemon=True),
                             threading.Thread(target=self._keep_time, name=f"{self.id}-keeps-time", daemon=True)]
        for t in self._threads:
            t.start()

    def wake(self) -> None:
        """Tell the timekeeper to look now rather than at its next cadence."""
        with self._cv:
            self._cv.notify_all()

    def stop(self, timeout: float | None = 5.0) -> None:
        """Finish the step in hand and exit both threads. Idempotent."""
        with self._cv:
            if self._stopped:
                return
            self._stopped = True
            self._cv.notify_all()
            threads = list(self._threads)
        self._work.put(None)                    # the sentinel: drained after everything before it
        for t in threads:
            if t is not threading.current_thread():
                t.join(timeout)

    def _run(self) -> None:
        while True:
            item = self._work.get()
            if item is None:
                return
            try:
                self._take(*item)
            except BaseException as exc:                                # noqa: BLE001
                log.error("%s: the executing thread outlives this: %s", self.id, exc)

    def _keep_time(self) -> None:
        while True:
            with self._cv:
                if self._stopped:
                    return
            try:
                self.tick()
            except BaseException as exc:                                # noqa: BLE001
                log.error("%s: the timekeeper outlives this: %s", self.id, exc)
            with self._cv:
                if self._stopped:
                    return
                wait = self.poll_s
                if self._next_due is not None:
                    wait = min(wait, max(0.0, (self._next_due - clock.now()).total_seconds()))
                self._cv.wait(clock.real_delay(wait))

    def __len__(self) -> int:
        return len(self.standing())


def _me_of(beliefs: ox.Store, agent_id: str) -> str | None:
    """The agent a belief base holds with the id it was told, off public knowledge, or None."""
    found = rows(beliefs, _ME_Q, graphs_of(beliefs, OREXIS + "PublicGraph"), id=ox.Literal(agent_id))
    return found[0]["me"] if found else None
