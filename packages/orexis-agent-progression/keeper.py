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
from dataclasses import dataclass, replace as _replace
from datetime import datetime, timedelta, timezone

from assembly.contribute import answer as contribution, contributes
from . import ledger
from .act import Step, method_of, predicts_from_json, predicts_json
from .store import bind, bindings

from .graphs import intentions_graph
from .ontology import ANSWER, OREXIS, PLAN_FAILED, PLAN_FINISHED, REPORTS, WITNESS

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
PREDICTS = OREXIS + "predicts"
PREDICTED_VALUE = OREXIS + "predictedValue"
OBSERVED_VALUE = OREXIS + "observedValue"
BASELINE_VALUE = OREXIS + "baselineValue"
BASELINE_AT = OREXIS + "baselineAt"
#  `orexis:deadlineAt` WAS HERE: the watch's deadline is the ACT's `orexis:notAfter` now — one window,
#  read by the keeper, the bidder's give-up and the host's redeem check alike
#  (an-act-is-a-filled-action-and-a-step-is-its-place-in-a-plan). `ledger` migrates it.
END_MET = OREXIS + "endMet"
END_VERIFIED_AT = OREXIS + "endVerifiedAt"
SUSPECT_AFTER = OREXIS + "suspectAfter"


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
    it pursues. `orexis:by` names the STEP the intention stands at — planned, not done; the
    action, the lever and the quantity are the step's, read through it."""

    uri: str
    step: Step
    want: str               # the desire's node — `orexis:pursues`; the kernel's only key besides the step
    adopted_at: datetime
    advanced_at: datetime | None = None   # when it last moved to a next step (#510), if it did

    @property
    def action(self) -> str:
        return self.step.action

    @property
    def via(self) -> str | None:
        return self.step.via or None

    def age_s(self, now: datetime | None = None) -> float:
        """How long it has stood AT THIS STEP — since adoption, or since the last advance:
        a plan progressing by feedback is not stale for being long (#510)."""
        since = max(self.adopted_at, self.advanced_at) if self.advanced_at else self.adopted_at
        return ((now or datetime.now(timezone.utc)) - since).total_seconds()


