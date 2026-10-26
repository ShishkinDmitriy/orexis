"""What speech says happened — the events its signals carry, and which are history.

A DOCUMENT FOR A PEER, `Told`, is what a transport carries to it. And every STATEMENT is history, an event in the
journal (`agent/journal.py`) in speech's words: `speech:Said`, each graph of a document the agent said, with every
agent it was told to (`speech:to`); and `speech:Heard`, each graph of a document a peer said to it. Each names the
statement (`speech:statement`) and carries what it said, its triples copied, and what kind of graph it says it is,
so the journal holds the exchange between two agents in the words they spoke it in — a question, an answer, a
commitment — and this module spells none of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

SPEECH = "http://example.org/orexis/speech#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


@dataclass(frozen=True)
class Told:
    """A document for a peer: the agent it is `to`, and the document as TriG bytes."""
    to: str
    document: bytes


@dataclass(frozen=True)
class Said:
    """A statement the agent said at `at`: the graph, the agents it was told to, the kinds it says it is and what it
    says, its triples."""
    statement: str
    to: tuple = ()
    at: datetime | None = None
    kinds: tuple = ()
    said: tuple = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the statement, whom it was told to, and what it said."""
        return [ox.Triple(node, _TYPE, ox.NamedNode(SPEECH + "Said")),
                *(ox.Triple(node, ox.NamedNode(SPEECH + "to"), ox.NamedNode(a)) for a in self.to),
                *_statement(node, self)]


@dataclass(frozen=True)
class Heard:
    """A statement a peer said to the agent, heard at `at`: the graph, the kinds it says it is and what it says."""
    statement: str
    at: datetime | None = None
    kinds: tuple = ()
    said: tuple = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the statement, and what it said."""
        return [ox.Triple(node, _TYPE, ox.NamedNode(SPEECH + "Heard")), *_statement(node, self)]


def _statement(node: ox.NamedNode, event) -> list[ox.Triple]:
    graph = ox.NamedNode(event.statement)
    return [ox.Triple(node, ox.NamedNode(SPEECH + "statement"), graph),
            *(ox.Triple(graph, _TYPE, ox.NamedNode(k)) for k in event.kinds), *event.said]
