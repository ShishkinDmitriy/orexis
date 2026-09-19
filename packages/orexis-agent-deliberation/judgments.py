"""The judgments in the store, as SPARQL and nothing else.

`judge_desires` hands the engine's own rows here and they are written as judgments;
`derive_wants` reads them back with one SELECT. No Python object stands for a judgment in
between — the sovereign's question, and the answer is no: the next function reads the
graph. This module owns the judgment graph: its name for eyes (`judgments/<holder>`), its
classification with owner, and that a holder's judgments are replaced whole on every run,
exactly as `Wants` owns the pursued graphs. A reader that means the graph asks its class.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from orexis_agent_progression import clock
from orexis_agent_progression.store import NAMESPACES, bind, rows

from .ontology import DELIBERATION, judgments_graph

JUDGMENT_GRAPH = DELIBERATION + "JudgmentGraph"

#  EVERY JUDGMENT HELD AND WHOSE IT IS, one row per result — a met one has a row with no
#  focus. The graph says whose, so the text joins the catalogue and is handed no default
#  graph: a judgment is written per holder and the wants it implies are written where that
#  holder's belong.
JUDGMENTS_Q = """
SELECT ?holder ?desire ?at ?met ?focus ?about ?k WHERE {
  GRAPH ?g { ?j a deliberation:Judgment ; deliberation:judges ?desire ; sh:conforms ?met .
    OPTIONAL { ?j orexis:holdsAt ?at }
    OPTIONAL { ?j sh:result ?r . ?r sh:focusNode ?focus ; deliberation:constraint ?k .
               OPTIONAL { ?r orexis:about ?about } } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a deliberation:JudgmentGraph ;
               orexis:beliefsOf ?holder } }"""

#  THE HOLDER'S STANDING JUDGMENT GRAPHS, asked of the catalogue by class and owner — what a
#  run replaces, whatever each is called.
_STANDING_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a deliberation:JudgmentGraph ; orexis:beliefsOf $holder } }
ORDER BY ?g"""


def save_judgments(store: ox.Store, holder: str,
                   judged: list[tuple[str, datetime | None, bool, list[dict]]]) -> None:
    """Replace `holder`'s judgments with these — `(desire, instant or None for the present,
    met, the engine's rows)` each — and say what the graph is.

    ONE GRAPH, WRITTEN WHOLE: a judgment is a conclusion about a situation, and the
    situation has moved by the next run, so nothing of the last run is worth keeping
    beside this one. Each judgment is named for its desire and its instant, so the same
    situation writes the same text — which is what a snapshot of the store is held to. A
    row is the compiled select's own binding (`this`, `_constraint`, `_about`,
    `_offending`) as the engine's terms, and the offending value is written back AS THE
    TERM it was — a bare string would lose whether it was an IRI or a typed literal.

    ONE UPDATE OVER THE ENGINE, and the writer names nothing it did not create: the
    holder's standing judgment graphs are asked of the catalogue by class and owner and
    dropped, whatever they are called; the new graph is named for its holder, since a name
    is for eyes and the holder is the one thing a desire says about whose it is; the
    catalogue that describes it is found by its own row; and every kind the vocabulary puts
    a judgment graph beneath is written on the row from the graphs the catalogue types as
    the vocabulary's — one `rdfs:subClassOf` step, since the closure is materialised at
    genesis and one step is every step (one-graph-both-engines-read) — so a text asks `?g a
    orexis:WorkingGraph` and walks no path. The graph and its description land together or
    not at all."""
    standing = [row["g"] for row in rows(store, _STANDING_Q, holder=holder)]
    graph = judgments_graph(holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1])
    now = clock.now().isoformat()
    blocks = []
    for desire, at, met, results in judged:
        node = desire + ".judgment" + (at.strftime(".%Y%m%dT%H%M%SZ") if at is not None else "")
        when = f' ; orexis:holdsAt "{at.isoformat()}"^^xsd:dateTime' if at is not None else ""
        results = "".join(
            f" ;\n      sh:result [ a sh:ValidationResult ; sh:focusNode {r['this']} ;"
            f" deliberation:constraint {int(r['_constraint'].value)}"
            + (f" ; orexis:about {r['_about']}" if "_about" in r else "")
            + (f" ; sh:value {term}" if (term := _term(r.get("_offending"))) else "") + " ]"
            for r in results)
        blocks.append(f"  <{node}> a deliberation:Judgment ; deliberation:judges <{desire}>{when} ;\n"
                      f'      prov:generatedAtTime "{now}"^^xsd:dateTime ;\n'
                      f"      sh:conforms {'true' if met else 'false'}{results} .")
    dropped = "".join(
        f"DROP SILENT GRAPH <{g}> ;\n"
        f"DELETE {{ GRAPH ?cat {{ <{g}> ?p ?o }} }} WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{g}> ?p ?o }} }} ;\n"
        for g in standing)
    store.update(dropped + f"""
INSERT {{
  GRAPH <{graph}> {{
{chr(10).join(blocks)}
  }}
  GRAPH ?cat {{ <{graph}> a deliberation:JudgmentGraph ; orexis:arrivedBy orexis:Derived ; orexis:beliefsOf <{holder}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ deliberation:JudgmentGraph rdfs:subClassOf ?kind }} }}""", prefixes=NAMESPACES)


def find_judgments(engine: ox.Store) -> dict[str, list[dict]]:
    """Every judgment's rows, by HOLDER — the judgment graphs asked by class and by whose they
    are, in the text's own `GRAPH` clauses. Each row: `desire`, `at` (absent for the present),
    `met` (`"true"`/`"false"`), and per result `focus`, `about`, `k`."""
    from orexis_agent_progression.store import rows

    out: dict[str, list[dict]] = {}
    for row in rows(engine, JUDGMENTS_Q):
        out.setdefault(row["holder"], []).append(row)
    return out


def _term(term) -> str | None:
    """The engine's term as the text that writes it back, or None for a blank node, which no
    other graph could point at."""
    if term is None or isinstance(term, ox.BlankNode):
        return None
    return str(term)                                        # its N-Triples form