@dataclass(frozen=True)
class OpenExpectation:
    """A watch still on: the act happened, and the world has yet to answer as promised."""

    uri: str
    step: str               # the step the watch is on — the intention stands at it
    action: str
    want: str
    deadline: datetime
    baseline: float | None = None        # where the property stood, where the step is about one
    baseline_at: datetime | None = None
    about_world: bool = True             # a step that predicted the world (`orexis:predicts`), not
                                         # one held on its action's doneWhen (#523)


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
        #  A pre-fold volume typed the node `orexis:by` names an Act; it is a STEP — planned,
        #  and the act is the record of its taking (the sovereign's ruling). Retyped, once.
        agent.intentions.update(f"""
INSERT {{ GRAPH <{self.graph}> {{ ?s a <{kernel("Step")}> }} }}
WHERE  {{ GRAPH <{self.graph}> {{ ?i <{kernel("by")}> ?s . FILTER NOT EXISTS {{ ?s a <{kernel("Step")}> }} }} }}""")
        self._deadlines: dict = {}
        self._compiled_conditions: dict = {}
        self._reconsidering = False
        self._claim_lock = threading.Lock()
        self._claimed: set = set()
        self._released: set[str] = set()   # readiness waits released or lapsed, to take once
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
        #  A PLAN, HANDED DOWN WHOLE (#510): `act` may be the plan's steps in order. The head
        #  is what the intention stands at (`orexis:by`); every step is `orexis:step`; each
        #  names the next (`orexis:then`). Absorption is keyed on the head, as it always was.
        steps = list(act) if isinstance(act, (list, tuple)) else None
        if steps is not None:
            act = steps[0]
        if isinstance(act, str):
            act = Step(action=act, via=via or "")
        action = act.action
        now = datetime.now(timezone.utc)
        for standing in self.standing(want=want):
            if standing.action != action and (steps is None or self._next_of(standing.uri) is None):
                continue                  # a different commitment about this want stands apart
            if standing.age_s(now) <= self.beliefs.patience_s:
                if standing.action == action:
                    return None
                continue
            #  A want has one plan at a time (#510): a stale one is superseded whatever its head.
            self._resolve(standing, "dropped",
                          f"outwaited: stood {standing.age_s(now):.0f}s against a patience "
                          f"of {self.beliefs.patience_s}s, superseded by a new adoption")
        stem = uuid.uuid4().hex[:8]
        uri = f"{OREXIS}intent_{self.agent.id}_{stem}"
        xsd = "http://www.w3.org/2001/XMLSchema#"
        plan = self._expanded(steps if steps is not None else [act])
        action = plan[0].action
        step_uris = [f"{OREXIS}step_{self.agent.id}_{stem}" + ("" if n == 0 else f"_{n}")
                     for n in range(len(plan))]
        blocks, parents, written = [], {}, set()
        for n, (step, step_uri) in enumerate(zip(plan, step_uris)):
            facts = [f'<{kernel("fills")}> <{step.action}>']
            if step.via:
                facts.append(f'<{kernel("through")}> <{step.via}>')
            if step.for_agent:
                facts.append(f'<{kernel("forAgent")}> <{step.for_agent}>')
            if step.quantity is not None:
                facts.append(f'<{kernel("quantity")}> "{step.quantity}"^^<{xsd}decimal>')
            if step.not_before:
                facts.append(f'<{kernel("notBefore")}> "{step.not_before.isoformat()}"^^<{xsd}dateTime>')
            if step.not_after:
                facts.append(f'<{kernel("notAfter")}> "{step.not_after.isoformat()}"^^<{xsd}dateTime>')
            if step.urgency_after is not None:
                facts.append(f'<{kernel("predictedUrgency")}> "{step.urgency_after:.6f}"^^<{xsd}decimal>')
            if step.predicts is not None:
                facts.append(f'<{PREDICTS}> {_literal(predicts_json(step.predicts))}')
            if step.about:
                facts.append(f'<{kernel("about")}> <{step.about}>')
            if step.via_by:
                facts.append(f'<{kernel("viaBy")}> {_literal(step.via_by)}')
            if step.about_by:
                facts.append(f'<{kernel("aboutBy")}> {_literal(step.about_by)}')
            if step.part_of is not None:
                parent_uri = parents.setdefault(id(step.part_of), f"{OREXIS}step_{self.agent.id}_{stem}_of{len(parents)}")
                facts.append(f'<{kernel("partOf")}> <{parent_uri}>')
                if id(step.part_of) not in written:
                    written.add(id(step.part_of))
                    p = step.part_of
                    pfacts = [f'<{kernel("fills")}> <{p.action}>']
                    if p.via:
                        pfacts.append(f'<{kernel("through")}> <{p.via}>')
                    if p.about:
                        pfacts.append(f'<{kernel("about")}> <{p.about}>')
                    if p.predicts is not None:
                        pfacts.append(f'<{PREDICTS}> {_literal(predicts_json(p.predicts))}')
                    if p.part_of is not None:
                        grand = parents.setdefault(id(p.part_of), f"{OREXIS}step_{self.agent.id}_{stem}_of{len(parents)}")
                        pfacts.append(f'<{kernel("partOf")}> <{grand}>')
                    blocks.append(f'  <{parent_uri}> a <{kernel("Step")}> ; {" ; ".join(pfacts)} .')
            if n + 1 < len(plan):
                facts.append(f'<{kernel("then")}> <{step_uris[n + 1]}>')
            blocks.append(f'  <{step_uri}> a <{kernel("Step")}> ; {" ; ".join(facts)} .')
        every = " , ".join(f"<{u}>" for u in step_uris)
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> a <{kernel("Intention")}> ;
    <{kernel("pursues")}> <{want}> ;
    <{kernel("by")}> <{step_uris[0]}> ;
    <{kernel("step")}> {every} ;
    <{kernel("adoptedAt")}> "{now.isoformat()}"^^<{xsd}dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
{chr(10).join(blocks)}
}} }}""")
        self._bind_parameters(uri)
        self.log.info("adopted %s for %s: %s", action.rsplit("#", 1)[-1], _short(want), because)
        self._tell("adopted", action, want, because)
        if until is not None or until_not is not None:
            self.hold(uri, until=until, until_not=until_not, not_after=not_after,
                      when_lapsed=when_lapsed)
        return uri

    # --- an intention held until a condition (#512, #514) --------------------------------

    def _expanded(self, plan: list) -> list:
        """The plan with every step of an action that declares a METHOD (#523) replaced by
        the method's members in order — recursively, a member with a method of its own
        expanding in turn — the last member inheriting the parent's prediction and predicted
        urgency, since the end the search planned on is reached when the method is done. A
        member is a step of the parent's lever and subject unless it carries templates of its
        own (`via_by`, `about_by`), which are bound when the step becomes current. The parent
        is kept on each member (`part_of`) and written to the ledger as the filling they came
        from."""
        out = []
        for step in plan:
            out.extend(self._members_of(step, depth=0))
        return out

    def _members_of(self, step, depth: int) -> list:
        members = self._method_of(step.action)
        if not members or depth > 8:
            return [step]
        out = []
        for n, member in enumerate(members):
            last = n == len(members) - 1
            child = _replace(step, action=member["action"],
                             via_by=member["via_by"], about_by=member["about_by"],
                             predicts=step.predicts if last else None,
                             urgency_after=step.urgency_after if last else None,
                             part_of=step)
            out.extend(self._members_of(child, depth + 1))
        return out

    def _method_of(self, action: str) -> list[dict]:
        return method_of(self.agent.beliefs.query, action)

    def _template_of(self, action: str, term: str) -> str | None:
        rows = bindings(self.agent.beliefs.query(f"SELECT ?t WHERE {{ <{action}> <{kernel(term)}> ?t }}"))
        return rows[0]["t"] if rows else None

    def _tokens(self, intention_uri: str, step) -> dict:
        """What a wait template may say instead of an instance: the rule's own tokens."""
        from .ontology import beliefs_graph
        from .store import Raw
        adopted = next((s.adopted_at for s in self.standing() if s.uri == intention_uri), None)
        since = (adopted or datetime.now(timezone.utc)).isoformat()
        return {"me": self.me.uri, "via": step.via or "urn:nothing",
                "about": self._about(intention_uri) or "urn:nothing",
                "subject": self.me.acts_for or "urn:nobody", "want": step.want or "urn:nothing",
                "beliefs": beliefs_graph(self.agent.id),
                "since": Raw(f'"{since}"^^xsd:dateTime')}      # when this intention was adopted

    def _bind_parameters(self, intention_uri: str) -> None:
        """LATE BINDING (#523): a method member that fills its lever or its subject by a
        template does so when it becomes current, against the world as it then is — the
        third move's disk is where the first two left it — with the parent step's lever and
        subject as `$via` and `$about`. Written onto the ledger step as `orexis:through` and
        `orexis:about`, where every later reader finds them."""
        from .ontology import beliefs_graph, STATE_GRAPH
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?step ?viaBy ?aboutBy ?pvia ?pabout WHERE {{ GRAPH <{self.graph}> {{
  <{intention_uri}> <{kernel("by")}> ?step .
  OPTIONAL {{ ?step <{kernel("viaBy")}> ?viaBy }}
  OPTIONAL {{ ?step <{kernel("aboutBy")}> ?aboutBy }}
  OPTIONAL {{ ?step <{kernel("partOf")}> ?parent .
             OPTIONAL {{ ?parent <{kernel("through")}> ?pvia }}
             OPTIONAL {{ ?parent <{kernel("about")}> ?pabout }} }} }} }}"""))
        if not rows or not (rows[0].get("viaBy") or rows[0].get("aboutBy")):
            return
        r = rows[0]
        tokens = {"me": self.me.uri, "subject": self.me.acts_for or "urn:nobody",
                  "via": r.get("pvia") or "urn:nothing", "about": r.get("pabout") or "urn:nothing",
                  "beliefs": beliefs_graph(self.agent.id), "state": STATE_GRAPH}
        for term, text, var in (("through", r.get("viaBy"), "via"), ("about", r.get("aboutBy"), "about")):
            if not text:
                continue
            try:
                answer = bindings(self.agent.beliefs.query_over(
                    bind(text, **tokens), *self.agent.beliefs.public_graphs(),
                    *self.agent.beliefs.recorded_graphs()))
            except Exception as exc:                                # noqa: BLE001
                self.log.error("a step's %s template will not run: %s", term, exc)
                continue
            if not answer or not answer[0].get(var):
                self.log.warning("a step's %s template bound nothing — the step keeps the parent's", term)
                continue
            self.agent.intentions.update(f"""
DELETE {{ GRAPH <{self.graph}> {{ <{r["step"]}> <{kernel(term)}> ?was }} }}
INSERT {{ GRAPH <{self.graph}> {{ <{r["step"]}> <{kernel(term)}> <{answer[0][var]}> }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{self.graph}> {{ <{r["step"]}> <{kernel(term)}> ?was }} }} }}""")

    def _lapses_at(self, action: str, tokens: dict) -> datetime | None:
        """When a wait on a step of this action is over, asked of the action's own
        `orexis:lapsesAt` — a dateTime, or seconds from now; None is the patience."""
        text = self._template_of(action, "lapsesAt")
        if not text:
            return None
        try:
            rows = bindings(self.agent.beliefs.query_over(
                bind(text, **tokens), *self.agent.beliefs.public_graphs(),
                *self.agent.beliefs.recorded_graphs()))
        except Exception as exc:                                    # noqa: BLE001
            self.log.error("%s's lapsesAt will not run: %s", action.rsplit("#", 1)[-1], exc)
            return None
        if not rows:
            return None
        if rows[0].get("at"):
            return datetime.fromisoformat(rows[0]["at"])
        if rows[0].get("seconds"):
            return datetime.now(timezone.utc) + timedelta(seconds=float(rows[0]["seconds"]))
        return None

    def _holds_now(self, shape) -> bool:
        import rdflib
        from . import violation
        root = next(s for s in shape.subjects(rdflib.RDF.type, _SH_NODE_SHAPE)
                    if isinstance(s, rdflib.URIRef))
        select = violation.entered_select(shape, root)
        return bool(bindings(self.agent.beliefs.query_over(
            select, *self.agent.beliefs.public_graphs(), *self.agent.beliefs.recorded_graphs())))

    def ready(self, intention_uri: str) -> bool:
        """May the step this intention stands at be taken now? True where its action states no
        `orexis:readyWhen`, or states one that holds; otherwise the step is HELD on it
        (`orexis:until`, taken when it lapses) and this answers False — `carry_out`'s question
        before it asks any actor (#523), and the same question after a release, when the
        condition holds and the answer is yes."""
        if intention_uri in self._released:
            self._released.discard(intention_uri)
            return True
        standing = next((s for s in self.standing() if s.uri == intention_uri), None)
        if standing is None:
            return True
        text = self._template_of(standing.action, "readyWhen")
        if not text:
            return True
        tokens = self._tokens(intention_uri, standing.step)
        shape = condition_shape(f"urn:orexis:ready:{uuid.uuid4().hex[:8]}", self.me.uri,
                                bind(text, **tokens))
        if self._holds_now(shape):
            return True
        if any(h.uri == intention_uri for h, _, _ in self.held()):
            return False                          # already waiting on it
        deadline = self._lapses_at(standing.action, tokens) or datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + float(self.beliefs.patience_s), tz=timezone.utc)
        self.log.info("holding %s until its action's condition holds (by %s)",
                      standing.action.rsplit("#", 1)[-1], deadline.isoformat(timespec="seconds"))
        self.hold(intention_uri, until=shape, not_after=deadline, when_lapsed="take")
        return False

    def after_take(self, intention_uri: str) -> None:
        """The step was taken: where its action states `orexis:doneWhen`, hold the step on it
        as its completion (`orexis:answeredWhen`) — met advances the plan, lapsing is an unmet
        verdict that drops the tail (#523)."""
        standing = next((s for s in self.standing() if s.uri == intention_uri), None)
        if standing is None:
            return
        text = self._template_of(standing.action, "doneWhen")
        if not text:
            return
        tokens = self._tokens(intention_uri, standing.step)
        shape = condition_shape(f"urn:orexis:done:{uuid.uuid4().hex[:8]}", self.me.uri,
                                bind(text, **tokens))
        deadline = self._lapses_at(standing.action, tokens) or datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + float(self.beliefs.patience_s), tz=timezone.utc)
        self.window(intention_uri, deadline)
        self.log.info("expecting %s to be done by %s: its action's condition",
                      standing.action.rsplit("#", 1)[-1], deadline.isoformat(timespec="seconds"))
        self._hold_step(intention_uri, kernel("answeredWhen"), shape, deadline, "unmet")

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
        ON THE STEP the intention stands at, so a sovereign asking sees what a step waits for.
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
        """Write a condition on the step the intention stands at, arm its deadline, and ask
        at once whether it already answers. ON THE STEP: a planned thing is what waits; the
        act is the record of its taking, written when that happens."""
        node, triples = self._condition_triples(intention_uri, condition)
        #  A NEW HOLD ON AN INTENTION ALREADY CLAIMED ONCE — the next step of a plan (#510) —
        #  is a new wait: the claim that ended the previous one is released here, or the
        #  second wait could never end.
        with self._claim_lock:
            self._claimed.discard(intention_uri)
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
        """Every step still waiting: `(holder, select, predicate)` — the select the store
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
  FILTER NOT EXISTS {{ ?act <{END_MET}> ?m }} }} }}"""))
        standing = {s.uri: s for s in self.standing()}
        watches = {w.uri: w for w in self.open_expectations(every=True)}
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
                            else holder.step.not_after)
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
            self._verdict(holder, True, "answered as the step predicted: the world conforms "
                                        "to the shape generated from its prediction")
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
                return
        #  NOT HELD: a plan standing at a step nobody took (#510) — its patience is its
        #  deadline, and passing it drops the tail and says so upward, so deliberation
        #  decides afresh from the world as it is.
        for standing in self.standing():
            if standing.uri == intention_uri:
                self._resolve(standing, "dropped", "the step it stood at was not taken before "
                                                   "its patience ran out — the tail is dropped")
                self.agent.tell(PLAN_FAILED, standing.uri, standing.action, standing.want)

    def _when_lapsed(self, intention_uri: str) -> str:
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?when WHERE {{ GRAPH <{self.graph}> {{
  <{intention_uri}> <{kernel("by")}> ?act . ?act <{kernel("whenLapsed")}> ?when }} }}"""))
        return rows[0]["when"] if rows else "take"

    def _release(self, standing: Standing, because: str) -> None:
        from .execution import carry_out
        #  RELEASED IS TAKEN: a readiness wait that lapsed is taken anyway (a held claim
        #  redeems blind rather than never), so `ready` is not asked again on this road.
        self._released.add(standing.uri)

        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{ <{standing.uri}> <{BECAUSE_OF}> {_literal(because)} . }} }}""")
        self.log.info("releasing %s: %s", standing.action.rsplit("#", 1)[-1], because)
        carry_out(self.agent, standing.step, None, standing.uri)

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
               baseline=None,
               tolerance: float | None = None,
               lands_after_s: float | None = None,
               seeing_s: float | None = None,
               not_after: datetime | None = None,
               predicts: tuple | None = None) -> bool:
        """Open the watch: the step was taken, now the world owes the change it predicted.

        ONE DECLARATION (#510, #518). What the world is held to is `orexis:predicts` on the
        step the intention stands at — the facts the search said this step makes true and
        false, the same facts its signature is made of — and nothing the actor sizes: the
        actor that used to say a delta and a direction now says only how CLOSE the world must
        land, `tolerance`, a fraction of the predicted movement, which is its own revisable
        pick. A caller may hand `predicts` in for a step the search did not make.

        The answering shape is generated here (`_answering_shape`): a KEYED fact — an
        observation, some package's `orexis:keyedBy` class — is put to that package through
        the `orexis:answer` extension, since what a reading is is sensing's; a PLAIN fact is
        the kernel's own, present for an addition and gone for a retraction, as one query
        under a shape. The keeper holds the step on the shape as `orexis:answeredWhen` and
        the verdict is its conformance before the deadline.

        THE DEADLINE IS THE STEP'S WINDOW. `not_after` where the actor states it, or the
        landing time plus the seeing time (#247) — an act that cannot say gets the patience:
        how long an agent waits before re-deciding, not how long the physics takes.

        The BASELINE — the reading the actor holds, where the step is about a property —
        is copied onto the step: the sensed graph keeps only the current witness, so the
        before of any before/after survives nowhere but the ledger. Since a plain fact has
        no baseline, it is optional, and `since` is then the moment of taking.

        False rather than a row when the step predicts nothing, or nothing can say what
        would answer it — an expectation that cannot be judged would sit unverified
        forever, which is indistinguishable from the failure it exists to catch.
        """
        step, persisted = self._step_of(intention_uri)
        if step is None:
            self.log.warning("cannot expect an end for %s — it stands at no step",
                             _short(intention_uri))
            return False
        predicts = predicts if predicts is not None else persisted
        if not predicts or not (predicts[0] or predicts[1]):
            self.log.warning("cannot expect an end for %s — the step predicts nothing, so "
                             "there is nothing to hold the world to", _short(intention_uri))
            return False
        now = datetime.now(timezone.utc)
        window = (lands_after_s + (seeing_s or 0.0) if lands_after_s is not None
                  else float(self.beliefs.patience_s))
        deadline_dt = not_after or datetime.fromtimestamp(now.timestamp() + window,
                                                          tz=timezone.utc)
        window = (deadline_dt - now).total_seconds()
        since = getattr(baseline, "result_time", None) or now
        value = float(baseline.value) if baseline is not None else None
        based = (f"""
  <{step}> <{BASELINE_VALUE}> "{value}"^^xsd:decimal ;
           <{BASELINE_AT}> "{since.isoformat()}"^^xsd:dateTime ."""
                 if value is not None else "")
        #  A prediction handed in for a step the search did not make is the step's from here
        #  on: the ledger, not the caller, is what the verdict and the reviewer read.
        stated = (f"""
  <{step}> <{PREDICTS}> {_literal(predicts_json(predicts))} .""" if persisted is None else "")
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{{based}{stated}
  <{intention_uri}> <{BECAUSE_OF}> {_literal(because)} . }} }}""")
        self.window(intention_uri, deadline_dt)
        shape = self._answering_shape(predicts, since, value, tolerance)
        if shape is None:
            self.log.warning("nothing says what a world answering %s would look like "
                             "— the watch can only lapse", _short(intention_uri))
        else:
            self._hold_step(intention_uri, kernel("answeredWhen"), shape, deadline_dt, "unmet")
        self.log.info("expecting %s to answer within %ss (%d predicted, %d retracted%s): %s",
                      _short(intention_uri), round(window), len(predicts[0]), len(predicts[1]),
                      f", from {value:.3f}" if value is not None else "", because)
        return True

    def _residual_of(self, step_uri: str) -> tuple[float | None, float | None]:
        """The one number a step predicted, and what the world shows for it now — None, None
        where the prediction carries no number or more than one (a plain-fact step, a step
        predicting two readings), or where nobody will witness it."""
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?predicts WHERE {{ GRAPH <{self.graph}> {{ <{step_uri}> <{PREDICTS}> ?predicts }} }}"""))
        if not rows:
            return None, None
        adds, _ = predicts_from_json(rows[0]["predicts"])
        numbers = [f for f in adds if f and f[0] == "keyed"
                   and isinstance(f[4], (int, float)) and not isinstance(f[4], bool)]
        if len(numbers) != 1:
            return None, None
        _, cls, key, _, predicted = numbers[0]
        observed = next((v for v in self.agent.ask(WITNESS, cls, dict(key)) if v is not None), None)
        return float(predicted), (float(observed) if observed is not None else None)

    def _step_of(self, intention_uri: str) -> tuple[str | None, tuple | None]:
        """The step an intention stands at, and what it predicts — None where it predicts
        nothing (a step an event adopted, a look)."""
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?step ?predicts WHERE {{ GRAPH <{self.graph}> {{
  <{intention_uri}> <{kernel("by")}> ?step .
  OPTIONAL {{ ?step <{PREDICTS}> ?predicts }} }} }}"""))
        if not rows:
            return None, None
        text = rows[0].get("predicts")
        return rows[0]["step"], (predicts_from_json(text) if text else None)

    def _answering_shape(self, predicts: tuple, since, baseline: float | None,
                         tolerance: float | None):
        """The shape a world answering this prediction conforms to, from the step's facts.

        A KEYED fact (`("keyed", class, key, predicate, value)` — a node some package
        declared `orexis:keyedBy`, an observation) is the package's to answer for: the
        `orexis:answer` extension is asked with the class, its key and what it carries, and
        the first opinion wins. A PLAIN fact `(s, p, o)` is the kernel's: every addition
        present and every retraction gone, as one query under a shape (`condition_shape`),
        so the ledger reads as the step meant it. A fact that cannot be stated as a triple
        — a blank node the search labelled by content — is passed over and said so.

        None where the step predicts nothing statable, or where a keyed fact finds no
        answerer, or where the prediction spans more than one shape can hold (a step that
        predicts both a reading and a world fact — no shipped action does; a seam).
        """
        adds, retracts = predicts
        keyed: dict = {}
        present, gone, anchors, passed = [], [], [], 0
        for fact in adds:
            if fact and fact[0] == "keyed":
                _, cls, key, p, v = fact
                keyed.setdefault((cls, key), {})[p] = v
            elif (t := _plain_pattern(fact)) is not None:
                present.append(t)
                anchors.append(fact[0])
            else:
                passed += 1
        for fact in retracts:
            if fact and fact[0] == "keyed":
                continue           # the old reading: superseded by the new one, not "gone"
            if (t := _plain_pattern(fact)) is not None:
                gone.append(t)
                anchors.append(fact[0])
            else:
                passed += 1
        if passed:
            self.log.warning("%d predicted fact(s) cannot be stated as triples — the world is "
                             "not held to them", passed)
        shapes = []
        for (cls, key), carried in keyed.items():
            g = next((g for g in self.agent.ask(ANSWER, cls, dict(key), carried, since,
                                                baseline, tolerance) if g is not None), None)
            if g is None:
                self.log.warning("nothing says what answers a predicted %s", cls.rsplit("#", 1)[-1])
                return None
            shapes.append(g)
        if present or gone:
            anchor = anchors[0]                 # the shape's focus: the first fact's subject
            body = "\n  ".join(f"{s} {p} {o} ." for s, p, o in present)
            body += "".join(f"\n  FILTER NOT EXISTS {{ {s} {p} {o} }}" for s, p, o in gone)
            shapes.append(condition_shape(f"urn:orexis:answer:{uuid.uuid4().hex[:8]}", anchor,
                                          f"SELECT $this WHERE {{\n  {body}\n}}"))
        if len(shapes) != 1:
            if shapes:
                self.log.warning("a step predicting %d kinds of change is held to none — one "
                                 "shape holds one kind", len(shapes))
            return None
        return shapes[0]

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

    def open_expectations(self, want: str | None = None, *, every: bool = False) -> list[OpenExpectation]:
        """Every watch still on: expectation adopted, end not yet verified — for one want, or
        for all of them. A watch on the WORLD — a step that predicted a reading, baselined —
        is what callers mean by "my dose has not answered": a step held on its action's
        `orexis:doneWhen` (#523) is the same wait inside the keeper and not that, so it is
        left out unless `every` is asked."""
        prop = f"FILTER(?want = <{want}>)" if want else ""
        world = "" if every else "FILTER(BOUND(?predicts))"
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?i ?step ?action ?want ?baseline ?baselineAt ?deadline ?predicts WHERE {{
  GRAPH <{self.graph}> {{
    ?i <{kernel("by")}> ?step ;
       <{kernel("pursues")}> ?want .
    ?step <{kernel("fills")}> ?action ;
          <{kernel("notAfter")}> ?deadline ;
          <{kernel("answeredWhen")}> ?shape .
    OPTIONAL {{ ?step <{PREDICTS}> ?predicts }}
    OPTIONAL {{ ?step <{BASELINE_VALUE}> ?baseline ; <{BASELINE_AT}> ?baselineAt }}
    FILTER NOT EXISTS {{ ?step <{END_MET}> ?met }}
    {world}
    {prop}
  }} }}"""))
        return [OpenExpectation(
            uri=r["i"], step=r["step"], action=r["action"], want=r["want"],
            deadline=datetime.fromisoformat(r["deadline"]),
            baseline=float(r["baseline"]) if r.get("baseline") else None,
            baseline_at=datetime.fromisoformat(r["baselineAt"]) if r.get("baselineAt") else None,
            about_world=bool(r.get("predicts")))
            for r in rows]

    #  `judge(want, value)` WAS HERE — every open watch on a want compared against a number
    #  that arrived, by this class's own arithmetic. An expectation is a hold on the shape of
    #  an answering observation now (#516), and the reading's write is what re-asks it.

    def _verdict(self, watch: OpenExpectation, met: bool, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        #  THE RESIDUAL (#518): what the step said the world would show, and what it shows at
        #  the verdict — met or unmet alike — written on the step for the reviewer, since the
        #  sensed graph keeps only the current witness and the ledger is what remembers.
        predicted, observed = self._residual_of(watch.step)
        residual = "".join(f'\n  <{watch.step}> <{p}> "{v}"^^xsd:decimal .'
                           for p, v in ((PREDICTED_VALUE, predicted), (OBSERVED_VALUE, observed))
                           if v is not None)
        self.agent.intentions.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{watch.step}> <{END_MET}> "{'true' if met else 'false'}"^^xsd:boolean ;
                 <{END_VERIFIED_AT}> "{now}"^^xsd:dateTime .
  <{watch.uri}> <{BECAUSE_OF}> {_literal(because)} .{residual}
}} }}""")
        #  A WATCH ON THE WORLD — a step that predicted something of it — is an end the
        #  graph promised, and its verdict is what the reports count and the suspicion reads.
        #  A step held on its action's `orexis:doneWhen` (#523) is the same wait inside the
        #  keeper and a different thing outside: a bid answered by a claim, or not. It
        #  advances or drops the plan, and says so in its own words.
        world = watch.about_world
        if world:
            (self.log.info if met else self.log.warning)(
                "end %s for %s: %s", "met" if met else "UNMET", _short(watch.want), because)
            self._tell("end-met" if met else "end-unmet", watch.action, watch.want, because)
        else:
            (self.log.info if met else self.log.warning)(
                "%s %s for %s: %s", watch.action.rsplit("#", 1)[-1], "done" if met else "LAPSED",
                _short(watch.want), because)
            self._tell("done" if met else "lapsed", watch.action, watch.want, because)
        if met and self._advance(watch):
            #  THE PLAN GOES ON (#510): this step's prediction was confirmed by the world,
            #  which is the only license the next step has — no search, no re-decision. The
            #  intention stands; the plan is finished only when its last step is answered.
            return
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
        if world and not met and self._is_suspect(watch.action, watch.want):
            self.log.warning(
                "AFFORDANCE SUSPECT: %s toward %s has not paid %d times running — the graph "
                "claims a movement the world keeps refusing",
                watch.action.rsplit("#", 1)[-1], _short(watch.want), self._suspect_after())

    def _advance(self, watch: OpenExpectation) -> bool:
        """Move the intention to the step that follows the one just answered, and take it.
        False where there is none — the plan's last step, finished the ordinary way."""
        from .execution import carry_out

        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?next WHERE {{ GRAPH <{self.graph}> {{ <{watch.step}> <{kernel("then")}> ?next }} }}"""))
        if not rows:
            return False
        following = rows[0]["next"]
        self.agent.intentions.update(f"""
