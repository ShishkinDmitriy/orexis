"""The judgments in the store: every desire's, at the present and at every foreseen instant.

A collection over stored rows, so it is handed a store and nothing else (a-collection-over-
stored-rows-is-handed-a-store). It owns the judgment graph — its name for eyes, its
classification, that it is replaced whole — exactly as `Wants` owns the pursued graphs, and
a reader asks it by class. What it holds is what `judge_desires` wrote and `derive_wants`
reads; the choir's half of a judgment, the urgency, is `agent.judgments`' until the two fold.
"""

from __future__ import annotations

import logging
from datetime import datetime

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH, OREXIS
from orexis_agent_progression.store import bindings

from .ontology import DELIBERATION, judgments_graph
from .verdict import Result, Verdict

log = logging.getLogger("verdicts")


class Verdicts:
    """Every judgment this agent's store holds, by the desire judged."""

    def __init__(self, store):
        self._store = store

    def save(self, agent_id: str, holder: str, verdicts: list[Verdict]) -> None:
        """Replace the agent's judgments with these, and say what the graph is.

        ONE GRAPH, WRITTEN WHOLE: a judgment is a conclusion about a situation, and the
        situation has moved by the next run, so nothing of the last run is worth keeping
        beside this one. Each judgment is named for its desire and its instant, so the same
        situation writes the same text — which is what a snapshot of the store is held to."""
        graph = self.graph_of(agent_id)
        now = clock.now().isoformat()
        blocks = []
        for v in verdicts:
            node = self.node_of(v)
            when = f' ; orexis:holdsAt "{v.holds_at.isoformat()}"^^xsd:dateTime' if v.holds_at is not None else ""
            results = "".join(
                f" ;\n      sh:result [ a sh:ValidationResult ; sh:focusNode <{r.focus}> ; deliberation:constraint {r.constraint}"
                + (f" ; orexis:about <{r.about}>" if r.about else "")
                + (f" ; sh:value {r.value}" if r.value else "") + " ]"
                for r in v.results)
            blocks.append(f"  <{node}> a deliberation:Judgment ; deliberation:judges <{v.desire}>{when} ;\n"
                          f'      prov:generatedAtTime "{now}"^^xsd:dateTime ;\n'
                          f"      sh:conforms {'true' if v.met else 'false'}{results} .")
        self._store.drop_graph(graph)
        self._store.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{
    <{graph}> a deliberation:JudgmentGraph ; orexis:arrivedBy orexis:Derived ;
        orexis:beliefsOf <{holder}> . }}
}}""")

    def find_all(self) -> list[Verdict]:
        """Every judgment held, the present's first and then by instant, by desire."""
        graphs = self._store.graphs_of(DELIBERATION + "JudgmentGraph")
        if not graphs:
            return []
        rows = bindings(self._store.query_over("""
SELECT ?d ?at ?met ?focus ?about ?k ?value WHERE {
  ?j a deliberation:Judgment ; deliberation:judges ?d ; sh:conforms ?met .
  OPTIONAL { ?j orexis:holdsAt ?at }
  OPTIONAL { ?j sh:result ?r . ?r sh:focusNode ?focus ; deliberation:constraint ?k .
             OPTIONAL { ?r orexis:about ?about } OPTIONAL { ?r sh:value ?value } } }""", *graphs))
        by_node: dict[tuple, dict] = {}
        for r in rows:
            at = datetime.fromisoformat(r["at"]) if r.get("at") else None
            entry = by_node.setdefault((r["d"], at), {"met": r["met"] == "true", "results": []})
            if r.get("focus"):
                entry["results"].append(Result(focus=r["focus"], about=r.get("about"),
                                               constraint=int(r["k"]), value=r.get("value")))
        return sorted((Verdict(desire=d, holds_at=at, met=e["met"],
                               results=tuple(sorted(set(e["results"]), key=lambda x: (x.focus, x.constraint))))
                       for (d, at), e in by_node.items()),
                      key=lambda v: (v.desire, v.holds_at is not None, v.holds_at or datetime.min))

    def find_all_by_desire(self, desire: str) -> list[Verdict]:
        return [v for v in self.find_all() if v.desire == desire]

    @staticmethod
    def node_of(verdict: Verdict) -> str:
        """A judgment's name: the desire's, `.judgment`, and the instant where it is about one."""
        tail = verdict.desire + ".judgment"
        if verdict.holds_at is not None:
            tail += "." + verdict.holds_at.strftime("%Y%m%dT%H%M%SZ")
        return tail

    @staticmethod
    def graph_of(agent_id: str) -> str:
        return judgments_graph(agent_id)
