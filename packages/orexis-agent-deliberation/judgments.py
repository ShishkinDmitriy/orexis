"""The judgments in the store, as SPARQL and nothing else.

`judge_desires` hands the engine's own rows here and they are written as judgments;
`derive_wants` reads them back with one SELECT. No Python object stands for a judgment in
between — the sovereign's question, and the answer is no: the next function reads the
graph. This module owns the judgment graph: its name for eyes (`judgments/<agent>`), its
classification with owner, and that it is replaced whole on every run, exactly as `Wants`
owns the pursued graphs. A reader that means the graph asks its class.
"""

from __future__ import annotations

import json
from datetime import datetime

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import CLASSIFICATION_GRAPH
from orexis_agent_progression.store import bindings

from .ontology import DELIBERATION, judgments_graph

JUDGMENT_GRAPH = DELIBERATION + "JudgmentGraph"

#  EVERY JUDGMENT HELD, one row per result — a met one has a row with no focus.
JUDGMENTS_Q = """
SELECT ?desire ?at ?met ?focus ?about ?k WHERE {
  ?j a deliberation:Judgment ; deliberation:judges ?desire ; sh:conforms ?met .
  OPTIONAL { ?j orexis:holdsAt ?at }
  OPTIONAL { ?j sh:result ?r . ?r sh:focusNode ?focus ; deliberation:constraint ?k .
             OPTIONAL { ?r orexis:about ?about } } }"""


def save_judgments(store, agent_id: str, holder: str,
                   judged: list[tuple[str, datetime | None, bool, list[dict]]]) -> None:
    """Replace the agent's judgments with these — `(desire, instant or None for the present,
    met, the engine's rows)` each — and say what the graph is.

    ONE GRAPH, WRITTEN WHOLE: a judgment is a conclusion about a situation, and the
    situation has moved by the next run, so nothing of the last run is worth keeping
    beside this one. Each judgment is named for its desire and its instant, so the same
    situation writes the same text — which is what a snapshot of the store is held to. A
    row is the compiled select's own binding (`this`, `_constraint`, `_about`,
    `_offending`), and the offending value is rendered back AS THE TERM it was — a bare
    string would lose whether it was an IRI or a typed literal."""
    graph = judgments_graph(agent_id)
    now = clock.now().isoformat()
    blocks = []
    for desire, at, met, rows in judged:
        node = desire + ".judgment" + (at.strftime(".%Y%m%dT%H%M%SZ") if at is not None else "")
        when = f' ; orexis:holdsAt "{at.isoformat()}"^^xsd:dateTime' if at is not None else ""
        results = "".join(
            f" ;\n      sh:result [ a sh:ValidationResult ; sh:focusNode <{r['this']['value']}> ;"
            f" deliberation:constraint {int(r['_constraint']['value'])}"
            + (f" ; orexis:about <{r['_about']['value']}>" if "_about" in r else "")
            + (f" ; sh:value {term}" if (term := _term(r.get("_offending"))) else "") + " ]"
            for r in rows)
        blocks.append(f"  <{node}> a deliberation:Judgment ; deliberation:judges <{desire}>{when} ;\n"
                      f'      prov:generatedAtTime "{now}"^^xsd:dateTime ;\n'
                      f"      sh:conforms {'true' if met else 'false'}{results} .")
    store.drop_graph(graph)
    store.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{
    <{graph}> a deliberation:JudgmentGraph ; orexis:arrivedBy orexis:Derived ;
        orexis:beliefsOf <{holder}> . }}
}}""")


def find_judgments(store) -> list[dict]:
    """Every judgment's rows, from the judgment graph asked by class: `desire`, `at` (absent
    for the present), `met` (`"true"`/`"false"`), and per result `focus`, `about`, `k`."""
    graphs = store.graphs_of(JUDGMENT_GRAPH)
    return bindings(store.query_over(JUDGMENTS_Q, *graphs)) if graphs else []


def _term(binding: dict | None) -> str | None:
    if not binding:
        return None
    if binding["type"] == "uri":
        return f"<{binding['value']}>"
    if binding["type"] != "literal":
        return None
    text = json.dumps(binding["value"])
    if binding.get("datatype"):
        return f"{text}^^<{binding['datatype']}>"
    if binding.get("xml:lang"):
        return f"{text}@{binding['xml:lang']}"
    return text
