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

from orexis_agent_deliberation.judgment import Judgment
from agent.module import Module
from orexis_agent_progression.ontology import (CLASSIFICATION_GRAPH, OREXIS, PERIODS_GRAPH, REPREDICT,
                                               obligations_graph)
from orexis_agent_progression.store import bind, bindings
from .terms import (AMOUNT_L, DISCHARGED_AT, FOR_CLAIM, LAPSED_AT, LAPSES_AT, NS, OWED_AT, OWED_FROM,
                    OWED_TO, PRESENTED)
from orexis_agent_progression import clock

#  What I owe, as rows — the obligation branch of what used to be one shipped `desires.rq` for every
#  kind of want. The stakes and the freshness wants went to sensing with the region
#  (the-stake-is-sensings-want), and the ledger reads its own graph, which it always named.
#  Rows are matched by their PREMISES — a counterparty, a claim — and never by a type: the
#  Obligation class retired (#471), and a volume written before it did carries the old type
#  triple harmlessly, because nothing asks.
#  OVER THE MODALITY'S UNION (#645): a debt is a graph of its own, holding from its issue to
#  its expiry, and the projection copies every one holding now; a settled row — paid or
#  lapsed — in the untimed record carries no `presented`, so it never reads as a duty.
#  THE ROAD'S WANT, judged by the ledger. A want under "no overdue debts" is minted by the
#  pursuit road about ONE debt — `orexis:about` names it — and what the ledger contributes is
#  the judgment of that want: how far its claim's redeem window has run, whom it is owed to,
#  when it expires, whether the holder has asked. The ledger used to mint the want itself and
#  judge its own; it writes debts and predictions now, and speaks for what the road derives
#  (one-road-derives-every-want). `$root` is this agent's desire.
_DUTIES_Q = """
SELECT ?desire ?owedTo ?claim ?presented ?at ?expires WHERE {
    ?desire prov:wasDerivedFrom $root ; orexis:about ?debt .
    ?debt market:owedTo ?owedTo ; market:forClaim ?claim ;
          market:presented ?presented ; market:owedAt ?at .
    OPTIONAL { ?debt orexis:expiresAt ?expires }
    FILTER NOT EXISTS { ?debt market:dischargedAt ?paid }
    FILTER NOT EXISTS { ?debt market:lapsedAt ?lapsed }
}"""


def obligation_graph(agent_id: str, claim_jti: str) -> str:
    """ONE debt's graph in ONE agent's store — the unit a period is said of (#645): holding
    from the claim's issue to its expiry, under the untimed record `obligations_graph`."""
    return f"{obligations_graph(agent_id)}/{claim_jti}"

