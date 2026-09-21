"""A call — the want a participant's LOW sources on a host. One writer, one reader.

`hosting.on_participant_event` used to announce a round on a LOW after checking a cooldown
and a dict. A LOW is now what makes a round WANTED: one `market:Call` per venue in the host's
own graph, written on the verdict, retracted when a round opens there, and pursued by the
search like any other want — Offer, or acquire upstream then Offer when the vessel is dry.
See knowledge/domain/call.md and a-round-is-a-fact-and-offering-is-an-action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import bindings

from .terms import CALL, CALLED_AT, CALLED_BY, CALLED_ON, HAS_ROUND, NS
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import PUBLIC

_XSD = "http://www.w3.org/2001/XMLSchema#"


def _sparql_literal(text: str) -> str:
    """One select as a SPARQL literal — long-quoted, since it spans lines and carries braces."""
    assert '"""' not in text, "a select carrying a long quote cannot be written as one"
    return '"""' + text + '"""'


def calls_graph(agent_id: str) -> str:
    """This host's calls, as a readable name. A NAME IS FOR EYES: every reader asks the
    catalogue for `market:CallsGraph`, and this spelling is the writer's convention."""
    return f"{NS}calls/{agent_id}"


#  THE CALL'S OWN MET-TEST, written beside it. Rows are the VIOLATION — this venue has no
#  round — which is what `orexis:unmetWhen` means everywhere else. `$this` is bound to the
#  asking agent and goes unread: a host holds calls only on venues it hosts, so the graph
#  the select reads is already scoped to whose it is.
#
#  IT NAMES NO WORLD (#666): an unqualified pattern reads whatever the runner hands it, which
#  is public knowledge, this agent's records and the world being judged — so a round that only
#  a plan's Offer put there answers the call exactly as a standing one does. That is the whole
#  reason a host can plan to open a round at all, and it used to be a UNION over two named
#  graphs inside the measure the host answered the choir with.
_UNMET = f"""SELECT ?venue WHERE {{
  <%s> <{CALLED_ON}> ?venue .
  FILTER NOT EXISTS {{ ?venue <{HAS_ROUND}> ?round }}
}}"""


@dataclass(frozen=True)
class Call:
    uri: str
    venue: str
    called_by: str
    called_at: datetime


def uri_for(venue_uri: str) -> str:
    #  ONE PER VENUE, minted from the venue's own IRI — a second LOW while a call stands
    #  restates it rather than raising a second, exactly as an open round absorbed one.
    return f"{NS}call_{venue_uri.rsplit('#', 1)[-1].rsplit('/', 1)[-1]}"


def call(agent, venue_uri: str, by: str, now: datetime | None = None) -> str:
    """Write (or restate) the call on this venue, with its met-test. Returns its IRI."""
    uri = uri_for(venue_uri)
    graph = calls_graph(agent.id)
    at = (now or clock.now()).isoformat()
    agent.beliefs.classify(graph, f"{NS}CallsGraph", OREXIS + "Received", agent.me.uri)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o . <{uri}.unmet> ?q ?r }} }}
WHERE  {{ GRAPH <{graph}> {{ <{uri}> ?p ?o . OPTIONAL {{ <{uri}.unmet> ?q ?r }} }} }} ;
INSERT DATA {{ GRAPH <{graph}> {{
  <{uri}> a <{CALL}> ;
    <{CALLED_ON}> <{venue_uri}> ;
    <{CALLED_BY}> "{by}" ;
    <{CALLED_AT}> "{at}"^^<{_XSD}dateTime> ;
    <{OREXIS}unmetWhen> <{uri}.unmet> .
  <{uri}.unmet> <http://www.w3.org/ns/shacl#select> {_sparql_literal(_UNMET % uri)} ;
    <http://www.w3.org/ns/shacl#prefixes> <http://example.org/orexis#> .
}} }}""")
    #  AND ASK FOR THE PROJECTION, as the ledger does when it writes a debt: the desire
    #  modality is a VIEW of these graphs, and the planner compiles its shapes from that view,
    #  so a call written after boot is invisible to a search until the view is rebuilt — its
    #  met-test with it, which reads unmet in every world including the one a round answers.
    #  A capability that asks for a rebuild is not minting.
    agent.desires.rebuild()
    return uri


def answer(agent, venue_uri: str) -> None:
    """A round opened on this venue: the call is answered and the row goes, met-test with it."""
    uri = uri_for(venue_uri)
    graph = calls_graph(agent.id)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o . <{uri}.unmet> ?q ?r }} }}
WHERE  {{ GRAPH <{graph}> {{ <{uri}> ?p ?o . OPTIONAL {{ <{uri}.unmet> ?q ?r }} }} }}""")
    agent.desires.rebuild()      # the call is answered, and the view must stop offering it


def calls_of(agent, venue_uri: str | None = None) -> list[Call]:
    venue = f"FILTER(?v = <{venue_uri}>)" if venue_uri else ""
    rows = bindings(agent.beliefs.query(f"""
SELECT ?c ?v ?by ?at WHERE {{ GRAPH ?g {{
  ?c a <{CALL}> ; <{CALLED_ON}> ?v ; <{CALLED_BY}> ?by ; <{CALLED_AT}> ?at . {venue} }} }}""",
        agent.beliefs.graphs_of(f"{NS}CallsGraph")))
    return [Call(uri=r["c"], venue=r["v"], called_by=r["by"],
                 called_at=datetime.fromisoformat(r["at"])) for r in rows]
