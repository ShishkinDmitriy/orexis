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

from .terms import CALL, CALLED_AT, CALLED_BY, CALLED_ON, NS
from orexis_agent_progression import clock
from orexis_agent_progression.ontology import PUBLIC

_XSD = "http://www.w3.org/2001/XMLSchema#"



def calls_graph(agent_id: str) -> str:
    """This host's calls, as a readable name. A NAME IS FOR EYES: every reader asks the
    catalogue for `market:CallsGraph`, and this spelling is the writer's convention."""
    return f"{NS}calls/{agent_id}"


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
    """Write (or restate) the call on this venue. Returns its IRI.

    THE INSTANCE AND NOTHING ELSE, which is the ledger's shape: a host holds one standing
    desire — *no unanswered calls*, `desires.ru` — and this writes the row that desire is
    about. The want is the derivation's, minted per call in trouble, and this asks for one
    (`derived`) so a LOW arriving is a want arriving rather than a want on the next tick.
    A capability that asks for a derivation is not minting.

    It carried a met-test of its OWN for one change (#765), because the host answered "is
    this call met" through the choir with a measure and removing the measure took the answer
    with it. A per-instance met-test is a desire per instance, which is the level this repo
    drew and struck: the instance is the want's grain, not the desire's.
    """
    from orexis_agent_deliberation import pursuit

    uri = uri_for(venue_uri)
    graph = calls_graph(agent.id)
    at = (now or clock.now()).isoformat()
    agent.beliefs.classify(graph, f"{NS}CallsGraph", OREXIS + "Received", agent.me.uri)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }}
WHERE  {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }} ;
INSERT DATA {{ GRAPH <{graph}> {{
  <{uri}> a <{CALL}> ;
    <{CALLED_ON}> <{venue_uri}> ;
    <{CALLED_BY}> "{by}" ;
    <{CALLED_AT}> "{at}"^^<{_XSD}dateTime> .
}} }}""")
    pursuit.derived(agent)
    return uri


def answer(agent, venue_uri: str) -> None:
    """A round opened on this venue: the call is answered and the row goes.

    And the want with it, by the derivation rather than by hand: a want exists because its
    desire read unmet, so the same rows withdraw it — the call is gone, the standing desire
    reads met, and `derived` takes the want down.
    """
    from orexis_agent_deliberation import pursuit

    uri = uri_for(venue_uri)
    graph = calls_graph(agent.id)
    agent.beliefs.update(f"""
DELETE {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }}
WHERE  {{ GRAPH <{graph}> {{ <{uri}> ?p ?o }} }}""")
    pursuit.derived(agent)


def calls_of(agent, venue_uri: str | None = None) -> list[Call]:
    venue = f"FILTER(?v = <{venue_uri}>)" if venue_uri else ""
    rows = bindings(agent.beliefs.query(f"""
SELECT ?c ?v ?by ?at WHERE {{ GRAPH ?g {{
  ?c a <{CALL}> ; <{CALLED_ON}> ?v ; <{CALLED_BY}> ?by ; <{CALLED_AT}> ?at . {venue} }} }}""",
        agent.beliefs.graphs_of(f"{NS}CallsGraph")))
    return [Call(uri=r["c"], venue=r["v"], called_by=r["by"],
                 called_at=datetime.fromisoformat(r["at"])) for r in rows]
