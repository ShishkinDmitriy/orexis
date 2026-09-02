"""The keeper: the ledger of what this agent is committed to, and the patience that makes a
commitment mean something.

**The kernel's, and granted by nothing.** This was Keeping, a member of a family
whose premise was a stake AND a lever. What that could never explain is why `Agent.__init__`
already built an intention STORE for every agent regardless: the modality was unconditional and
the thing that writes it was a grant. Commitment is not plug-in-able, so both are the kernel's.

The family's second member was sketched and never written — something that weighs a commitment
against what has changed since it was made, the open-minded commitment of the BDI literature.
That remains a real alternative, and it is a PICK when someone builds it, not a grant: how
stubborn to be is already each agent's own belief, and which rule decides to drop belongs beside
it rather than in the world graph.

**This existed before it had a name, as module state.** `bidding.pending` was an intention to
observe; a bid awaiting its claim was an intention to acquire; both lived in Python attributes
that died with the process and answered to nothing. They are rows in a graph now, with an
adoption time, a resolution, and a reason — so an operator can ask what an agent thought it was
doing, and phase 4's deliberator can ask what already stands before deciding anything.

**Nothing here decides, and the seam is deliberate.** Whoever acts calls `adopt` when it acts
and `satisfy`/`drop` when the world answers; this module only keeps the ledger honest. The one
piece of policy it owns is the COMMITMENT itself: `adopt` refuses to re-adopt what is already
standing and younger than the agent's patience, and that refusal is the amortisation the
decision record is named for — within your patience, a second impulse to do the same thing is
absorbed, not re-decided. With an LLM deliberator that absorption is the cost model.

Vocabulary: `agent/ontology.ttl` (the intention terms are the kernel's). Rules: its shapes.ttl. Derivation: its
rules.ru. See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

import logging
import threading

from rdflib import URIRef
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from assembly.contribute import answer as contribution, contributes
from . import ledger
from .act import Act
from .store import bindings

from .graphs import intentions_graph
from .ontology import ANSWER, OREXIS, PLAN_FAILED, PLAN_FINISHED, REPORTS

#  What an intention is made of — the mind's own words, and they were the kernel's already
#  (the-mind-is-six-graphs). What has joined them is the four figures the KEEPING member used to
#  own privately: a patience, a suspicion threshold and the bounds on the patience. They are the
#  kernel's now for the same reason the class is — every agent keeps a ledger, so a figure that
#  governs keeping is not one package's private setting.
INTENTION_CLASS = OREXIS + "Intention"
BY = OREXIS + "by"
PURSUES = OREXIS + "pursues"
ADOPTED_AT = OREXIS + "adoptedAt"
RESOLVED_AT = OREXIS + "resolvedAt"
_SH_NODE_SHAPE = URIRef("http://www.w3.org/ns/shacl#NodeShape")


def condition_shape(root: str, focus: str, binds: str):
    """A condition that is naturally a query, as a shape that CONFORMS when the query binds.

    SHACL's own polarity runs the other way — a `sh:sparql` constraint's rows are violations
    — so the query goes under `sh:not`: the shape conforms exactly where the constraint is
    violated, which is where `binds` returns rows for `$this`. Held `until`, the act is
    released when the query binds; `until_not`, when it stops binding. Written this way
    rather than inverted at the call site, so the ledger reads as the caller meant it.
    """
    import rdflib
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    g = rdflib.Graph()
    node, negated, constraint = rdflib.URIRef(root), rdflib.BNode(), rdflib.BNode()
    g.add((node, rdflib.RDF.type, SH.NodeShape))
    g.add((node, SH.targetNode, rdflib.URIRef(focus)))
    g.add((node, SH["not"], negated))
    g.add((negated, rdflib.RDF.type, SH.NodeShape))
    g.add((negated, SH.sparql, constraint))
    g.add((constraint, SH.select, rdflib.Literal(binds)))
    return g


def _rdflib_term(t):
    """One engine term as rdflib's, for the shape compiler, which walks rdflib graphs."""
    import pyoxigraph as ox
    import rdflib
    if isinstance(t, ox.NamedNode):
        return rdflib.URIRef(t.value)
    if isinstance(t, ox.BlankNode):
        return rdflib.BNode(t.value)
    if t.language:
        return rdflib.Literal(t.value, lang=t.language)
    return rdflib.Literal(t.value, datatype=rdflib.URIRef(t.datatype.value))
OUTCOME = OREXIS + "outcome"
BECAUSE_OF = OREXIS + "becauseOf"

# The means — what kind of act the commitment is to.

# The commitment policy — the belief, not the mechanism.
PATIENCE_S = OREXIS + "patienceS"

# The expectation — the END, judged apart from the action.
EXPECTS_RISE = OREXIS + "expectsRise"
BASELINE_VALUE = OREXIS + "baselineValue"
BASELINE_AT = OREXIS + "baselineAt"
EXPECTS_DELTA = OREXIS + "expectsDelta"
#  `orexis:deadlineAt` WAS HERE: the watch's deadline is the ACT's `orexis:notAfter` now — one window,
#  read by the keeper, the bidder's give-up and the host's redeem check alike
#  (an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan). `ledger` migrates it.
END_MET = OREXIS + "endMet"
END_VERIFIED_AT = OREXIS + "endVerifiedAt"
SUSPECT_AFTER = OREXIS + "suspectAfter"
MET_FRACTION = OREXIS + "metFraction"


def kernel(name: str) -> str:
    """A mind state, by local name."""
    return OREXIS + name