DELETE {{ GRAPH <{self.graph}> {{ <{watch.uri}> <{kernel("by")}> ?was }} }}
INSERT {{ GRAPH <{self.graph}> {{ <{watch.uri}> <{kernel("by")}> <{following}> ;
                                <{BECAUSE_OF}> {_literal("step answered as predicted — advancing to the next")} }} }}
WHERE  {{ GRAPH <{self.graph}> {{ <{watch.uri}> <{kernel("by")}> ?was }} }}""")
        self._bind_parameters(watch.uri)
        standing = next((s for s in self.standing(want=watch.want) if s.uri == watch.uri), None)
        if standing is None:
            return False
        self.log.info("advanced %s to %s", _short(watch.uri), standing.action.rsplit("#", 1)[-1])
        self._tell("advanced", standing.action, watch.want, "the previous step was answered")
        desire = next((d for d in self.agent.pursuing() if d.uri == watch.want), None)
        carry_out(self.agent, standing.step, desire, watch.uri)
        return True

    def current(self, intention_uri: str):
        """The step this intention stands at, as the ledger has it — what there is to take."""
        return next((s.step for s in self.standing() if s.uri == intention_uri), None)

    def in_progress(self, want: str):
        """A standing intention for this want whose plan has a step still to come, and
        which is younger than my patience — the case pursuit does not search over (#510):
        the plan goes on by feedback, and a search would re-decide what the world has not
        yet contradicted. None otherwise."""
        now = datetime.now(timezone.utc)
        held = {h.uri for h, _, _ in self.held()} if self._holding else set()
        for standing in self.standing(want=want):
            #  Stale at this step and not waiting on anything: a step nobody could take,
            #  standing past the patience, is not progress — pursuit decides afresh and
            #  `adopt` supersedes it. A held step has a deadline of its own.
            if standing.uri not in held and standing.age_s(now) > self.beliefs.patience_s:
                continue
            if self._next_of(standing.uri) is not None:
                return standing
        return None

    def _next_of(self, intention_uri: str) -> str | None:
        rows = bindings(self.agent.intentions.query_union(f"""
SELECT ?next WHERE {{ GRAPH <{self.graph}> {{ <{intention_uri}> <{kernel("by")}> ?s . ?s <{kernel("then")}> ?next }} }}"""))
        return rows[0]["next"] if rows else None

    def _suspect_after(self) -> int:
        rows = bindings(self.agent.beliefs.query(_SUSPECT_Q))
        return int(rows[0]["n"]) if rows else 3

    def _is_suspect(self, action: str, want: str) -> bool:
        """The last suspectAfter verdicts for this pair, all unmet, none met among them.

        Consecutive rather than cumulative, so one success resets the count: an affordance
        that mostly pays is noisy, not false.
        """
        rows = bindings(self.agent.intentions.query(f"""
SELECT ?met WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("step")}> ?act ;
     <{kernel("pursues")}> <{want}> .
  ?act <{kernel("fills")}> <{action}> ;
       <{END_MET}> ?met ;
       <{END_VERIFIED_AT}> ?at .
}} }} ORDER BY DESC(?at) LIMIT {self._suspect_after()}"""))
        n = self._suspect_after()
        return len(rows) >= n and all(r["met"] == "false" for r in rows)

    def suspects(self) -> list[tuple[str, str]]:
        """Every (action, want) pair currently suspect. What review and the report read."""
        pairs = {(r["action"], r["want"]) for r in bindings(self.agent.intentions.query(f"""
