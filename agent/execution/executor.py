"""The executor: the intentions this agent is committed to, and the two threads that carry
a commitment out.

**IT OWNS THE INTENTIONS STORE, AND NOTHING ELSE WRITES THEM.** A plan found above is handed
to `commit` — the planner's crossing hands every plan of a pass here — and from that moment
it is the executor's: any plan among the intentions is scheduled, and every adoption wakes
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
`landsAt` for the present to hold what it predicted, every addition present and every
retraction gone over the agent's readings, and `execution:by` moves to the next step when it
does, the last step resolving the intention `done`; past the landing by the patience with no
answer, the intention resolves `failed`. A step that predicts nothing moves as soon as it is
taken. A FICTIVE ACTION — an `execution:Fictive` operation in its implementation — is taken by writing the step's own prediction into the readings, so the
present answers because nothing else could have; an executor built `fictive` takes every
step so, the shorthand for a pure simulation. The one seam is `take`, a callable handed the step's rows: it is where a step will reach real
code — an actuator, a message on the bus — and how an action names its taker is not
decided here. A `take` that raises records the act as not taken and resolves the intention
`failed`, and the executing thread outlives it.

**THE PATIENCE IS STILL HERE**, unchanged from the keeper this was: a second plan for a want
already standing is absorbed inside the patience and supersedes past it, which is the
amortisation (an-intention-is-an-amortised-deliberation). The planner does not go through
this door — it never plans for a want being walked — but a caller that wants the absorption
asks here.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import uuid
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent import clock
from agent.hash_named_graph import facts_of
from agent.ontology import OREXIS, STATE, local_of
from agent.store import Raw, add_quads, bind, revisions_of, graphs_of, instant, quads, rows, update

from .implementation import FICTIVE, operations
from .ontology import EXECUTION, intentions_graph

log = logging.getLogger("executor")

DEFAULT_PATIENCE_S = 60.0

INTENTION = EXECUTION + "Intention"
#  The head a standing intention is AT — not the whole plan, which `execution:step` names, and
#  not the first step for ever: what `by` points at moves as the world answers each step.
BY = EXECUTION + "by"
STEP = EXECUTION + "step"
PURSUES = EXECUTION + "pursues"
ADOPTED_AT = EXECUTION + "adoptedAt"
RESOLVED_AT = EXECUTION + "resolvedAt"
OUTCOME = EXECUTION + "outcome"
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
#  where it has, what it predicted and when that should show.
_HEADS_Q = """
SELECT ?intention ?step ?due ?act ?taken ?lands ?predicts WHERE {
  GRAPH $intentions {
    ?intention a execution:Intention ; execution:by ?step .
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
    OPTIONAL { ?step execution:notBefore ?due }
    OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken }
    OPTIONAL { ?step execution:landsAt ?lands }
    OPTIONAL { ?step execution:predicts ?predicts } } }
ORDER BY ?due ?intention"""

_PREDICTS_Q = """SELECT ?predicts WHERE { GRAPH $intentions { $step execution:predicts ?predicts } }"""


#  WHAT A STEP SAYS OF ITSELF IN WORDS OTHER THAN THIS LAYER'S: the action and the filling are
#  the layer above's and the package's to spell, and this layer repeats them without reading.
_STEP_Q = """
SELECT ?p ?o WHERE {
  GRAPH $intentions { $step ?p ?o . FILTER(!STRSTARTS(STR(?p), STR(execution:)) && ?p != rdf:type) } }
ORDER BY ?p"""

_NEXT_Q = """SELECT ?next WHERE { GRAPH $intentions { $step execution:then ?next } }"""

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


def _term(fact) -> ox.NamedNode | ox.Literal:
    """A canonical term back as the engine's: an IRI, a text with its language or datatype, a
    number as a decimal. A blank node's content is not a term and is refused."""
    kind = fact[0]
    if kind == "iri":
        return ox.NamedNode(fact[1])
    if kind == "num":
        return ox.Literal(repr(fact[1]), datatype=ox.NamedNode(_XSD + "decimal"))
    if kind == "lit":
        tag = fact[2]
        return ox.Literal(fact[1], language=tag) if "://" not in tag else ox.Literal(fact[1], datatype=ox.NamedNode(tag))
    raise ValueError(f"a fictive world cannot write a fact hanging off a blank node: {fact!r}")