# What this package asks OF others — namespaces, never Python. The direction a lever moves the
# property it is priced in is the domain's statement (#127), copied into the expectation row;
# sensing is asked to look once so the baseline is the freshest thing on record.
#  The sensing family, the two market directions and the direction query WERE HERE. The keeper
#  used to look up which way a dose should move the value (the market's word) and ask sensing
#  to look once (the sensing family's name) when a watch opened — the last package words this
#  file named. Both are the ACTOR's to say: whoever opened the watch knows which way its act
#  pushes and how long a reading of that property takes to arrive, and nudges its own sensing.

# How many consecutive unmet ends make an affordance suspect — the family's figure, like the
# patience bounds: what this society tolerates before it stops trusting a claim.
_SUSPECT_Q = """
SELECT ?n WHERE {
  GRAPH ?g { orexis:Intention orexis:suspectAfter ?n }
} LIMIT 1"""

# The fraction of an expected delta that counts as the world answering (#165). Carried by
# `orexis:Intention` itself now that there is no family to hang it on — what a society accepts as
# evidence is a fact about intentions, not about one way of keeping them.
_MET_FRACTION_Q = """
SELECT ?f WHERE {
  GRAPH ?g { orexis:Intention orexis:metFraction ?f }
} LIMIT 1"""


@dataclass(frozen=True)
class KeepingBeliefs:
    """The commitment policy, which is the agent's own opinion."""

    patience_s: int


#  `KEEPING_PICKS` — the belief reader that fills this dataclass — WAS HERE and is the
#  deliberator's now (#452): a pick is a belief, a belief is read by the search and by nothing
#  beneath it, and progression never reads one. The container reads the pick and HANDS the
#  patience in; a keeper that was handed none says so the moment anything needs it.


class NoPatience(LookupError):
    """This agent states no `orexis:patienceS`, and something asked for it.

    An agent that keeps commitments and states no patience is missing something
    `orexis:Intention` needs, not something it was granted — `orexis:KeeperShape` refuses to let an
    agent with a stake boot without one, so reaching this is a stakeless agent being asked to
    commit, which is a bug in the asker."""


@dataclass(frozen=True)
class Standing:
    """One unresolved commitment, as a reader gets it back: the ACT committed to, and the want
    it pursues. `orexis:by` names the act node (an-act-is-a-filled-action…); the action, the
    lever and the quantity are the act's, read through it."""

    uri: str
    act: Act
    want: str               # the desire's node — `orexis:pursues`; the kernel's only key besides the act
    adopted_at: datetime

    @property
    def action(self) -> str:
        return self.act.action

    @property
    def via(self) -> str | None:
        return self.act.via or None

    def age_s(self, now: datetime | None = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.adopted_at).total_seconds()


@dataclass(frozen=True)
class OpenExpectation:
    """A watch still on: the act happened, and the world has yet to answer as promised."""

    uri: str
    action: str
    want: str
    rises: bool             # which way the act promised to move the value
    baseline: float
    baseline_at: datetime
    deadline: datetime
    expected_delta: float | None = None  # how far the act should move it, when the actor knows