def lapse_graph(agent_id: str, claim_jti: str) -> str:
    """The PREDICTION beside one debt: that it lapses at its deadline, a graph holding from that
    instant on. What makes "overdue" askable — the door hands it at the deadline and not before,
    so the desire's met-test reads met while a debt has time to run and unmet at the instant it
    would not, with no rule reading a clock (one-road-derives-every-want)."""
    return f"{obligation_graph(agent_id, claim_jti)}/lapse"


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
            expires_at: float | None = None, amount_l: float | None = None,
            usable_from: float | None = None) -> str | None:
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
        amount = (f' <{AMOUNT_L}> {amount_l} ;' if amount_l is not None else "")
        #  FROM WHEN it may be demanded (#626): the claim's usable instant — the arrival this
        #  debt predicts, which the vessel's drift reads to foresee the stock leaving its region.
        opens = ""
        if usable_from is not None:
            opens = (f' ;\n                <{OWED_FROM}> '
                     f'"{datetime.fromtimestamp(usable_from, timezone.utc).isoformat()}"'
                     f'^^<http://www.w3.org/2001/XMLSchema#dateTime>')
        expiry = ""
        if expires_at is not None:
            expiry = (f' ;\n                <{OREXIS}expiresAt> '
                      f'"{datetime.fromtimestamp(expires_at, timezone.utc).isoformat()}"'
                      f'^^<http://www.w3.org/2001/XMLSchema#dateTime>')
        uri = f"{OREXIS}obligation.{claim_jti}"
        graph = obligation_graph(self.agent.id, claim_jti)
        if bindings(self.agent.beliefs.query_union(
                f"SELECT ?o WHERE {{ ?o <{FOR_CLAIM}> \"{claim_jti}\" }} LIMIT 1")):
            return None
        #  A GRAPH HOLDING DURING THE DEBT (#645): from its issue to the claim's expiry, open
        #  where the claim named none. The door hands a lapsed debt to nobody, the one sweep
        #  drops its graph, and `outdated` below writes what it came to into the record.
        now = clock.now()
        ends = (f'\n      orexis:end "{datetime.fromtimestamp(expires_at, timezone.utc).isoformat()}"^^xsd:dateTime ;'
                if expires_at is not None else "")
        #  THE DEBT, AND WHAT THE LEDGER PREDICTS OF IT — never the want. The want under "no
        #  overdue debts" is the road's to mint from this, the way a want under a region desire
        #  is minted from a reading and the drift's prediction (one-road-derives-every-want).
        #  The prediction is a graph holding FROM the deadline: at that instant the debt is
        #  unserved unless something is done, which is exactly what a drift says of a reading.
        lapse = ""
        if expires_at is not None:
            when = datetime.fromtimestamp(expires_at, timezone.utc).isoformat()
            lapse = f"""
  GRAPH <{lapse_graph(self.agent.id, claim_jti)}> {{
            <{uri}> <{LAPSES_AT}> "{when}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{lapse_graph(self.agent.id, claim_jti)}> a orexis:PredictionGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{lapse_graph(self.agent.id, claim_jti)}> dcterms:temporal [ a dcterms:PeriodOfTime ;
      orexis:start "{when}"^^xsd:dateTime ] . }}"""
        self.agent.beliefs.update(f"""INSERT DATA {{
  GRAPH <{graph}> {{
            <{uri}> <{OWED_TO}> <{to_agent}> ;
                <{FOR_CLAIM}> "{claim_jti}" ;
                <{PRESENTED}> false ;{amount}
                <{OWED_AT}> "{now.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime>{opens}{expiry} }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> a <{NS}ObligationsGraph> ; orexis:arrivedBy orexis:Received . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;{ends}
      orexis:start "{now.isoformat()}"^^xsd:dateTime ] . }}{lapse}
}}""")
        #  A debt arriving at runtime is a want arriving at runtime: the record above is the
        #  belief base's, and the desire modality is RECOMPUTED to hold it — the same
        #  record-then-rebuild order a re-pick follows, because recomputation is the only way
        #  that store ever changes.
        self.agent.desires.rebuild()
        self.log.info("owed to %s for claim %s", to_agent_id, claim_jti)
        self.agent.tell(REPREDICT)      # the ledger is a premise the vessel's drift reads (#643)
        self._road()                    # an instance arrived; the road mints, the ledger does not
        return uri

    def demanded(self, claim_jti: str) -> None:
        """The holder presented: an obligation nobody had asked for is now asked for.

        The step this capability's `presented` flag exists for — an unpresented claim
        requires nothing of me, a presented one requires acting now — and the reason urgency
        here is a step rather than a curve until claims may be held over time.
        """
        #  WHEREVER THE DEBT IS: its own graph (#645), or the untimed record for one written
        #  before debts had graphs of their own.
        self.agent.beliefs.update(f"""
            DELETE {{ GRAPH ?g {{ ?o <{PRESENTED}> ?was }} }}
            INSERT {{ GRAPH ?g {{ ?o <{PRESENTED}> true }} }}
            WHERE  {{ GRAPH ?g {{ ?o <{FOR_CLAIM}> "{claim_jti}" ;
                                  <{PRESENTED}> ?was }}
                      FILTER(STRSTARTS(STR(?g), "{obligations_graph(self.agent.id)}")) }}""")
        self.agent.desires.rebuild()   # standing became demanded — the want moved
        self.agent.tell(REPREDICT)      # the ledger is a premise the vessel's drift reads (#643)
        self._road()                    # a claim with no deadline is a want from presentation

    def discharge(self, claim_jti: str) -> None:
        """The dose is out: the debt is paid, and says when. Never deleted — a debt paid and
        a debt forgotten must not look alike, which is the same reason a resolved intention
        stays in its ledger."""
        self.agent.beliefs.update(f"""INSERT {{ GRAPH ?g {{
                ?o <{DISCHARGED_AT}> "{clock.now().isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }} }}
            WHERE {{ GRAPH ?g {{ ?o <{FOR_CLAIM}> "{claim_jti}" .
                     FILTER NOT EXISTS {{ ?o <{DISCHARGED_AT}> ?done }} }}
                     FILTER(STRSTARTS(STR(?g), "{obligations_graph(self.agent.id)}")) }}""")
        #  A DEBT PAID WILL NOT LAPSE: the prediction goes, and with it the want's ground.
        self.agent.beliefs.drop_graph(lapse_graph(self.agent.id, claim_jti))
        self.agent.desires.rebuild()   # a paid debt is history, and the want is no longer implied
        self.agent.tell(REPREDICT)      # the ledger is a premise the vessel's drift reads (#643)

    def owed(self, presented_only: bool = False) -> list[dict]:
        """What still stands, newest first — what an agent owes, askable by the sovereign."""
        extra = f'?o <{PRESENTED}> true .' if presented_only else ""
        #  THROUGH THE DOOR (#645): a debt past its window is handed to nobody, so what still
        #  stands is what the door hands at this instant.
        return bindings(self.agent.beliefs.query_at(f"""
SELECT ?o ?to ?jti ?presented ?at ?expires WHERE {{
  ?o <{OWED_TO}> ?to ; <{FOR_CLAIM}> ?jti ;
     <{PRESENTED}> ?presented ; <{OWED_AT}> ?at .
  OPTIONAL {{ ?o <{OREXIS}expiresAt> ?expires }}
  {extra}
  FILTER NOT EXISTS {{ ?o <{DISCHARGED_AT}> ?done }} }} ORDER BY DESC(?at)"""))

    def settled(self) -> list[dict]:
        """What this agent's debts came to (#645): each paid or lapsed, in the untimed record
        — the verdict the ledger keeps once a debt's own graph is gone. Askable by the sovereign."""
        return bindings(self.agent.beliefs.query_union(f"""
SELECT ?o ?to ?jti ?paid ?lapsed WHERE {{ GRAPH <{obligations_graph(self.agent.id)}> {{
  ?o <{OWED_TO}> ?to ; <{FOR_CLAIM}> ?jti .
  OPTIONAL {{ ?o <{DISCHARGED_AT}> ?paid }} OPTIONAL {{ ?o <{LAPSED_AT}> ?lapsed }}
  FILTER(BOUND(?paid) || BOUND(?lapsed)) }} }} ORDER BY ?jti"""))

    def outdated(self, graph: str) -> None:
        """A debt's window has closed and the one sweep is about to drop its graph (#645): the
        verdict is written first, into the untimed record — `market:dischargedAt` carried
        over for a debt paid, `market:lapsedAt` now for one the holder never presented — so
        a debt paid and a debt forgotten never look alike, and the ledger keeps the verdict,
        not the want. The vessel's drift read the debt as an arrival, so it predicts again."""
        if not graph.startswith(obligations_graph(self.agent.id) + "/"):
            return
        rows = bindings(self.agent.beliefs.query_union(f"""
SELECT ?o ?to ?jti ?a ?at ?paid WHERE {{ GRAPH <{graph}> {{
  ?o <{OWED_TO}> ?to ; <{FOR_CLAIM}> ?jti ; <{OWED_AT}> ?at .
  OPTIONAL {{ ?o <{AMOUNT_L}> ?a }} OPTIONAL {{ ?o <{DISCHARGED_AT}> ?paid }} }} }}"""))
        for row in rows:
            verdict = (f'<{DISCHARGED_AT}> "{row["paid"]}"^^xsd:dateTime' if row.get("paid")
                       else f'<{LAPSED_AT}> "{clock.now().isoformat()}"^^xsd:dateTime')
            amount = f' ; <{AMOUNT_L}> {row["a"]}' if row.get("a") else ""
            self.agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{obligations_graph(self.agent.id)}> {{
  <{row["o"]}> <{OWED_TO}> <{row["to"]}> ; <{FOR_CLAIM}> "{row["jti"]}" ;
      <{OWED_AT}> "{row["at"]}"^^xsd:dateTime{amount} ; {verdict} . }} }}""")
            self.log.info("debt for claim %s %s — the verdict stays, the want goes", row["jti"],
                          "was paid" if row.get("paid") else "LAPSED unserved")
        if rows:
            #  THE VERDICT IS WRITTEN; the prediction that the debt would lapse has come true
            #  or been overtaken, and either way it is not a forecast any more.
            self.agent.beliefs.drop_graph(graph + "/lapse")
            self.agent.desires.rebuild()
            self.agent.tell(REPREDICT)

    def start(self) -> None:
        self.endow()

    def _road(self) -> None:
        """Run the pursuit road for this agent's desire: an instance was written or moved, and
        the want under it is the road's to mint. The one thing the ledger asks of deliberation,
        and it asks rather than does — nothing here writes a want."""
        from orexis_agent_deliberation import pursuit
        pursuit.top_up(self.agent, f"{self.agent.me.uri}.no_overdue_debts")

    def endow(self) -> int:
        """A debt written while the ledger minted its own want carried no PREDICTION beside it,
        and the road derives nothing from a debt that predicts nothing: never-held structures
        arrive with the volume (an-amendment-endows-what-it-grants). Each debt with a deadline
        and no lapse in view gets the lapse the ledger would write today — wherever the debt
        is, its own graph or the untimed record of one written before debts had graphs. The
        met-test it used to carry is the DESIRE's now and is left where it lies."""
        rows = bindings(self.agent.beliefs.query_union(f"""
SELECT ?g ?o ?jti ?expires WHERE {{ GRAPH ?g {{ ?o <{FOR_CLAIM}> ?jti ; <{OREXIS}expiresAt> ?expires .
  FILTER NOT EXISTS {{ ?o <{DISCHARGED_AT}> ?paid }} FILTER NOT EXISTS {{ ?o <{LAPSED_AT}> ?lapsed }} }}
  FILTER(STRSTARTS(STR(?g), "{obligations_graph(self.agent.id)}"))
  FILTER NOT EXISTS {{ GRAPH ?p {{ ?o <{LAPSES_AT}> ?w }} }} }}"""))
        for row in rows:
            lapse = lapse_graph(self.agent.id, row["jti"])
            self.agent.beliefs.update(f"""INSERT DATA {{
  GRAPH <{lapse}> {{ <{row["o"]}> <{LAPSES_AT}> "{row["expires"]}"^^xsd:dateTime }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{lapse}> a orexis:PredictionGraph ; orexis:arrivedBy orexis:Recorded . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{lapse}> dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start "{row["expires"]}"^^xsd:dateTime ] . }} }}""")
        if rows:
            self.log.info("%d debt(s) written before the ledger predicted their lapse, endowed", len(rows))
            self.agent.desires.rebuild()
            self._road()
        return len(rows)

    def foresight(self, root: str) -> float | None:
        """How far ahead "no overdue debts" derives a want from a prediction: EVERY deadline a
        host has been given. A region desire foresees as far as its drift is worth believing;
        a debt's deadline is not a forecast but a term of the claim, and a host that only
        noticed a debt some hours before it lapsed would be a host that never planned to serve.
        Unbounded, for this root and no other. Reached through the module that holds the
        ledger, since the ledger is no longer a module of its own in the choir."""
        return float("inf") if root == f"{self.agent.me.uri}.no_overdue_debts" else None

    def obligations(self, now: datetime | None = None) -> list[Judgment]:
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

    def desires(self, now: datetime | None = None) -> list[Judgment]:
        """MY contribution to what this agent is pursuing: its debts, and no stakes.

        The half of the choir the city had no way to contribute before, which is the whole of
        #233. Lapsed is judged HERE, against the same clock the urgency uses — one reader, one
        now, so a debt cannot be maximally hot and still count as open because two clocks
        disagreed.
        """
        now = now or clock.now()
        out = []
        #  `$root` THROUGH THE BINDER, not the engine's substitutions: those reach only a
        #  variable the query projects at its top level, and this one is a token in a pattern.
        for row in bindings(self.agent.desires.query_union(
                bind(_DUTIES_Q, root=f"{self.agent.me.uri}.no_overdue_debts"))):
            demanded = row.get("presented") == "true"
            lapsed = bool(row.get("expires")) and now >= datetime.fromisoformat(row["expires"])
            out.append(Judgment(uri=row["desire"], urgency=_duty_urgency(row, now),
                              claim=row["claim"], owed_to=row["owedTo"],
                              expires=(datetime.fromisoformat(row["expires"])
                                       if row.get("expires") else None),
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
