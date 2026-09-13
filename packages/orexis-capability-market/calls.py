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

from orexis_agent_progression.ontology import beliefs_graph
from orexis_agent_progression.store import bindings

from .terms import CALL, CALLED_AT, CALLED_BY, CALLED_ON, NS
from orexis_agent_progression import clock

_XSD = "http://www.w3.org/2001/XMLSchema#"


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
    """Write (or restate) the call on this venue. Returns its IRI."""
    uri = uri_for(venue_uri)
    at = (now or clock.now()).isoformat()
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{uri}> ?p ?o }} }}
WHERE  {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{uri}> ?p ?o }} }} ;
INSERT DATA {{ GRAPH <{beliefs_graph(agent.id)}> {{
  <{uri}> a <{CALL}> ;
    <{CALLED_ON}> <{venue_uri}> ;
    <{CALLED_BY}> "{by}" ;
    <{CALLED_AT}> "{at}"^^<{_XSD}dateTime> .
}} }}""")
    return uri


def answer(agent, venue_uri: str) -> None:
    """A round opened on this venue: the call is answered and the row goes."""
    uri = uri_for(venue_uri)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{uri}> ?p ?o }} }}
WHERE  {{ GRAPH <{beliefs_graph(agent.id)}> {{ <{uri}> ?p ?o }} }}""")


def calls_of(agent, venue_uri: str | None = None) -> list[Call]:
    venue = f"FILTER(?v = <{venue_uri}>)" if venue_uri else ""
    rows = bindings(agent.beliefs.query(f"""
SELECT ?c ?v ?by ?at WHERE {{ GRAPH <{beliefs_graph(agent.id)}> {{
  ?c a <{CALL}> ; <{CALLED_ON}> ?v ; <{CALLED_BY}> ?by ; <{CALLED_AT}> ?at . {venue} }} }}"""))
    return [Call(uri=r["c"], venue=r["v"], called_by=r["by"],
                 called_at=datetime.fromisoformat(r["at"])) for r in rows]