class Keeper:
    """The keeper. Speaks to no topic; its callers are its siblings, through the agent.

    NOT a `Module`, and it was one. `Module` is the container's contract for what a capability
    plugs in — the choir's points, `publish`, the injections — and a layer may not import the
    container that assembles it. What the keeper needs of that contract is the four names the
    runtime asks of everything in its module list (`name`, `CAPABILITY`, `start`, `stop`) and
    one contribution (`reports`), which `assembly.contribute` answers for any object. So it
    states those itself, and the choir finds it exactly as it finds a module.
    """

    name = "intention"
    CAPABILITY = ""     # nothing a world grants — `provider()` can never return the keeper

    def answer(self, term: str):
        """Whatever fills one point on me, as a bound method — or None. The same door a
        `Module` has, so whoever walks `agent.modules` asking by term finds this too."""
        return contribution(self, term)

    def __init__(self, agent):
        self.agent = agent
        self.me = agent.me
        self.log = logging.getLogger(f"{agent.id}.{self.name}")
        self.graph = intentions_graph(agent.id)
        self._picks = None
        #  A volume from before the ledger keyed on the want: rows carrying a property are
        #  given the want that property names for this agent, once, at construction.
        about_of = {r["want"]: r["about"] for r in bindings(agent.desires.query_union(
            f"SELECT ?want ?about WHERE {{ <{self.me.uri}> orexis:holds ?want . "
            f"?want orexis:about ?about }}"))}
        if (n := ledger.migrate_ledger(agent.intentions, self.graph, about_of)):
            self.log.info("ledger migrated: %d row(s) keyed by a property now pursue a want", n)
        if (n := ledger.migrate_ledger_acts(agent.intentions, self.graph)):
            self.log.info("ledger migrated: %d row(s) naming an action now commit to an act", n)
        #  THE HOLDS (#512): re-armed from the ledger's `orexis:until` rows on every belief
        #  write, and their deadlines on the scheduler. A restart loses a deadline's clock
        #  and keeps the condition — the next write re-asks it — which is the honest half.
        self._deadlines: dict = {}
        self._compiled_conditions: dict = {}
        self._reconsidering = False
        self._claim_lock = threading.Lock()
        self._claimed: set = set()
        self._holding = True               # ask once; `reconsider` learns whether any stands
        agent.beliefs.on_write(self._on_written)

    @property
    def beliefs(self) -> KeepingBeliefs:
        """The commitment policy, HANDED IN by the container and never read here.

        It used to be read from the desire modality on first use — lazily, because reading it
        eagerly turned "this agent states no patience" into "this agent cannot start" and
        killed `world/sensing`'s stakeless agent. Since #452 progression reads no belief at
        all: the container reads `KEEPING_PICKS` (the deliberator's) and assigns the result
        through the setter below, or assigns nothing where the agent states none. The check
        is not softened: `orexis:KeeperShape` still REFUSES to let an agent with a stake boot
        without a patience inside the constitutional bounds, and an agent that reaches a
        commitment with none raises `NoPatience` here, naming the missing term.
        """
        if self._picks is None:
            raise NoPatience(f"{self.agent.id} states no patience (orexis:patienceS) and was asked "
                             "to keep a commitment")
        return self._picks

    @beliefs.setter
    def beliefs(self, picks: KeepingBeliefs) -> None:
        """Install a policy directly, skipping the read.

        A setter because the attribute WAS one, and two callers legitimately assign it: a test
        pinning behaviour at a chosen patience, and any future `on_belief_revised` taking up a
        re-picked one. Making it lazy must not quietly turn an assignment into an AttributeError
        at the one moment a revision lands.
        """
        self._picks = picks

    def start(self) -> None:
        """Nothing to start. THE TICK WAS HERE — on my patience clock, hand every want to the
        search — and it is the deliberator's now (#452): a clock that asks the search is the
        search's clock, and progression may not import the layer above it. The patience is
        still mine, and the deliberator reads its interval off `beliefs.patience_s`."""

    def stop(self) -> None:
        """Nothing to stop; the ledger is a graph and outlives the process on purpose."""

    # --- the ledger, written -------------------------------------------------------------

    def adopt(self, act, want: str, because: str, via: str | None = None,
              until=None, until_not=None, not_after: datetime | None = None,
              when_lapsed: str = "take") -> str | None:
        """Commit to one ACT toward one want. Returns the intention's IRI, or None.

        `act` is an `Act` — the plan's head, sized, through its lever — or, for an actor
        committing on its own event with nothing sized (a held claim), the action's IRI and
        the lever as `via`. Either way the ledger holds an act NODE: `orexis:by` names it, and it
        carries `orexis:fills` the action, `orexis:through` the lever, `orexis:quantity` and the window
        (an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan).

        KEYED ON (ACTION, WANT) and nothing else: a want is its node, and the kernel no longer
        knows what one is about (the-stake-is-sensings-want). Two commitments about one
        property but different wants were always distinct — a dealer owing water to fern and
        to tomato holds two Serving rows — and the property was only ever the coarser key.

        `via` is the lever the plan's head goes through — written as `orexis:through`, so the
        ledger says which valve or venue and the actor handed the row later knows too.
        Execution passes it; an actor adopting on its own event (a held claim) may not.

        `desire` is which end this serves — the bounds an agent is held to, or the obligation a
        claim raised. Optional, because the first three means predate desires having names; a
        commitment without one is keyed as it always was. WITH one, two commitments about the
        same property but different desires are distinct: a dealer owing water to fern and to
        tomato holds two Apply rows that would otherwise be indistinguishable, so satisfying
        one would satisfy both and the patience would absorb the second impulse as the first.

        **None is the amortisation**: an intention with the same means and property already
        stands and is younger than my patience, so the impulse is absorbed rather than
        re-decided — the caller should treat it exactly as it treats its own cooldowns. A
        standing one PAST my patience is superseded: resolved as dropped with the reason
        recorded, and the new commitment adopted, because honouring a commitment forever is as
        wrong as honouring it not at all.
        """
        if isinstance(act, str):
            act = Act(action=act, via=via or "")
        action = act.action
        now = datetime.now(timezone.utc)
        for standing in self.standing(action=action, want=want):
            if standing.age_s(now) <= self.beliefs.patience_s:
                return None
            self._resolve(standing, "dropped",
                          f"outwaited: stood {standing.age_s(now):.0f}s against a patience "
                          f"of {self.beliefs.patience_s}s, superseded by a new adoption")
        stem = uuid.uuid4().hex[:8]
        uri = f"{OREXIS}intent_{self.agent.id}_{stem}"
        act_uri = f"{OREXIS}act_{self.agent.id}_{stem}"
        xsd = "http://www.w3.org/2001/XMLSchema#"
        facts = [f'<{kernel("fills")}> <{action}>']
        if act.via:
            facts.append(f'<{kernel("through")}> <{act.via}>')
        if act.for_agent:
            facts.append(f'<{kernel("forAgent")}> <{act.for_agent}>')
        if act.quantity is not None:
            facts.append(f'<{kernel("quantity")}> "{act.quantity}"^^<{xsd}decimal>')
        if act.not_before:
            facts.append(f'<{kernel("notBefore")}> "{act.not_before.isoformat()}"^^<{xsd}dateTime>')
        if act.not_after:
            facts.append(f'<{kernel("notAfter")}> "{act.not_after.isoformat()}"^^<{xsd}dateTime>')
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> a <{kernel("Intention")}> ;
    <{kernel("pursues")}> <{want}> ;
    <{kernel("by")}> <{act_uri}> ;
    <{kernel("step")}> <{act_uri}> ;
    <{kernel("adoptedAt")}> "{now.isoformat()}"^^<{xsd}dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
  <{act_uri}> a <{kernel("Act")}> ; {" ; ".join(facts)} .
}} }}""")
        self.log.info("adopted %s for %s: %s", action.rsplit("#", 1)[-1], _short(want), because)
        self._tell("adopted", action, want, because)
        if until is not None or until_not is not None:
            self.hold(uri, until=until, until_not=until_not, not_after=not_after,
                      when_lapsed=when_lapsed)
        return uri

    # --- an intention held until a condition (#512, #514) --------------------------------

    def hold(self, intention_uri: str, until=None, until_not=None,
             not_after: datetime | None = None, when_lapsed: str = "take") -> None:
        """Hold an adopted intention until a condition — or until `not_after`, whichever first.

        PROGRESSION'S PRIMITIVE, and the whole of the middle layer's job in one call: adopt,
        wait, take on feedback. The wait is two things. A condition on the world, re-asked
        whenever a belief lands (`Store.on_write`), so the hold ends the moment the world
        answers and never on a clock's guess; and a deadline on the scheduler, so a world that
        never answers does not hold the act forever — taken as lapsed (a held claim redeems
        blind rather than never) or dropped, as the adopter said.

        TWO POLARITIES, ONE OF THEM (#514): `until` releases when the condition HOLDS,
        `until_not` when it stops holding — hold while the round is open. ONE FORM: a SHAPE,
        an rdflib graph whose one named `sh:NodeShape` is the condition, compiled here into
        the select the store runs — conformance for `until`, violation for `until_not`. A
        condition that is naturally a query is a shape carrying a `sh:sparql` constraint,
        the form SHACL already has (`condition_shape` builds one). The ledger keeps the shape
        ON THE ACT the intention stands at, so a sovereign asking sees what an act waits for.
        """
        if (until is None) == (until_not is None):
            raise ValueError("a hold is `until` or `until_not`, exactly one")
        if when_lapsed not in ("take", "drop"):
            raise ValueError(f"whenLapsed is `take` or `drop`, not {when_lapsed!r}")
        predicate = kernel("until") if until is not None else kernel("untilNot")
        condition = until if until is not None else until_not
        if not_after is not None:
            self.window(intention_uri, not_after)
        self._hold_step(intention_uri, predicate, condition, not_after, when_lapsed)

    def _hold_step(self, intention_uri: str, predicate: str, condition, not_after,
                   when_lapsed: str) -> None:
        """Write a condition on the act the intention stands at, arm its deadline, and ask
        at once whether it already answers. ON THE ACT: the same node that was planned is
        the one that waits, is taken, and is answered — its place in the plan is a link."""
        node, triples = self._condition_triples(intention_uri, condition)
        self.agent.intentions.update(f"""
INSERT {{ GRAPH <{self.graph}> {{
  ?act <{predicate}> <{node}> ; <{kernel("whenLapsed")}> "{when_lapsed}" .
  {triples} }} }}
WHERE  {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("by")}> ?act }} }}""")
        if not_after is not None:
            delay = (not_after - datetime.now(timezone.utc)).total_seconds()
            from .scheduler import scheduler
            self._deadlines[intention_uri] = scheduler().at(
                max(0.0, delay), lambda: self.lapse(intention_uri))
        self._holding = True
        self.reconsider()                  # the condition may hold already

    def _condition_triples(self, intention_uri: str, condition) -> tuple[str, str]:
        """The condition as ledger triples: the shape's own graph, and its one named root."""
        import rdflib
        if not isinstance(condition, rdflib.Graph):
            raise TypeError("a condition is a shape — an rdflib graph with one named "
                            "sh:NodeShape; a query is a shape with a sh:sparql constraint "
                            "(`condition_shape`)")
        roots = [s for s in condition.subjects(rdflib.RDF.type, _SH_NODE_SHAPE)
                 if isinstance(s, rdflib.URIRef)]
        if len(roots) != 1:
            raise ValueError("a shape condition is one graph with exactly one named sh:NodeShape")
        return str(roots[0]), condition.serialize(format="nt")

    def held(self) -> list[tuple]:
        """Every act still waiting: `(holder, select, predicate)` — the select the store
        runs, compiled from the shape: conformance for `until` and `answeredWhen`, violation
        for `untilNot`, so rows always mean the wait is over — and which wait it was. A
        READINESS wait (`until`, `untilNot`) holds a STANDING intention and releases its act;
        a COMPLETION wait (`answeredWhen`) holds an expectation on an intention the means
        already RESOLVED — resolving the means is where the watch on the end begins — and
        answers with the verdict. The holder is the `Standing` or the `OpenExpectation`."""
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?i ?p ?node WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("by")}> ?act .
  ?act ?p ?node ; <{kernel("whenLapsed")}> ?when .
  ?node a sh:NodeShape .
  FILTER(?p IN (<{kernel("until")}>, <{kernel("untilNot")}>, <{kernel("answeredWhen")}>))
  FILTER NOT EXISTS {{ ?i <{END_MET}> ?m }} }} }}"""))
        standing = {s.uri: s for s in self.standing()}
        watches = {w.uri: w for w in self.open_expectations()}
        out = []
        for r in rows:
            if r["p"] == kernel("answeredWhen"):
                holder = watches.get(r["i"])
            else:
                holder = standing.get(r["i"])
            if holder is not None:
                out.append((holder, self._compiled(r["node"], r["p"] != kernel("untilNot")), r["p"]))
        return out

    def _compiled(self, node: str, holds: bool) -> str:
        """The select a shape condition compiles to, once per node: conformance where the
        hold releases when the shape HOLDS, violation where it releases when it stops."""
        key = (node, holds)
        if key not in self._compiled_conditions:
            import rdflib
            from . import violation
            g = rdflib.Graph()
            for quad in self.agent.intentions.quads(self.graph):
                g.add(tuple(_rdflib_term(t) for t in (quad.subject, quad.predicate, quad.object)))
            shape = g.cbd(rdflib.URIRef(node))
            compile = violation.entered_select if holds else violation.unmet_select
            self._compiled_conditions[key] = compile(shape, rdflib.URIRef(node))
        return self._compiled_conditions[key]

    def reconsider(self) -> None:
        """Re-ask every held condition; release the intentions whose condition says so.

        Called after every belief write while anything is held, on the writer's thread —
        the release hands the act to the loop and waits, as any take does. Re-entrant
        writes (the release itself writes the ledger) find the guard and return.
        """
        #  NO LOCK HERE, and the absence is load-bearing: a release hands the act to the
        #  loop and WAITS, the loop's take writes beliefs, and that write calls back into
        #  this method on the loop's thread. A lock held across the release deadlocked the
        #  agent; the flag lets the nested call return and the outer one finish.
        if not self._holding or self._reconsidering:
            return
        self._reconsidering = True
        try:
            held = self.held()
            self._holding = bool(held)
            now = datetime.now(timezone.utc)
            for holder, select, predicate in held:
                try:
                    rows = bindings(self.agent.beliefs.query_over(
                        select, *self.agent.beliefs.public_graphs(),
                        *self.agent.beliefs.recorded_graphs()))
                except Exception as exc:                        # noqa: BLE001 — a bad select
                    self.log.error("the condition %s waits for will not run: %s",
                                   _short(holder.uri), exc)
                    continue
                deadline = (holder.deadline if isinstance(holder, OpenExpectation)
                            else holder.act.not_after)
                if rows:
                    self._answered(holder, predicate)
                elif deadline is not None and now >= deadline:
                    #  THE DEADLINE, checked here as well as on the scheduler: a write that
                    #  lands after it lapses the wait at once, on this thread, rather than
                    #  a clock's tick later.
                    self._lapse(holder, predicate)
        finally:
            self._reconsidering = False

    def _claim(self, intention_uri: str) -> bool:
        """End this hold, once. Two roads reach a hold — a write on the writer's thread and
        the deadline on the loop's — and both may find it still held; the first to claim it
        ends it, the second finds it gone. The lock covers the claim and the ledger's
        unhold only, never a release or a verdict, which is what deadlocked before."""
        with self._claim_lock:
            if intention_uri in self._claimed:
                return False
            self._claimed.add(intention_uri)
            self._unhold(intention_uri)
            return True

    def _answered(self, holder, predicate: str) -> None:
        """The wait is over: a readiness wait releases the act, a completion wait is met."""
        if not self._claim(holder.uri):
            return
        if predicate == kernel("answeredWhen"):
            self._verdict(holder, True, "moved as promised: an observation later than the "
                                        "baseline shows the property past the threshold")
        else:
            self._release(holder, "the condition it was held for answers now")

    def _lapse(self, holder, predicate: str) -> None:
        when = self._when_lapsed(holder.uri)     # read before the claim removes it
        if not self._claim(holder.uri):
            return
        if predicate == kernel("answeredWhen"):
            self._verdict(holder, False,
                          f"deadline passed, baseline {holder.baseline} — the act was "
                          f"honoured and the world did not answer as the graph promised")
        elif when == "drop":
            self._resolve(holder, "dropped",
                          "the deadline passed and the condition it waited for never answered")
        else:
            self._release(holder, "the deadline passed before the condition answered — "
                                  "taken as lapsed rather than never")

    def lapse(self, intention_uri: str) -> None:
        """The deadline passed before the condition answered: take as lapsed, drop, or — for
        a completion wait — the verdict unmet. The scheduler's road; `reconsider` takes the
        same road on a write that lands past the deadline."""
        for holder, _, predicate in self.held():
            if holder.uri == intention_uri:
                self._lapse(holder, predicate)

    def _when_lapsed(self, intention_uri: str) -> str:
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?when WHERE {{ GRAPH <{self.graph}> {{
  <{intention_uri}> <{kernel("by")}> ?act . ?act <{kernel("whenLapsed")}> ?when }} }}"""))
        return rows[0]["when"] if rows else "take"

    def _release(self, standing: Standing, because: str) -> None:
        from .execution import carry_out

        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{ <{standing.uri}> <{BECAUSE_OF}> {_literal(because)} . }} }}""")
        self.log.info("releasing %s: %s", standing.action.rsplit("#", 1)[-1], because)
        carry_out(self.agent, standing.act, None, standing.uri)

    def _unhold(self, intention_uri: str) -> None:
        entry = self._deadlines.pop(intention_uri, None)
        if entry is not None:
            entry.cancel()
        #  The condition's own triples stay in the ledger as the record of what was waited
        #  for; only the hold — the pointer and the lapse rule — goes.
        self.agent.intentions.update(f"""