SELECT DISTINCT ?action ?want WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("step")}> ?act ;
     <{kernel("pursues")}> ?want .
  ?act <{kernel("fills")}> ?action ;
       <{END_MET}> ?met .
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
        for term in ("through", "quantity", "forAgent", "notBefore", "notAfter", "predicts",
                     "about", "viaBy", "aboutBy", "partOf"):
            clauses.append(f'OPTIONAL {{ ?act <{kernel(term)}> ?{term} }}')
        clauses.append(f'OPTIONAL {{ SELECT ?i (MAX(?v) AS ?advanced) WHERE {{ '
                       f'?i <{kernel("step")}> ?done . ?done <{END_VERIFIED_AT}> ?v }} GROUP BY ?i }}')
        rows = bindings(self.agent.intentions.query(
            "SELECT ?i ?act ?action ?want ?at ?through ?quantity ?forAgent ?notBefore ?notAfter "
            "?predicts ?about ?viaBy ?aboutBy ?partOf ?advanced WHERE { GRAPH <%s> { %s } }"
            % (self.graph, " ".join(clauses))))
        #  WHAT THE WANT IS ABOUT rides along (#510): a step taken from the ledger — the
        #  second of a plan, advanced to on feedback — goes to its actor exactly as the head
        #  did from the search, and the actor reads the property off the step, not the want.
        about_of = {w["want"]: w["about"] for w in bindings(self.agent.desires.query_union(
            "SELECT ?want ?about WHERE { ?want orexis:about ?about }"))} if rows else {}
        return [Standing(
            uri=r["i"], want=r["want"], adopted_at=datetime.fromisoformat(r["at"]),
            advanced_at=datetime.fromisoformat(r["advanced"]) if r.get("advanced") else None,
            step=Step(action=r["action"], via=r.get("through") or "", want=r["want"],
                    about=r.get("about") or about_of.get(r["want"]),
                    via_by=r.get("viaBy"), about_by=r.get("aboutBy"), part_of=r.get("partOf"),
                    predicts=predicts_from_json(r["predicts"]) if r.get("predicts") else None,
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
SELECT ?met (COUNT(?s) AS ?n) WHERE {{ GRAPH <{self.graph}> {{
  ?i <{kernel("step")}> ?s . ?s <{END_MET}> ?met ; <{PREDICTS}> ?world }} }} GROUP BY ?met"""))
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


def _plain_pattern(fact) -> tuple[str, str, str] | None:
    """A canonical plain fact as three SPARQL terms — None where one of them is a label the
    search gave a blank node, which no query can name. An IRI is told from a string by its
    scheme; a number is written bare so the store compares it as one."""
    import re
    if len(fact) != 3 or not all(isinstance(x, (str, int, float)) for x in fact):
        return None
    out = []
    for x in fact:
        if isinstance(x, bool):
            out.append("true" if x else "false")
        elif isinstance(x, (int, float)):
            out.append(repr(float(x)))
        elif re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s<>\"{}|^`\\]+$", x):
            out.append(f"<{x}>")
        else:
            out.append(_literal(x))
    return tuple(out)
