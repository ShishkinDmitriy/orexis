"""Every judgment this agent is making right now, as a collection.

**THE ONE COLLECTION THAT IS MADE RATHER THAN HELD, and the exception is stated because the
convention asks for it.** Every other repository here reads rows somebody wrote: `Wants` and
`Desires` hand back what is in a graph. Nothing ever writes a judgment. This one ASSEMBLES —
it asks every module what it is pursuing and how badly, runs an avoided state's own select to
see whether the world has entered it, compiles a shape into the select whose rows are its
violations, and ranks what comes back by an urgency each contributor computed its own way.

That makes it a repository by its name and a service by its work, which is a line this repo
usually holds (`a-repository-is-not-a-service`). It is kept on the collection side for the
reason `Affordances` is: what it hands back is a collection of domain objects, derived on every ask
and never stored, and a caller asking "what am I pursuing" is asking for the contents rather
than for a decision. See knowledge/decisions/a-desire-is-declared-and-a-judgment-is-made.md.

**It is handed the AGENT, and unlike `Wants` that is not a failure to narrow.** A judgment is
CONTRIBUTED — the ledger judges a debt by its redeem window, sensing judges a stake by the
survival envelope — so the collection has to reach the choir, and the choir is the agent. A
repository over stored rows needs a store; a repository over contributed answers needs the
contributors. That asymmetry is the clearest statement of what the two kinds of collection are.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from rdflib import URIRef

from orexis_agent_deliberation.judgment import Judgment
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import DESIRES
from orexis_agent_progression.store import bind, bindings

log = logging.getLogger("judgments")

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
#  THE WANTS DERIVED UNDER A ROOT (#618): an `orexis:Desire` is never pursued itself, and
#  while a want derived under it stands the container presents THAT, with the root's own measure.
_CHILDREN_Q = """
SELECT ?me ?root ?child ?holdsAt ?since WHERE {
  ?me orexis:holds ?child .
  ?child a orexis:Want ; orexis:bindsWhen ?binding ; prov:wasDerivedFrom ?root .
  ?root a orexis:Desire .
  FILTER(?binding IN (orexis:AtEnd, orexis:At))
  OPTIONAL { ?child orexis:holdsAt ?holdsAt ; prov:generatedAtTime ?since }
}"""


class Judgments:
    """Every judgment this agent is making, hottest first."""

    def __init__(self, agent):
        self._agent = agent

    def find_all(self, now: datetime | None = None) -> list[Judgment]:
        """Everything this agent is pursuing, hottest first, whoever sourced it.

        Assembled from the modules that hold wants rather than asked of one, because since the
        ledger became its own capability no single module can see them all: desire contributes
        stakes, owing contributes debts, and an agent may compose either without the other. The
        ranking is what makes the two comparable — urgency is unit-free on both sides, so a
        litre owed and a pot drying finally rank against each other.
        """
        #  ONE WANT, ONE NODE. Two modules may hold the same want — the gardener composes two
        #  sensing modules and each reads every region the agent holds — and a want is its
        #  node, so the second sighting is the same want and not a second one.
        seen: dict[str, Judgment] = {}
        #  A ROOT IS PRESENTED AS THE WANT DERIVED UNDER IT (#618), where one stands: the
        #  root's own row — its measure, its reading, its property — under the derived want's
        #  name, naming the root beside it. The derived want is never lifted on its own.
        children = {r["root"]: r
                    for r in bindings(self._agent.desires.query_union(_CHILDREN_Q, {"me": self._agent.me.uri}))}
        derived = {r["child"] for r in children.values()}
        for wants in self._agent.ask(DESIRES, now):
            for judgment in wants:
                if judgment.uri not in derived:
                    seen.setdefault(judgment.uri, judgment)
        #  THE WANTS NO MODULE SPEAKS FOR (#468): a world may ratify a desire DIRECTLY — the
        #  asserted block — and wanting is the kernel's, so the kernel is who lifts such a
        #  want into pursuit rather than a capability minted to re-say it. Scoped to the
        #  avoided-pattern wants, whose judging is one select on the store's own engine;
        #  binary, because between entered and held there is nothing to be nearer to. A
        #  pattern that fails to run reads as unmet — the loud direction.
        for row in bindings(self._agent.desires.query_union(_AVOIDED_Q, {"me": self._agent.me.uri})):
            if row["want"] in seen or row["want"] in derived:
                continue
            #  THE DESIRE OWNS THE TERM AND THE PACKAGE OWNS THE MEASURE: a world may write
            #  the pattern inline beside its asserted want, or point at a node the domain
            #  package declares. The first rides in the modality; the second is public
            #  knowledge and is asked of the belief base — one text, either road.
            select = row.get("select")
            if not select:
                found = bindings(self._agent.beliefs.query(_SELECT_Q, {"node": row["avoided"]}))
                select = found[0]["select"] if found else None
            try:
                if select:
                    #  ASKED AS A RULE IS (#666): public knowledge, this agent's records and
                    #  its readings, all one default graph. The pattern names no world —
                    #  `query` alone reads the PUBLIC graphs, and an avoided state is almost
                    #  always about a reading, so asked there it binds nothing and a hot want
                    #  reads as met.
                    text = bind(select, this=self._agent.me.uri)
                    entered = bool(bindings(self._agent.beliefs.query_at(text)))
                elif bindings(self._agent.beliefs.query(_IS_SHAPE_Q, {"node": row["avoided"]})):
                    #  THE AVOIDED STATE AS A SHAPE (#499): compiled to its conformance
                    #  select — rows where the state has been entered — and run over the
                    #  same view a compiled positive want is.
                    text = self._unmet_select(row["want"], row["avoided"], entered=True)
                    entered = bool(bindings(self._agent.beliefs.query_over(
                        text, *self._agent.beliefs.public_graphs(),
                        *self._agent.beliefs.recorded_graphs())))
                else:
                    log.error("%s: %s points at an avoided state that is neither a select "
                              "nor a shape", self._agent.id, row["want"])
                    continue
            except Exception as exc:
                log.error("%s: avoided-state pattern failed to run: %s", self._agent.id, exc)
                entered = True
            seen[row["want"]] = Judgment(uri=row["want"],
                                       urgency=1.0 if entered else 0.0,
                                       state="unmet" if entered else "met")
        #  A SHAPE WANT NO MODULE SPEAKS FOR (#497): the courier's and hanoi's, authored
        #  positive and universal, pointing at a shape the package declares. Compiled once
        #  per want into the select whose rows are its violations — computed, never stored —
        #  and run on the store's own engine over the same view the judge would be handed.
        #  Binary, like the pattern wants above: met is no row.
        for row in bindings(self._agent.desires.query_union(_SHAPED_Q, {"me": self._agent.me.uri})):
            if row["want"] in seen or row["want"] in derived:
                continue
            try:
                text = self._unmet_select(row["want"], row["shape"])
                violated = bool(bindings(self._agent.beliefs.query_over(
                    text, *self._agent.beliefs.public_graphs(), *self._agent.beliefs.recorded_graphs())))
            except Exception as exc:
                log.error("%s: could not judge %s by its shape: %s", self._agent.id, row["want"], exc)
                violated = True
            seen[row["want"]] = Judgment(uri=row["want"],
                                       urgency=1.0 if violated else 0.0,
                                       state="unmet" if violated else "met")
        for root, r in children.items():
            if root not in seen:
                continue
            seen[root] = replace(seen[root], uri=r["child"], derived_from=root)
            if r.get("holdsAt"):
                seen[root] = self._at_instant(seen[root], root, datetime.fromisoformat(r["holdsAt"]),
                                              datetime.fromisoformat(r["since"]) if r.get("since") else None,
                                              now)
        return sorted(seen.values(), key=lambda g: -g.urgency)

    def _at_instant(self, row: Judgment, root: str, holds_at: datetime, since: datetime | None,
                    now: datetime | None) -> Judgment:
        """A want met AT an instant, as presented (#619): its room is TIME — the stretch from
        its derivation to the instant, the fraction run being its urgency, never less than
        the root's own — and it reads met exactly where the newest prediction says the
        reading still holds at the instant, unmet where it says it will have crossed."""
        from orexis_agent_deliberation import pursuit
        now = now or clock.now()
        urgency = row.urgency
        if since is not None and holds_at > since:
            run = (now - since).total_seconds() / (holds_at - since).total_seconds()
            urgency = max(urgency, min(1.0, max(0.0, run)))
        state, read_at = row.state, row.read_at
        if state == "met":
            #  The newest prediction, from the reading in hand: still crossing by the instant
            #  is unmet; a reading a dose has lifted predicts a later crossing, and that is met.
            found = pursuit.crossing_row_of(self._agent, root)
            state = "unmet" if found is not None and found[0] <= holds_at else "met"
            #  A want nobody's row dates — an asserted one the kernel lifts — takes the instant
            #  of the reading the crossing was predicted from, which is what a pass for it
            #  must be clocked from.
            if read_at is None and found is not None:
                read_at = found[1]
        return replace(row, holds_at=holds_at, urgency=urgency, state=state, read_at=read_at)

    def _unmet_select(self, want: str, shape: str, entered: bool = False) -> str:
        """The compiled select of an asserted want's shape, once per process: an asserted
        want never changes while the agent runs, and compiling is a carve and a string. Read
        from public knowledge, where a package's shape lives — and the asserted block is
        public too. `entered` picks the conformance select, for a shape under `unmetWhen`."""
        from orexis_agent_deliberation.conformance import graph_from
        from orexis_agent_progression.violation import entered_select, unmet_select

        cache = self.__dict__.setdefault("_compiled_wants", {})
        if (want, entered) not in cache:
            public = graph_from(self._agent.beliefs, *self._agent.beliefs.public_graphs())
            compile = entered_select if entered else unmet_select
            cache[(want, entered)] = compile(public.cbd(URIRef(shape)), URIRef(shape))
        return cache[(want, entered)]
