"""`answer`: what an agent says back to a peer's question (knowledge/domain/coordination/answer.md).

**ONLY UNDER A SHARED CONSTRAINT.** A question names its constraint; an agent that does not hold it says
nothing at all, which the asker takes as silence — need-to-know, in the distributed-constraint shape,
where values cross only over the constraints that link two agents.

**ONLY WHAT MEETS.** The answerer's own holdings under the constraint at the same values of its key over
periods that overlap an asked one, and none other: an answer never carries a fact outside the asked key,
values and periods. Said even where nothing meets — an empty answer is the cost of no conflict — in the
answer's graph, named for the answerer, the asker and the constraint, so it is replaced each time the
question is said again.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from agent.ontology import RECEIVED, SELF_GRAPH
from agent.store import Raw, catalogue_of, graphs_of, rows

from .holdings import _heard, _said, _violates, holdings
from .ontology import ANSWER, ANSWER_GRAPH, COORDINATION, CONSTRAINT_GRAPH, answer_graph

#  WHAT A QUESTION HEARD SAYS: who asks, and under which constraint; only one that arrived from a peer.
_QUESTION_Q = """
SELECT ?asker ?constraint WHERE { GRAPH $cat { $graph orexis:arrivedBy $received }
  GRAPH $graph { ?q a coordination:Question ; coordination:asks ?asker ; coordination:over ?constraint } } LIMIT 1"""
_HOLDS_Q = "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds $constraint . BIND($constraint AS ?c) } LIMIT 1"


def answer(store: ox.Store, me: str, question: str, at: datetime) -> tuple[str, ox.Store] | None:
    """The answer the self `me` of `store` says to the question heard in the graph `question`, with the
    peer it is to — or None where the question is no peer's, or names a constraint the agent does not hold."""
    cat = catalogue_of(store)
    found = rows(store, _QUESTION_Q, (), cat=Raw(f"<{cat}>"), graph=Raw(f"<{question}>"), received=RECEIVED) if cat else []
    if not found:
        return None
    asker, constraint = found[0]["asker"], found[0]["constraint"]
    if asker == me or not rows(store, _HOLDS_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *graphs_of(store, SELF_GRAPH)],
                                constraint=constraint):
        return None
    asked = _heard(store, question)
    meeting = [h for h in holdings(store, constraint, at) if any(_violates(store, constraint, h, q) for q in asked)]
    graph = answer_graph(me, asker, constraint)
    about = [("http://www.w3.org/1999/02/22-rdf-syntax-ns#type", ox.NamedNode(ANSWER)),
             (COORDINATION + "answers", ox.NamedNode(question)), (COORDINATION + "answeredBy", ox.NamedNode(me)),
             (COORDINATION + "over", ox.NamedNode(constraint))]
    return asker, _said(graph, ANSWER_GRAPH, graph, about, meeting)
