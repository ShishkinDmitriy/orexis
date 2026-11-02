"""`chat`: the chats an agent is in, read off the common beliefs — each its channel, the people in it by the names
they go by, the agents in it by the names they answer to, and the kinds of graph its model may query — and whether words name
an agent.

A CHAT IS WHO SPEAKS WITH WHOM THROUGH WHAT (knowledge/domain/speech/chat.md): `speech:Chat`, its participants and
its one channel, of whatever kind a transport carries. An agent answers to its local id, its IRI's local name and the
name it goes by, `schema:name`, so a person in a group asks one by any of them, as a word of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.ontology import BELIEF, SELF_GRAPH, local_of
from agent.store import graphs_of, rows

#  EVERY CHAT THE AGENT IS IN, a row per participant: its channel, and who else is in it, a person by its name.
_CHATS_Q = """
SELECT ?chat ?channel ?who ?kind ?name ?id WHERE {
  ?me a orexis:Self . ?chat a speech:Chat ; speech:participant ?me , ?who ; speech:channel ?channel .
  ?who a ?kind . VALUES ?kind { schema:Person orexis:Agent }
  OPTIONAL { ?who schema:name ?name } OPTIONAL { ?who orexis:localId ?id } } ORDER BY ?chat ?who"""

#  WHAT EACH CHAT'S MODEL MAY QUERY: the kinds of graph it reads (knowledge/domain/speech/chat.md).
_READS_Q = "SELECT ?chat ?kind WHERE { ?chat a speech:Chat ; speech:reads ?kind } ORDER BY ?chat ?kind"


@dataclass(frozen=True)
class Chat:
    iri: str
    channel: str
    people: tuple[tuple[str, str], ...]          # (IRI, name)
    agents: tuple[tuple[str, tuple[str, ...]], ...]  # (IRI, the names it answers to)
    reads: tuple[str, ...] = ()                  # the kinds of graph its model may query, none where it states none

    def person(self, sender: str | None) -> tuple[str, str] | None:
        """Who wrote: the sender the channel told, where they are in the chat, or the chat's one person."""
        if sender is not None:
            return next((p for p in self.people if p[0] == sender), None)
        return self.people[0] if len(self.people) == 1 else None


def chats_of(store) -> list[Chat]:
    """Every chat the self is in, read off the common beliefs beside its self graph."""
    found: dict[str, dict] = {}
    graphs = [*graphs_of(store, BELIEF, common=True), *graphs_of(store, SELF_GRAPH)]
    for r in rows(store, _CHATS_Q, graphs):
        chat = found.setdefault(r["chat"], {"channel": r["channel"], "people": {}, "agents": {}})
        if r["kind"].endswith("Person"):
            chat["people"][r["who"]] = r.get("name") or local_of(r["who"])
        else:
            chat["agents"][r["who"]] = tuple(dict.fromkeys(n for n in (r.get("id"), local_of(r["who"]), r.get("name")) if n))
    reads: dict[str, list[str]] = {}
    for r in rows(store, _READS_Q, graphs):
        reads.setdefault(r["chat"], []).append(r["kind"])
    return [Chat(iri, c["channel"], tuple(sorted(c["people"].items())), tuple(sorted(c["agents"].items())),
                 tuple(sorted(reads.get(iri, ()))))
            for iri, c in sorted(found.items())]


def named(text: str, names) -> bool:
    """Whether `text` names an agent by one of `names`, as a word of its own."""
    return any(re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", text, re.I) for n in names)