def _quad(fact, graph: str) -> ox.Quad:
    s, p, o = fact
    return ox.Quad(_term(s), ox.NamedNode(p), _term(o), ox.NamedNode(graph))


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

    Handed the beliefs engine and the one identifier a process is told. The intentions store is
    its own — made here where none is handed in, since this layer owns it — and `intentions` is
    how a planner is told where a plan goes. It holds no beliefs of its own: the patience is a
    PICK, read off the beliefs store where the agent's picks are, because how stubborn to be is
    the agent's own belief and not the executor's constant.
    """

    def __init__(self, beliefs: ox.Store, agent_id: str, intentions: ox.Store | None = None,
                 holder: str | None = None, *, take=None, fictive: bool = False,
                 poll_s: float = POLL_S):
        self.intentions = intentions if intentions is not None else ox.Store()
        self.beliefs = beliefs
        self.id = agent_id
        self.holder = holder
        self.graph = intentions_graph(agent_id)
        self.take = take if take is not None else self.say
        self.all_fictive = fictive
        self.poll_s = poll_s
        self._work: queue.SimpleQueue = queue.SimpleQueue()
        self._inflight: set[str] = set()
        self._next_due: datetime | None = None
        self._cv = threading.Condition()
        self._threads: list[threading.Thread] = []
        self._stopped = False

    # --- committing ---------------------------------------------------------------------------

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
        """Copy the plan in `graph` of `source` into the intentions. The intention, or None.

        None for an empty plan, which is an answer and not a commitment: the search reached
        the want's met state in no steps, so there is nothing to carry out and nothing to
        stand. The intention is adopted at the clock's instant, stands at the plan's HEAD and
        names the want it pursues. Nothing decides here — whoever found the plan decided,
        and this keeps the record honest (an-intention-is-a-plan-committed-to).

        A COPY AND NOT A REWRITE, which is why the search writes its steps in this layer's
        words: a translation on the way would be a second place the two shapes could
        disagree. What the search adds of its own crosses with the rest and is not read
        here. QUADS AND NOT TEXT: a serialise-and-reparse relabels blank nodes.
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
        #  EVERY INTENTION'S STEPS ARE ITS OWN. A plan names its steps for the want and the worlds
        #  it searched, so a second plan for one want — after the first failed — names its steps
        #  as the first did, and the act the first recorded would read as the second's step taken.
        #  A name an earlier intention holds is tagged with this one's; a fresh one is kept.
        tag = uuid.uuid4().hex[:8]
        held = {s for s in steps if next(self.intentions.quads_for_pattern(ox.NamedNode(s), None, None, node), None)}
        own_name = {s: ox.NamedNode(f"{s}.{tag}" if s in held else s) for s in steps}
        renamed = lambda t: own_name.get(t.value, t) if isinstance(t, ox.NamedNode) else t
        add_quads(self.intentions, (ox.Quad(renamed(q.subject), q.predicate, renamed(q.object), node)
                                    for q in quads(source, graph)))
        intention = ox.NamedNode(f"{OREXIS}intention_{self.id}_{tag}")
        own = [ox.Quad(intention, _RDF_TYPE, ox.NamedNode(INTENTION), node),
               ox.Quad(intention, ox.NamedNode(PURSUES), ox.NamedNode(want), node),
               ox.Quad(intention, ox.NamedNode(ADOPTED_AT), instant(clock.now()), node),
               ox.Quad(intention, ox.NamedNode(BY), own_name[head[0]], node)]
        own += [ox.Quad(intention, ox.NamedNode(STEP), own_name[s], node) for s in sorted(steps)]
        add_quads(self.intentions, own)
        log.info("%s: committed a plan of %d step(s) for %s", self.id, len(steps),
                 want.rsplit("#", 1)[-1])
        return intention.value

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
        want while the first stands is the thing `commit` absorbs."""
        return next((s for s in self.standing() if s.want == want), None)

    # --- resolving ----------------------------------------------------------------------------

    def resolve(self, intention: str, outcome: str) -> None:
        """Say this commitment has ended, and how.

        THE LIFECYCLE IS TWO TIMESTAMPS AND AN OUTCOME, not a state machine: standing is an
        adoption with no resolution, and how it ended is a word. A resolved intention STAYS —
        every one does, with its outcome — because intentions that forgot their resolutions could
        not answer the only question an operator brings to it, which is what this agent
        thought it was doing and why it stopped.
        """
        update(self.intentions, f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention}> <{RESOLVED_AT}> "{clock.now().isoformat()}"^^xsd:dateTime ;
                <{OUTCOME}> "{outcome}" . }} }}""")
        log.info("%s: %s — %s", self.id, intention.rsplit("#", 1)[-1], outcome)

    # --- keeping time: one pass -----------------------------------------------------------------

    def tick(self, now: datetime | None = None) -> list[str]:
        """One pass of the timekeeper: hand every head step due at `now` to the queue, and
        hold every head already taken to what it predicted. The steps handed over. Whatever
        is not yet due — a step's opening, a landing, a deadline — is remembered as the
        instant to wake at.

        THE WORLD ANSWERS OR IT DOES NOT. A taken head that predicts something waits at its
        `landsAt`; from then on, every pass asks the present whether what the step predicted
        holds, and moves the intention along when it does. Past the landing by the patience
        with no answer, the step is unmet, the tail is dropped with it and the intention
        resolves `failed` — the search will see the want again on its next pass, standing in
        a present that surprised it. The executor never replans; it says what happened.
        """
        now = now or clock.now()
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
                if when is None or when <= now:
                    self._inflight.add(step)
                    self._work.put((intention, step))
                    due.append(step)
                else:
                    wake_at(when)
                continue
            if not r.get("predicts"):
                continue                        # advanced when it was taken; nothing to hold it to
            lands = self._landing(r, now)
            if now < lands:
                wake_at(lands)
            elif self._answered(r["predicts"]):
                self._advance(intention, step)
            elif now >= lands + timedelta(seconds=self.patience_s):
                log.warning("%s: the world did not answer %s by %s — %s fails",
                            self.id, local_of(step), lands.isoformat(), intention.rsplit("#", 1)[-1])
                self.resolve(intention, "failed")
            else:
                wake_at(lands + timedelta(seconds=self.patience_s))
        self._next_due = soonest
        return due

    @staticmethod
    def _landing(head: dict, now: datetime) -> datetime:
        """When a taken head should show what it predicted: as long after it was TAKEN as the
        plan placed its landing after its opening. A plan places every step at the instants of
        the worlds it searched, and a step taken late — the step before it waited on a round
        that cleared late, or on a peer — lands late by as much; held to the placed instant, it
        would fail before the world could answer it."""
        if not head.get("lands"):
            return now
        lands = datetime.fromisoformat(head["lands"])
        if head.get("taken") and head.get("due"):
            lands += max(timedelta(0), datetime.fromisoformat(head["taken"]) - datetime.fromisoformat(head["due"]))
        return lands

    def _answered(self, predicts: str) -> bool:
        """Does the present hold what a step predicted — every addition present, every
        retraction gone — over the agent's readings as they stand and what the rules concluded
        of them?"""
        said = json.loads(predicts)
        #  THE READINGS AND THEIR REVISIONS: a step predicts in the concepts the rules conclude —
        #  a dose, that the soil comes to be inside its range — so it is answered when the next
        #  reading is revised to that, and the side lives in the graph derived from the reading's.
        states = graphs_of(self.beliefs, STATE)
        present = {json.dumps(f) for f in facts_of(self.beliefs, *states, *revisions_of(self.beliefs, *states))}
        return all(json.dumps(f) in present for f in said.get("adds", ())) \
            and not any(json.dumps(f) in present for f in said.get("retracts", ()))

    def _advance(self, intention: str, step: str) -> None:
        """Move the intention to the step after `step`, or resolve it `done` at the last. The
        timekeeper is woken either way: a new head may be due at once."""
        following = next(iter(rows(self.intentions, bind(_NEXT_Q, intentions=Raw(f"<{self.graph}>"), step=step))), None)
        if following is None:
            self.resolve(intention, "done")
        else:
            update(self.intentions, bind(_ADVANCE_U, intentions=Raw(f"<{self.graph}>"),
                                         intention=intention, step=step, next=following["next"]))
        self.wake()

    # --- executing: one pass ----------------------------------------------------------------------

    def drain(self) -> int:
        """One pass of the executor, on the calling thread: take every step in the queue. How
        many were taken."""
        taken = 0
        while True:
            try:
                item = self._work.get_nowait()
            except queue.Empty:
                return taken
            if item is not None:
                self._take(*item)
                taken += 1

    def _take(self, intention: str, step: str) -> None:
        """Take one step: hand its rows to `take`, record the act, and move the intention
        along — to the next step, or to `done`; to `failed` where the taking raised."""
        said = self.step_of(step)
        #  THE RECORD IS THE ACT'S, NOT THE STEP'S: when the taker was handed the step and
        #  when it returned, in the one timeline. The step's own instants are the plan's
        #  requirement (`notBefore`) and prediction (`landsAt`), and stay what they were.
        taken_at = clock.now()
        try:
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
        #  THE INTENTION MOVES BEFORE THE STEP LEAVES FLIGHT: a tick between the two would
        #  find the old head and hand it over twice. A step that predicts something does not
        #  move here at all — the act on record is what the next tick reads, and the world's
        #  answer is what moves it.
        if not taken:
            self.resolve(intention, "failed")
        elif not rows(self.intentions, bind(_PREDICTS_Q, intentions=Raw(f"<{self.graph}>"), step=step)):
            self._advance(intention, step)
        self._inflight.discard(step)
        self.wake()

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
        that exists only in the store. The fact is rebuilt from its canonical form, which
        keeps an IRI and a text and rounds a number, and a fact hanging off a blank node is
        refused rather than guessed at.
        """
        self.say(said, intention)
        (predicts,) = rows(self.intentions, bind(_PREDICTS_Q, intentions=Raw(f"<{self.graph}>"), step=said["step"])) or [{}]
        if not predicts:
            return
        (state, *_) = graphs_of(self.beliefs, STATE) or [None]
        if state is None:
            raise RuntimeError(f"{self.id}: a fictive step has no state graph to write into")
        change = json.loads(predicts["predicts"])
        for fact in change.get("retracts", ()):
            self.beliefs.remove(_quad(fact, state))
        add_quads(self.beliefs, (_quad(fact, state) for fact in change.get("adds", ())))

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

    # --- the one figure -----------------------------------------------------------------------

    @property
    def patience_s(self) -> float:
        """How long a standing commitment blocks re-adoption of one for the same want.

        A CONSTANT HERE, AND IT SHOULD NOT STAY ONE. It is an OPINION — the agent's own
        belief, which a review may move inside whatever room its world leaves — and it was
        read from the graph an agent's picks live in. That graph is reached by NAME and has no
        class, nothing in this tree writes one, and the mechanism that would is review, which
        this tree does not load. So the read is gone with the rest of picks and the figure is
        `DEFAULT_PATIENCE_S` until something can revise it (a-pick-is-read-not-guessed).
        """
        return DEFAULT_PATIENCE_S

    def __len__(self) -> int:
        return len(self.standing())
