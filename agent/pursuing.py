"""Everything this agent is pursuing right now, as a collection.

**THE ONE COLLECTION THAT IS MADE RATHER THAN HELD, and the exception is stated because the
convention asks for it.** Every other read here reads rows somebody wrote: `find_wants` and
`Desires` hand back what is in a graph. Nothing ever writes these. This one ASSEMBLES — it
asks every module what it is pursuing and how badly, runs an avoided state's own select to
see whether the world has entered it, compiles a shape into the select whose rows are its
violations, and hands back what comes back — in no order, since nothing chose by one.

That makes it a repository by its name and a service by its work, which is a line this repo
usually holds (`a-repository-is-not-a-service`). It is kept on the collection side for the
reason `Steps` is: what it hands back is a collection of domain objects, derived on every ask
and never stored, and a caller asking "what am I pursuing" is asking for the contents rather
than for a decision.

**It is handed the AGENT, and unlike `find_wants` that is not a failure to narrow.** What a
want reads as here is CONTRIBUTED — the ledger reads a debt against its redeem window, sensing
reads a stake against the survival envelope — so the collection has to reach the choir, and
the choir is the agent. A read over stored rows needs a store; a read over contributed answers
needs the contributors. That asymmetry is the clearest statement of what
the two kinds of collection are.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from rdflib import URIRef

from orexis_agent_deliberation.want import Want
from orexis_agent_deliberation.wants import find_wants
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import DESIRES
from orexis_agent_progression.store import bind, bindings
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import FORESEEN, KNOWN

log = logging.getLogger("pursuing")

#  The avoided-pattern wants the kernel lifts into pursuit itself (#468) — see `pursuing`.
#  The select is OPTIONAL here because the node a want points at may be the DOMAIN's — declared
#  in a package's ontology, public knowledge the desire modality does not keep after its
#  rebuild — and is then read from the belief base, whose default graph merges public knowledge.
#  `?me`, `?node` are BOUND BY SUBSTITUTION (#500) — the engine's own parameters, projected
#  so the engine can reach them — never spliced into the text.
_AVOIDED_Q = """
SELECT ?me ?want ?avoided ?select WHERE {
  ?me orexis:holds ?want .
  ?want orexis:unmetWhen ?avoided .
  OPTIONAL { ?avoided sh:select ?select }
}"""
_SELECT_Q = "SELECT ?node ?select WHERE { ?node sh:select ?select } LIMIT 1"
_IS_SHAPE_Q = "SELECT ?node WHERE { ?node a sh:NodeShape } LIMIT 1"
#  And the SHAPE-authored wants nobody speaks for (#497): a world may assert a positive want
#  whose met-test is a shape the domain package declares; the kernel compiles it and judges.
_SHAPED_Q = """
SELECT ?me ?want ?shape WHERE {
  ?me orexis:holds ?want .
  ?want orexis:metWhen ?shape .
}"""


class Pursuing:
    """Everything this agent is pursuing, hottest first."""

    def __init__(self, agent):
        self._agent = agent

    def find_all(self, now: datetime | None = None) -> list[Want]:
        """Everything this agent is pursuing, hottest first, whoever sourced it.

        Assembled from the modules that hold wants rather than asked of one, because since the
        ledger became its own capability no single module can see them all: desire contributes
        stakes, owing contributes debts, and an agent may compose either without the other. The
        ranking is what would make the two comparable — and nothing ranks them, so a
        litre owed and a pot drying finally rank against each other.
        """
        #  ONE WANT, ONE NODE. Two modules may hold the same want — the gardener composes two
        #  sensing modules and each reads every region the agent holds — and a want is its
        #  node, so the second sighting is the same want and not a second one.
        seen: dict[str, Want] = {}
        #  A ROOT IS PRESENTED AS THE WANT DERIVED UNDER IT (#618), where one stands: the
        #  root's own row — its measure, its reading, its property — under the derived want's
        #  name, naming the root beside it. The derived want is never lifted on its own.
        #  ASKED OF THE MODULE THAT READS THEM (#618): the want derived under each root, and
        #  the instant it must hold at. This was a select here, keyed on the agent and on the
        #  parent being a desire — every column of which is a field of `Want`. `derived=True`
        #  is the family the derivation mints into, said here rather than spelled into a
        #  finder's name: what is wanted is the derivation's children, not a debt or a promise.
        children: dict = {}
        for w in find_wants(self._agent.beliefs, now, derived=True):
            children.setdefault(w.desire, []).append(w)
        derived = {w.uri for ws in children.values() for w in ws}
        #  A CAPABILITY MAY SPEAK FOR A DERIVED WANT — the ledger reads the want under
        #  "no overdue debts" against its claim's redeem window, and names the claim — and its
        #  word wins over the root's copy below, keeping the derivation's provenance.
        spoken_for: dict = {}
        for wants in self._agent.ask(DESIRES, now):
            for want in wants:
                if want.uri in derived:
                    spoken_for.setdefault(want.uri, want)
                else:
                    seen.setdefault(want.uri, want)
        #  THE WANTS NO MODULE SPEAKS FOR (#468): a world may ratify a desire DIRECTLY — the
        #  asserted block — and wanting is the kernel's, so the kernel is who lifts such a
        #  want into pursuit rather than a capability minted to re-say it. Scoped to the
        #  avoided-pattern wants, whose judging is one select on the store's own engine;
        #  binary, because between entered and held there is nothing to be nearer to. A
        #  pattern that fails to run reads as unmet — the loud direction.
        for row in bindings(self._agent.desires.query(_AVOIDED_Q, {"me": self._agent.me.uri})):
            if row["want"] in seen or row["want"] in derived:
                continue
            #  THE DESIRE OWNS THE TERM AND THE PACKAGE OWNS THE MEASURE: a world may write
            #  the pattern inline beside its asserted want, or point at a node the domain
            #  package declares. The first rides in the modality; the second is public
            #  knowledge and is asked of the belief base — one text, both paths.
            select = row.get("select")
            if not select:
                found = bindings(self._agent.beliefs.query(_SELECT_Q, self._agent.beliefs.graphs_of(PUBLIC), {"node": row["avoided"]}))
                select = found[0]["select"] if found else None
            try:
                if select:
                    #  ASKED AS A RULE IS (#666): public knowledge, this agent's records and
                    #  its readings, all one default graph. The pattern names no world —
                    #  `query` alone reads the PUBLIC graphs, and an avoided state is almost
                    #  always about a reading, so asked there it binds nothing and a hot want
                    #  reads as met.
                    text = bind(select, this=self._agent.me.uri)
                    entered = bool(bindings(self._agent.beliefs.query(
                        text, self._agent.beliefs.graphs_of(*FORESEEN, at=clock.now()))))
                elif bindings(self._agent.beliefs.query(_IS_SHAPE_Q, self._agent.beliefs.graphs_of(PUBLIC), {"node": row["avoided"]})):
                    #  THE AVOIDED STATE AS A SHAPE (#499): compiled to its conformance
                    #  select — rows where the state has been entered — and run over the
                    #  same view a compiled positive want is.
                    text = self._unmet_select(row["want"], row["avoided"], entered=True)
                    entered = bool(bindings(self._agent.beliefs.query(
                    text, self._agent.beliefs.graphs_of(*KNOWN, at=clock.now()))))
                else:
                    log.error("%s: %s points at an avoided state that is neither a select "
                              "nor a shape", self._agent.id, row["want"])
                    continue
            except Exception as exc:
                log.error("%s: avoided-state pattern failed to run: %s", self._agent.id, exc)
                entered = True
            seen[row["want"]] = Want(uri=row["want"],
                                       state="unmet" if entered else "met")
        #  A SHAPE WANT NO MODULE SPEAKS FOR (#497): the courier's and hanoi's, authored
        #  positive and universal, pointing at a shape the package declares. Compiled once
        #  per want into the select whose rows are its violations — computed, never stored —
        #  and run on the store's own engine over the same view the judge would be handed.
        #  Binary, like the pattern wants above: met is no row.
        for row in bindings(self._agent.desires.query(_SHAPED_Q, {"me": self._agent.me.uri})):
            if row["want"] in seen or row["want"] in derived:
                continue
            try:
                text = self._unmet_select(row["want"], row["shape"])
                violated = bool(bindings(self._agent.beliefs.query(
                    text, self._agent.beliefs.graphs_of(*KNOWN, at=clock.now()))))
            except Exception as exc:
                log.error("%s: could not judge %s by its shape: %s", self._agent.id, row["want"], exc)
                violated = True
            seen[row["want"]] = Want(uri=row["want"],
                                       state="unmet" if violated else "met")
        #  A ROOT WITH WANTS UNDER IT IS PRESENTED AS THEM — one row per want, each
        #  carrying the root's own measure under the want's name, and ITS OWN STATE: a want's
        #  met-test is the root's instantiated at its witness, so a want about one tank reads
        #  met when that tank is in range, whatever the others read. Several where the
        #  witnesses fell in several scopes (one-function-mints-every-want); one everywhere shipped.
        for root, wants in children.items():
            if root not in seen:
                continue
            base = seen.pop(root)
            for want in wants:
                if want.uri in spoken_for:
                    presented = replace(spoken_for[want.uri], desire=root)
                else:
                    presented = replace(base, uri=want.uri, desire=root)
                    #  THE STATE IS THE WANT'S OWN where its shape says met — its instance is
                    #  in range, whatever the root's others read — and the root's word
                    #  otherwise, since the choir's words are finer than a shape's two
                    #  (`stale`, `unmeasured`); the MEASURE stays the root's either way, and
                    #  met-and-urgent is a true situation (desire.md).
                    own = self._own_state(want.uri)
                    if own == "met" or (own == "unmet" and presented.state == "met"):
                        presented = replace(presented, state=own)
                if want.holds_at:
                    presented = self._at_instant(
                        presented, want.uri, want.holds_at, want.derived_at, now)
                seen[want.uri] = presented
        #  IN NO ORDER OF MINE. These came back hottest first, and nothing ever chose by it:
        #  `Deliberator.pursued` plans for every want it is handed, so the rank decided which
        #  was searched first and nothing else. What would rank them is what their plans cost
        #  and how long they take, which is the search's answer and not a contributor's.
        return list(seen.values())

    def _own_state(self, want: str) -> str | None:
        """What a derived want's OWN met-test says of the world now — `met` or `unmet` — or
        None where it carries none of its own and is judged as its root is (a want minted
        before wants carried one). The shape lives in the want's graph, the agent's own."""
        rows = bindings(self._agent.desires.query(
            f"SELECT ?s WHERE {{ <{want}> orexis:metWhen ?s . FILTER(?s != <{want}>) }} LIMIT 1"))
        if not rows or not rows[0]["s"].startswith(want):
            return None
        try:
            text = self._unmet_select(want, rows[0]["s"])
            violated = bool(bindings(self._agent.beliefs.query(
                    text, self._agent.beliefs.graphs_of(*KNOWN, at=clock.now()))))
        except Exception as exc:                                    # noqa: BLE001
            log.error("%s: could not judge %s by its own shape: %s", self._agent.id, want, exc)
            return None
        return "unmet" if violated else "met"

    def _at_instant(self, row: Want, node: str, holds_at: datetime, since: datetime | None,
                    now: datetime | None) -> Want:
        """A want met AT an instant, as presented (#619): it reads met exactly where the newest
        prediction says the reading still holds at the instant, unmet where it says it will
        have crossed. Its room is TIME — the stretch from its derivation to the instant — and
        the fraction of that run used to be its urgency, which is the one arithmetic here the
        kernel did rather than a capability, and is gone with the field. The
        question is asked of the want's OWN results — the cluster it was minted from — so a
        want about one tank is not held to another's prediction."""
        from orexis_agent_deliberation.judging import unmet_by
        now = now or clock.now()
        state, read_at = row.state, row.read_at
        if state == "met":
            #  IS IT STILL IN TROUBLE BY THEN? The want was minted because its desire was
            #  judged unmet at this instant; a reading that lifted the corridor leaves the
            #  desire met by then, and the want reads met. The want's own met-test answers,
            #  asked at the instant it was minted for and over the results it was minted from.
            found = unmet_by(self._agent.beliefs.engine, node, holds_at)
            state = "unmet" if found is not None else "met"
            #  A want nobody's row dates — an asserted one the kernel lifts — takes the instant
            #  it reads unmet at, which is what a pass for it must be clocked from.
            if read_at is None and found is not None:
                read_at = found
        return replace(row, holds_at=holds_at, state=state, read_at=read_at)

    def _unmet_select(self, want: str, shape: str, entered: bool = False) -> str:
        """The compiled select of an asserted want's shape, once per process: an asserted
        want never changes while the agent runs, and compiling is a carve and a string. Read
        from public knowledge, where a package's shape lives — and the asserted block is
        public too. `entered` picks the conformance select, for a shape under `unmetWhen`."""
        from orexis_agent_deliberation.conformance import graph_from
        from orexis_agent_progression.violation import entered_select, unmet_select

        cache = self.__dict__.setdefault("_compiled_wants", {})
        if (want, entered) not in cache:
            #  AND THE AGENT'S OWN GRAPHS, asked by classification: a package's desire and its
            #  shape are authored into the roots graph at genesis (#644), not into public
            #  knowledge — compiled from the public graphs alone the ledger's shape had no
            #  target, raised, and the error path read the root as unmet every pass. It named
            #  the roots graph for a while; which graphs are the agent's is what boot's
            #  classification says, and a reader asks it rather than spelling an instance.
            public = graph_from(self._agent.beliefs,
                                *self._agent.beliefs.graphs_of(*KNOWN, at=clock.now()))
            compile = entered_select if entered else unmet_select
            cache[(want, entered)] = compile(public.cbd(URIRef(shape)), URIRef(shape))
        return cache[(want, entered)]
