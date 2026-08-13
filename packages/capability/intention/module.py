"""intention:Keeping — the ledger of what this agent is committed to, and the patience that
makes a commitment mean something.

**This existed before it had a name, as module state.** `bidding.pending` was an intention to
observe; a bid awaiting its voucher was an intention to acquire; both lived in Python attributes
that died with the process and answered to nothing. They are rows in a graph now, with an
adoption time, a resolution, and a reason — so an operator can ask what an agent thought it was
doing, and phase 4's deliberator can ask what already stands before deciding anything.

**Nothing here decides, and the seam is deliberate.** Whoever acts calls `adopt` when it acts
and `satisfy`/`drop` when the world answers; this module only keeps the ledger honest. The one
piece of policy it owns is the COMMITMENT itself: `adopt` refuses to re-adopt what is already
standing and younger than the agent's patience, and that refusal is the amortisation the
decision record is named for — within your patience, a second impulse to do the same thing is
absorbed, not re-decided. With an LLM deliberator that absorption is the cost model.

Vocabulary: packages/capability/intention/ontology.ttl. Rules: its shapes.ttl. Derivation: its
rules.ru. See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from agent.beliefs import Block
from agent.module import Module
from agent.store import bindings

from .graphs import intentions_graph
from .terms import BECAUSE_OF, KEEPING, NS, PATIENCE_S, term


@dataclass(frozen=True)
class KeepingBeliefs:
    """intention:Keeping — the commitment policy, which is the agent's own opinion."""

    patience_s: int


KEEPING_BLOCK = Block(
    capability=KEEPING,
    cls=KeepingBeliefs,
    terms={"patience_s": PATIENCE_S},
)


@dataclass(frozen=True)
class Standing:
    """One unresolved commitment, as a reader gets it back."""

    uri: str
    means: str
    observed_property: str
    adopted_at: datetime

    def age_s(self, now: datetime | None = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.adopted_at).total_seconds()


class IntentionModule(Module):
    """The keeper. Speaks to no topic; its callers are its siblings, through the agent."""

    CAPABILITY = KEEPING
    name = "intention"

    def __init__(self, agent):
        super().__init__(agent)
        self.beliefs = agent.beliefs.read(KEEPING_BLOCK)
        self.graph = intentions_graph(agent.id)

    # --- the ledger, written -------------------------------------------------------------

    def adopt(self, means: str, observed_property: str, because: str) -> str | None:
        """Commit to one means toward one property. Returns the intention's IRI, or None.

        **None is the amortisation**: an intention with the same means and property already
        stands and is younger than my patience, so the impulse is absorbed rather than
        re-decided — the caller should treat it exactly as it treats its own cooldowns. A
        standing one PAST my patience is superseded: resolved as dropped with the reason
        recorded, and the new commitment adopted, because honouring a commitment forever is as
        wrong as honouring it not at all.
        """
        now = datetime.now(timezone.utc)
        for standing in self.standing(means=means, observed_property=observed_property):
            if standing.age_s(now) <= self.beliefs.patience_s:
                return None
            self._resolve(standing.uri, "dropped",
                          f"outwaited: stood {standing.age_s(now):.0f}s against a patience "
                          f"of {self.beliefs.patience_s}s, superseded by a new adoption")
        uri = f"{NS}intent_{self.agent.id}_{uuid.uuid4().hex[:8]}"
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> a <{term("Intention")}> ;
    <{term("by")}> <{means}> ;
    <http://www.w3.org/ns/ssn/forProperty> <{observed_property}> ;
    <{term("adoptedAt")}> "{now.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("adopted %s(%s): %s",
                      means.rsplit("#", 1)[-1], observed_property.rsplit("#", 1)[-1], because)
        return uri

    def satisfy(self, means: str, observed_property: str, because: str) -> None:
        """The world answered: whatever stood for this means and property is done."""
        for standing in self.standing(means=means, observed_property=observed_property):
            self._resolve(standing.uri, "satisfied", because)

    def drop(self, means: str, observed_property: str, because: str) -> None:
        """The commitment died without being met, and the reason is the record.

        A commitment abandoned without a reason is indistinguishable from one forgotten, which
        is why the argument is not optional.
        """
        for standing in self.standing(means=means, observed_property=observed_property):
            self._resolve(standing.uri, "dropped", because)

    def _resolve(self, uri: str, outcome: str, because: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.agent.store.update(f"""
INSERT DATA {{ GRAPH <{self.graph}> {{
  <{uri}> <{term("resolvedAt")}> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
          <{term("outcome")}> {_literal(outcome)} ;
          <{BECAUSE_OF}> {_literal(because)} .
}} }}""")
        self.log.info("%s: %s", outcome, because)

    # --- the ledger, read ----------------------------------------------------------------

    def standing(self, means: str | None = None,
                 observed_property: str | None = None) -> list[Standing]:
        """What stands: adopted and not resolved. The question a deliberator asks first."""
        clauses = [f"?i a <{term('Intention')}> ; <{term('by')}> ?means ; "
                   f"<http://www.w3.org/ns/ssn/forProperty> ?property ; "
                   f"<{term('adoptedAt')}> ?at .",
                   f"FILTER NOT EXISTS {{ ?i <{term('resolvedAt')}> ?done }}"]
        if means:
            clauses.append(f"FILTER(?means = <{means}>)")
        if observed_property:
            clauses.append(f"FILTER(?property = <{observed_property}>)")
        rows = bindings(self.agent.store.query(
            "SELECT ?i ?means ?property ?at WHERE { GRAPH <%s> { %s } }"
            % (self.graph, " ".join(clauses))))
        return [Standing(uri=r["i"], means=r["means"], observed_property=r["property"],
                         adopted_at=datetime.fromisoformat(r["at"]))
                for r in rows]

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
        return out


def _literal(text: str) -> str:
    """A prose reason as a safe SPARQL string literal."""
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