DELETE {{ GRAPH <{self.graph}> {{ ?act ?p ?c ; <{kernel("whenLapsed")}> ?w }} }}
WHERE  {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("by")}> ?act .
          ?act ?p ?c ; <{kernel("whenLapsed")}> ?w .
          FILTER(?p IN (<{kernel("until")}>, <{kernel("untilNot")}>, <{kernel("answeredWhen")}>)) }} }}""")

    def _on_written(self) -> None:
        if self._holding:
            self.reconsider()

    def satisfy(self, action: str, want: str | None, because: str) -> list[str]:
        """The world answered: whatever stood for this action and want is done — or, with the
        want omitted, for this action toward anything.

        Returns the resolved rows' IRIs, because resolving the MEANS is where an expectation
        about the END begins — the caller hands them straight to `expect`.

        Naming the desire is what keeps one debt from discharging another: without it, a dose
        that answered fern's claim would resolve tomato's too, since both are Apply rows about
        soil moisture. Omitted, it resolves every row for the means and property, which is
        what every caller predating desires meant and still action.
        """
        resolved = []
        for standing in self.standing(action=action, want=want):
            self._resolve(standing, "satisfied", because)
            resolved.append(standing.uri)
        return resolved

    def drop(self, action: str, want: str | None, because: str) -> None:
        """The commitment died without being met, and the reason is the record.

        A commitment abandoned without a reason is indistinguishable from one forgotten, which
        is why the argument is not optional.
        """
        for standing in self.standing(action=action, want=want):
            self._resolve(standing, "dropped", because)

    def _resolve(self, standing: Standing, outcome: str, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{standing.uri}> <{kernel("resolvedAt")}> "{now}"^^xsd:dateTime ;
          <{kernel("outcome")}> {_literal(outcome)} ;
          <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("%s: %s", outcome, because)
        self._tell(outcome, standing.action, standing.want, because)

    def _tell(self, kind: str, action: str, want: str, because: str) -> None:
        """One transition into the kernel's event buffer (#125), for the operator's eyes.

        The ledger stays the record; this is a projection — the reporting capability drains it
        into the agent's own bucket on its own tick, so nothing new is granted and an agent
        without that sink simply keeps a bounded buffer nobody empties. Local names, because a
        dashboard tag is for filtering by a person, exactly as the log lines above shorten.
        """
        self.agent.metrics.event(kind, because, means=action.rsplit("#", 1)[-1],
                                 want=_short(want))

    # --- the expectation: the end, judged apart from the means (#131) ---------------------

    def expect(self, intention_uri: str, because: str,
               expected_delta: float | None = None,
               lands_after_s: float | None = None,
               rises: bool | None = None,
               seeing_s: float | None = None,
               baseline=None,
               not_after: datetime | None = None) -> bool:
        """Open the watch: the act happened, now the world owes a movement.

        THE DEADLINE IS THE ACT'S WINDOW. `not_after`, where the actor states it (the act it
        committed to carries one), or else the landing time plus the seeing time computed
        here — and either way it is written as the act's `orexis:notAfter`, so the ledger holds
        one window and every reader reads that one.

        The BASELINE — the reading the actor holds, handed in — is copied into the row: the
        sensed graph keeps only the current witness, so the before of any before/after survives
        nowhere but the ledger. WHICH WAY the value
        should move is the actor's to say: `rises`, or the sign of `expected_delta` — how far
        the act should move the property when the actor can size it (#165), which is what the
        met-verdict measures its margin against. An act that cannot size itself passes `rises`
        alone and keeps the exact-crossing verdict. The keeper used to look the direction up
        from the market's statement on the valuation; that is a package word, and the actor
        that opened the watch already holds it.

        The DEADLINE is the act's landing time (`lands_after_s`, asked of the effect rule by
        the actor, #247) PLUS how long a reading of that property may honestly take to arrive
        (`seeing_s`, the cadence the actor's sensing keeps) — both figures somebody already
        states. An act that cannot size itself gets the patience, unchanged: how long an agent
        waits before re-deciding, not how long the physics takes, and holding a dose to it
        called a valve late at 120s while the pot's own sensor reported every 600.

        The actor also asks its sensing to look once after opening the watch, so the freshest
        before is on record; the keeper no longer names the sensing family to do it.

        False rather than a row when something needed is missing — no reading to baseline on,
        no direction said — and the reason is logged: an expectation that cannot be judged
        would sit unverified forever, which is indistinguishable from the failure it exists to
        catch.
        """
        #  THE BASELINE IS THE ACTOR'S TO HAND IN: the reading it holds, value and instant.
        #  The keeper used to read it off the belief base itself, which meant knowing what a
        #  reading looks like — sensing's knowledge, not the ledger's. Anything with `.value`
        #  and `.result_time` will do; a reading with no instant cannot be a before.
        reading = baseline
        if reading is None or getattr(reading, "result_time", None) is None:
            self.log.warning("cannot expect an end for %s — no baselined reading to leave from",
                             _short(intention_uri))
            return False
        if rises is None and expected_delta:
            rises = expected_delta > 0
        if rises is None:
            self.log.warning("cannot expect an end for %s — the actor said which way it "
                             "should move neither by sign nor by word", _short(intention_uri))
            return False
        expected_delta = abs(expected_delta) if expected_delta else None
        now = datetime.now(timezone.utc)
        window = (lands_after_s + (seeing_s or 0.0) if lands_after_s is not None
                  else float(self.beliefs.patience_s))
        deadline_dt = not_after or datetime.fromtimestamp(now.timestamp() + window,
                                                          tz=timezone.utc)
        window = (deadline_dt - now).total_seconds()
        delta = (f"""
    <{EXPECTS_DELTA}> "{expected_delta}"^^xsd:decimal ;"""
                 if expected_delta else "")
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{intention_uri}>{delta}
    <{EXPECTS_RISE}> {"true" if rises else "false"} ;
    <{BASELINE_VALUE}> "{reading.value}"^^xsd:decimal ;
    <{BASELINE_AT}> "{reading.result_time.isoformat()}"^^xsd:dateTime ;
    <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.window(intention_uri, deadline_dt)
        #  THE WATCH IS A HOLD (#516): the shape of an observation that answers this act,
        #  asked of whoever knows what a reading is (`orexis:answer` — sensing), and the
        #  step held on it as its COMPLETION condition. Conformance is the verdict met; the
        #  deadline passing first is the verdict unmet. The arithmetic that used to judge
        #  every reading here is inside that shape now, its numbers baked at this instant.
        shape = next((g for g in self.agent.ask(
            ANSWER, self.me.acts_for, self._about(intention_uri), reading.result_time,
            float(reading.value), expected_delta, rises, self._met_fraction()) if g is not None), None)
        if shape is None:
            self.log.warning("nothing says what an observation answering %s would look like "
                             "— the watch can only lapse", _short(intention_uri))
        else:
            self._hold_step(intention_uri, kernel("answeredWhen"), shape, deadline_dt, "unmet")
        self.log.info("expecting %s to %s from %.3f within %ss: %s",
                      _short(intention_uri),
                      "rise" if rises else "fall", reading.value, round(window), because)
        return True

    def _about(self, intention_uri: str) -> str | None:
        """What the want this intention pursues is about — the property, for a stake."""
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?want WHERE {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("pursues")}> ?want }} }}"""))
        if not rows:
            return None
        about = bindings(self.agent.desires.query_union(
            "SELECT ?want ?about WHERE { ?want orexis:about ?about }", {"want": rows[0]["want"]}))
        return about[0]["about"] if about else None

    def window(self, intention_uri: str, not_after: datetime) -> None:
        """Set the window's close on the act an intention names — the one figure the bidder's
        give-up, the host's redeem check and the expectation's verdict all read."""
        self.agent.intentions.update(f"""
DELETE {{ GRAPH <{self.graph}> {{ ?act <{kernel("notAfter")}> ?was }} }}
INSERT {{ GRAPH <{self.graph}> {{ ?act <{kernel("notAfter")}> "{not_after.isoformat()}"^^xsd:dateTime }} }}
WHERE  {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("by")}> ?act .
                                  OPTIONAL {{ ?act <{kernel("notAfter")}> ?was }} }} }}""")

    def open_expectations(self, want: str | None = None) -> list[OpenExpectation]:
        """Every watch still on: expectation adopted, end not yet verified — for one want, or
        for all of them."""
        prop = f"FILTER(?want = <{want}>)" if want else ""
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?i ?action ?want ?rises ?baseline ?baselineAt ?deadline ?delta WHERE {{
  GRAPH <{self.graph}> {{
    ?i <{kernel("by")}> ?act ;
       <{kernel("pursues")}> ?want .
    ?act <{kernel("fills")}> ?action ;
         <{kernel("notAfter")}> ?deadline .
    ?i <{EXPECTS_RISE}> ?rises ;
       <{BASELINE_VALUE}> ?baseline ;
       <{BASELINE_AT}> ?baselineAt .
    OPTIONAL {{ ?i <{EXPECTS_DELTA}> ?delta }}
    FILTER NOT EXISTS {{ ?i <{END_MET}> ?met }}
    {prop}
  }} }}"""))
        return [OpenExpectation(
            uri=r["i"], action=r["action"], want=r["want"],
            rises=r["rises"] in ("true", "1"), baseline=float(r["baseline"]),
            baseline_at=datetime.fromisoformat(r["baselineAt"]),
            deadline=datetime.fromisoformat(r["deadline"]),
            expected_delta=float(r["delta"]) if r.get("delta") else None) for r in rows]

    #  `judge(want, value)` WAS HERE — every open watch on a want compared against a number
    #  that arrived, by this class's own arithmetic. An expectation is a hold on the shape of
    #  an answering observation now (#516), and the reading's write is what re-asks it.

    def _verdict(self, watch: OpenExpectation, met: bool, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{watch.uri}> <{END_MET}> "{'true' if met else 'false'}"^^xsd:boolean ;
                <{END_VERIFIED_AT}> "{now}"^^xsd:dateTime ;
                <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        (self.log.info if met else self.log.warning)(
            "end %s for %s: %s", "met" if met else "UNMET", _short(watch.want), because)
        self._tell("end-met" if met else "end-unmet", watch.action, watch.want, because)
        #  SAID UPWARD (#452): the step's result is judged here, against the baseline the actor
        #  handed in and never against a belief; what deliberation does about it — re-plan the
        #  want, mostly — is its own, heard as an event because the ledger imports no search.
        if met:
            self.agent.tell(PLAN_FINISHED, watch.uri, watch.action, watch.want)
        else:
            self.agent.tell(PLAN_FAILED, watch.uri, watch.action, watch.want)
        #  A COMMITMENT THAT STOOD UNTIL THE WORLD ANSWERED is done now, either way. An
        #  Actuate stands from the command to this verdict (#353) — the intention is to the
        #  END, and while it stands `adopt` absorbs the next impulse by the ordinary rule,
        #  which is what the actuator's ledger-reading guard used to do by hand. Satisfied,
        #  not dropped, whatever the verdict: the act was taken, and satisfied-and-unmet is
        #  the false-knowledge signature this ledger exists to record. An Acquire was already
        #  satisfied by its claim and this finds nothing standing.
        for s in self.standing(action=watch.action, want=watch.want):
            if s.uri == watch.uri:
                self._resolve(s, "satisfied",
                              f"the world answered — end {'met' if met else 'unmet'}")
        if not met and self._is_suspect(watch.action, watch.want):
            self.log.warning(
                "AFFORDANCE SUSPECT: %s toward %s has not paid %d times running — the graph "
                "claims a movement the world keeps refusing",
                watch.action.rsplit("#", 1)[-1], _short(watch.want), self._suspect_after())

    def _suspect_after(self) -> int:
        rows = bindings(self.agent.beliefs.query(_SUSPECT_Q))
        return int(rows[0]["n"]) if rows else 3

    def _met_fraction(self) -> float:
        rows = bindings(self.agent.beliefs.query(_MET_FRACTION_Q))
        return float(rows[0]["f"]) if rows else 0.25

    def _is_suspect(self, action: str, want: str) -> bool:
        """The last suspectAfter verdicts for this pair, all unmet, none met among them.

        Consecutive rather than cumulative, so one success resets the count: an affordance
        that mostly pays is noisy, not false.
        """
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?met WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("by")}> ?act ;
     <{kernel("pursues")}> <{want}> ;
     <{END_MET}> ?met .
  ?act <{kernel("fills")}> <{action}> .
  ?i
     <{END_VERIFIED_AT}> ?at .
}} }} ORDER BY DESC(?at) LIMIT {self._suspect_after()}"""))
        n = self._suspect_after()
        return len(rows) >= n and all(r["met"] == "false" for r in rows)

    def suspects(self) -> list[tuple[str, str]]:
        """Every (action, want) pair currently suspect. What review and the report read."""
        pairs = {(r["action"], r["want"]) for r in bindings(self.agent.intentions.query(f"""
SELECT DISTINCT ?action ?want WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("by")}> ?act ;
     <{kernel("pursues")}> ?want ;
     <{END_MET}> ?met .
  ?act <{kernel("fills")}> ?action .
}} }}"""))}
        return sorted(p for p in pairs if self._is_suspect(*p))

    # --- what sensing asks me: the verification watch ----------------------------------

    def watching(self, want: str) -> bool:
        """Is a watch on for this want, its deadline not yet passed?

        The two processes run at different speeds — evaporation is fractions per day, a dose
        lands in seconds — and the one place urgency-by-state gets it wrong is right after
        acting: the value improves, attention would relax, and the dose would land unobserved.
        So an open expectation IS urgency, and sensing folds this into its cadence as the
        maximal answer: it tightens the moment the watch opens and relaxes the moment it
        resolves, bounded by the deadline so a dead sensor cannot hold the fast cadence for
        ever. This was the keeper's answer to the reading choir, keyed by property; the want
        is the key now, and sensing asks per want it holds about the property it is pacing.
        """
        now = datetime.now(timezone.utc)
        return any(now < w.deadline for w in self.open_expectations(want))

    def standing(self, action: str | None = None, want: str | None = None) -> list[Standing]:
        """What stands: adopted and not resolved. The question a deliberator asks first."""
        clauses = [f"?i a <{kernel('Intention')}> ; <{kernel('by')}> ?act ; "
                   f"<{kernel('pursues')}> ?want ; "
                   f"<{kernel('adoptedAt')}> ?at .",
                   f"?act <{kernel('fills')}> ?action .",
                   f"FILTER NOT EXISTS {{ ?i <{kernel('resolvedAt')}> ?done }}"]
        if action:
            clauses.append(f"FILTER(?action = <{action}>)")
        if want:
            clauses.append(f"FILTER(?want = <{want}>)")
        for term in ("through", "quantity", "forAgent", "notBefore", "notAfter"):
            clauses.append(f'OPTIONAL {{ ?act <{kernel(term)}> ?{term} }}')
        rows = bindings(self.agent.intentions.query(
            "SELECT ?i ?act ?action ?want ?at ?through ?quantity ?forAgent ?notBefore ?notAfter "
            "WHERE { GRAPH <%s> { %s } }" % (self.graph, " ".join(clauses))))
        return [Standing(
            uri=r["i"], want=r["want"], adopted_at=datetime.fromisoformat(r["at"]),
            act=Act(action=r["action"], via=r.get("through") or "", want=r["want"],
                    quantity=float(r["quantity"]) if r.get("quantity") else None,
                    for_agent=r.get("forAgent"),
                    not_before=datetime.fromisoformat(r["notBefore"]) if r.get("notBefore") else None,
                    not_after=datetime.fromisoformat(r["notAfter"]) if r.get("notAfter") else None))
            for r in rows]

    @contributes(REPORTS)
    def reports(self) -> dict:
        """How many commitments stand, and how old the oldest is.

        The second number is the one that catches trouble: a standing intention growing old is
        an agent that committed to something the world never answered — a bid whose round
        vanished, a look whose board went quiet — and that is invisible in every other series
        precisely because nothing is happening.
        """
        standing = self.standing()
        out: dict = {"intentions_standing": len(standing)}
        if standing:
            out["oldest_intention_s"] = round(max(s.age_s() for s in standing), 1)
        # The end-verdicts, counted from the ledger. `expectations_unmet` climbing while
        # `satisfied` outcomes accumulate is the false-knowledge signature in series form;
        # `affordances_suspect` above zero is the flag itself.
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?met (COUNT(?i) AS ?n) WHERE {{ GRAPH <{self.graph}> {{
  ?i <{END_MET}> ?met }} }} GROUP BY ?met"""))
        counts = {r["met"]: int(r["n"]) for r in rows}
        out["expectations_open"] = len(self.open_expectations())
        out["expectations_met"] = counts.get("true", 0)
        out["expectations_unmet"] = counts.get("false", 0)
        out["affordances_suspect"] = len(self.suspects())
        return out


def _short(iri: str) -> str:
    """A node's local name, for a log line or a dashboard tag."""
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _literal(text: str) -> str:
    """A prose reason as a safe SPARQL string literal."""
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
