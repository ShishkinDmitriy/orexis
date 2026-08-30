"""The OWER: the ledger of what this agent owes, and why keeping it is its own ability.

Named for what it does, like every service — `Ower` runs owing, as `Keeper` runs keeping. The
capability words below (`desire:Owing`, `desire:Deducing`) are retired and kept here because the
argument they carry is why this is a separate ledger at all.

A debt is a want this agent did not source, so it belongs to the desire family's vocabulary —
and keeping one is a DIFFERENT ability from working out a region, granted by a different fact.
Deducing needs a stake: something to advance for, that states what it needs. Owing needs a
LEVER others can demand: a venue this agent opened and an actuator drawing from its source.

They were one capability, and `world/simulation`'s city showed the cost (#233). The city acts
for a mains that states no ranges, so it had no stake, so no desire module, so no ledger — while
hosting a market, issuing claims and redeeming them all day. The one agent whose failure to
deliver would have left no evidence was the one best placed to fail. Splitting the capability
gives it a ledger without pretending it wants anything for itself.

Vocabulary: this package's ontology.ttl. Grant: rule 1b of its rules.ru.
See knowledge/decisions/an-obligation-is-a-desire-someone-else-sourced.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from orexis_deliberation_search.desire import Desire
from agent.module import Module
from orexis_progression_patience.ontology import AG, obligations_graph
from orexis_progression_patience.store import bindings

#  What I owe, as rows — the obligation branch of what used to be one shipped `desires.rq` for every
#  kind of want. The stakes and the freshness wants went to sensing with the region
#  (the-stake-is-sensings-want), and the ledger reads its own graph, which it always named.
_DUTIES_Q = """
SELECT ?desire ?owedTo ?claim ?presented ?at ?expires WHERE {
  GRAPH <%s> {
    ?desire a ag:Obligation ; ag:owedTo ?owedTo ; ag:forClaim ?claim ;
            ag:presented ?presented ; ag:owedAt ?at .
    OPTIONAL { ?desire ag:expiresAt ?expires }
    FILTER NOT EXISTS { ?desire ag:dischargedAt ?paid } }
}"""


def _duty_urgency(row: dict, now: datetime) -> float:
    """The fraction of the claim's redeem window that has run, clamped.

    Here rather than in the query because the store's engine binds NOTHING for
    `duration / duration` — measured, and pinned by a test, because an unsupported operation
    that returns unbound instead of failing is how a whole column silently reads zero.
    """
    if not row.get("expires"):
        return 0.0                        # a market with no redeem channel; nobody is waiting
    owed_at = datetime.fromisoformat(row["at"])
    window = (datetime.fromisoformat(row["expires"]) - owed_at).total_seconds()
    if window <= 0:
        return 1.0
    return max(0.0, min(1.0, (now - owed_at).total_seconds() / window))


class Ower(Module):
    """What I owe, kept where a restart cannot lose it. Speaks to no topic."""

    #  THE LOG CHANNEL IS THE PROCESS, not the class: `Deliberator` logs to `deliberation` and
    #  `Keeper` to `intention`, so `Ower` logs to `owing`. Renaming this would rename a channel
    #  an operator greps, for no gain.
    name = "owing"

    def _uri_of(self, agent_id: str) -> str | None:
        """The counterparty's node, from the one thing a claim carries: its id. Public wiring,
        so a debt names an agent the world declares and never a string somebody sent me."""
        rows = bindings(self.agent.beliefs.query(
            f'SELECT ?a WHERE {{ ?a a <http://example.org/orexis#Agent> ; '
            f'<http://example.org/orexis#localId> "{agent_id}" }} LIMIT 1'))
        return rows[0]["a"] if rows else None

    def owe(self, to_agent_id: str, claim_jti: str,
            expires_at: float | None = None, amount_l: float | None = None) -> str | None:
        """Record what the society just made this agent owe. Returns the obligation's IRI.

        Raised when a claim is ISSUED, not when it is presented: the debt exists from the
        moment the society allocated it, and the holder's silence afterwards is the holder's
        business. Idempotent by the claim's own jti — single-use there, single-use here — so a
        replay raises nothing new.

        Written to a graph of this agent's own, so a restarting host still knows what it owes:
        the issued claims used to live in a module dict that died with the process.
        """
        to_agent = self._uri_of(to_agent_id)
        if to_agent is None:
            # Whom I may owe is TOPOLOGY (the ACL shape): an obligation to an agent this
            # world does not declare is not a debt, it is a forgery, and refusing here means
            # no forged presentation can ever raise a want.
            self.log.warning("asked to owe %s, whom this world does not declare — refused",
                             to_agent_id)
            return None
        #  The claim's own deadline, kept as the debt's. Both timestamps are recorded because
        #  urgency is the room BETWEEN them — how much of the window has run — and an agent
        #  that stored only the expiry would have to assume when the window opened. A claim
        #  with no expiry leaves the triple out, and the obligation is simply never hot: that
        #  is a market with no redeem channel, where the dose went out on issue and there was
        #  never a wait to be late for.
        #  The amount, recorded so the effect rule that says what SERVING makes true can size
        #  the pour from the record rather than from a module's memory (#255). Optional for
        #  the one market shape with no quantity; an obligation without it stays servable by
        #  the direct row and unplannable, which is the graceful half of the widening.
        amount = (f' <{AG}amountL> {amount_l} ;' if amount_l is not None else "")
        expiry = ""
        if expires_at is not None:
            expiry = (f' ;\n                <{AG}expiresAt> '
                      f'"{datetime.fromtimestamp(expires_at, timezone.utc).isoformat()}"'
                      f'^^<http://www.w3.org/2001/XMLSchema#dateTime>')
        uri = f"{AG}obligation.{claim_jti}"
        graph = obligations_graph(self.agent.id)
        if bindings(self.agent.beliefs.query(
                f"SELECT ?o WHERE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }} LIMIT 1")):
            return None
        self.agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{graph}> {{
            <{uri}> a <{AG}Obligation> ;
                <http://www.w3.org/ns/prov#wasDerivedFrom> "{claim_jti}" ;
                <{AG}owedTo> <{to_agent}> ;
                <{AG}forClaim> "{claim_jti}" ;
                <{AG}presented> false ;{amount}
                <{AG}owedAt> "{datetime.now(timezone.utc).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime>{expiry} }} }}""")
        #  A debt arriving at runtime is a want arriving at runtime: the record above is the
        #  belief base's, and the desire modality is RECOMPUTED to hold it — the same
        #  record-then-rebuild order a re-pick follows, because recomputation is the only way
        #  that store ever changes.
        self.agent.desires.rebuild()
        self.log.info("owed to %s for claim %s", to_agent_id, claim_jti)
        return uri

    def demanded(self, claim_jti: str) -> None:
        """The holder presented: an obligation nobody had asked for is now asked for.

        The step this capability's `presented` flag exists for — an unpresented claim
        requires nothing of me, a presented one requires acting now — and the reason urgency
        here is a step rather than a curve until claims may be held over time.
        """
        graph = obligations_graph(self.agent.id)
        self.agent.beliefs.update(f"""
            DELETE {{ GRAPH <{graph}> {{ ?o <{AG}presented> ?was }} }}
            INSERT {{ GRAPH <{graph}> {{ ?o <{AG}presented> true }} }}
            WHERE  {{ GRAPH <{graph}> {{ ?o <{AG}forClaim> "{claim_jti}" ;
                                         <{AG}presented> ?was }} }}""")
        self.agent.desires.rebuild()   # standing became demanded — the want moved

    def discharge(self, claim_jti: str) -> None:
        """The dose is out: the debt is paid, and says when. Never deleted — a debt paid and
        a debt forgotten must not look alike, which is the same reason a resolved intention
        stays in its ledger."""
        graph = obligations_graph(self.agent.id)
        self.agent.beliefs.update(f"""INSERT {{ GRAPH <{graph}> {{
                ?o <{AG}dischargedAt> "{datetime.now(timezone.utc).isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
            WHERE {{ GRAPH <{graph}> {{ ?o <{AG}forClaim> "{claim_jti}" .
                     FILTER NOT EXISTS {{ ?o <{AG}dischargedAt> ?done }} }} }}""")
        self.agent.desires.rebuild()   # a paid debt is history, and the want is no longer implied

    def owed(self, presented_only: bool = False) -> list[dict]:
        """What still stands, newest first — what an agent owes, askable by the sovereign."""
        extra = f'?o <{AG}presented> true .' if presented_only else ""
        return bindings(self.agent.beliefs.query(f"""
SELECT ?o ?to ?jti ?presented ?at ?expires WHERE {{ GRAPH <{obligations_graph(self.agent.id)}> {{
  ?o a <{AG}Obligation> ; <{AG}owedTo> ?to ; <{AG}forClaim> ?jti ;
     <{AG}presented> ?presented ; <{AG}owedAt> ?at .
  OPTIONAL {{ ?o <{AG}expiresAt> ?expires }}
  {extra}
  FILTER NOT EXISTS {{ ?o <{AG}dischargedAt> ?done }} }} }} ORDER BY DESC(?at)"""))

    def obligations(self, now: datetime | None = None) -> list[Desire]:
        """What this agent owes, as desires — hottest first, and hot means CLOSE TO EXPIRY.

        A stake's urgency is distance scaled by the survival envelope; an obligation has no envelope,
        so its room is time: the fraction of the redeem window that has run. At issue nothing
        has gone wrong and the debt is cool; at the deadline it is maximal. The sovereign chose
        this over the two alternatives the obligation record names as the whole risk — an obligation
        pinned at 1.0 is the honoured mode returning under another name, and an obligation with no heat
        is an agent that defects while its ledger looks tidy.

        A debt whose claim named no deadline stays at zero for ever, and that is not a bug: the
        market that issued it has no redeem channel, so the dose went out when it was won and
        nobody is waiting. `pursuable` is the OTHER question — whether the holder has asked, and
        whether the window is still open — and it is deliberately not folded into urgency,
        because a debt this agent can see expiring while nobody has presented is worth seeing.
        """
        return self.desires(now)

    def desires(self, now: datetime | None = None) -> list[Desire]:
        """MY contribution to what this agent is pursuing: its debts, and no stakes.

        The half of the choir the city had no way to contribute before, which is the whole of
        #233. Lapsed is judged HERE, against the same clock the urgency uses — one reader, one
        now, so a debt cannot be maximally hot and still count as open because two clocks
        disagreed.
        """
        now = now or datetime.now(timezone.utc)
        out = []
        for row in bindings(self.agent.desires.query_union(
                _DUTIES_Q % obligations_graph(self.agent.id))):
            demanded = row.get("presented") == "true"
            lapsed = bool(row.get("expires")) and now >= datetime.fromisoformat(row["expires"])
            out.append(Desire(uri=row["desire"], urgency=_duty_urgency(row, now),
                              claim=row["claim"], owed_to=row["owedTo"],
                              state="lapsed" if lapsed else
                                    ("demanded" if demanded else "standing"),
                              pursuable=demanded and not lapsed))
        return sorted(out, key=lambda g: -g.urgency)

    def series(self) -> list[tuple[str, dict, dict]]:
        """What I owe, as figures. A host straining under debts it cannot serve used to look
        exactly like a calm one on every panel — and a host with no stake of its own reported
        nothing at all, because the module that would have said so was never composed."""
        obligations = self.desires()
        return [("agent_debts", {}, {
            "owed": float(len(obligations)),
            "demanded": float(sum(1 for g in obligations if g.pursuable)),
            "hottest": max((g.urgency for g in obligations), default=0.0),
        })]
