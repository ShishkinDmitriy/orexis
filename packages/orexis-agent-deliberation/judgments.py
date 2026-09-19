"""The judgments in the store, as SPARQL and nothing else — and the WITNESS, which is what one
result of one judgment says.

`judge_desires` hands the engine's own rows here and they are written as judgments;
`derive_wants` reads them back with one SELECT, and so does every other reader of what a
desire read: the judgment is written down so that nobody judges twice. No Python object stands for a judgment in
between — the sovereign's question, and the answer is no: the next function reads the
graph. This module owns the judgment graph: its name for eyes (`judgments/<holder>`), its
classification with owner, and that a holder's judgments are replaced whole on every run,
exactly as `Wants` owns the pursued graphs. A reader that means the graph asks its class.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from orexis_agent_progression import clock
from orexis_agent_progression.store import NAMESPACES, answer, bind, bindings, rows

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


@dataclass(frozen=True)
class Witness:
    """One way a desire is failing, and when it first does: the focus node that failed, the
    constraint it failed, what that constraint is about where its block says, and the instant.
    A universal is refuted by a witness, and the want minted under it is the universal
    instantiated at that witness (one-road-derives-every-want).

    It is one `sh:result` of one judgment, read back — which is why it lives beside them."""

    instance: str
    constraint: str
    about: str | None
    at: datetime


#  WHAT A WANT NARROWS ITS DESIRE TO: the desire it was derived from, what it is about, and
#  the one node its met-test targets where it has one. A want is not judged — a judgment is
#  about a DESIRE — so a want's witnesses are its desire's, kept to the rows the want was
#  minted from. Nothing for a node that is no want, which is then a desire and takes its own.
_NARROWS_Q = """
SELECT ?desire (GROUP_CONCAT(STR(?about); separator=" ") AS ?abouts) ?target WHERE {
  GRAPH ?g { $node prov:wasDerivedFrom ?desire .
             OPTIONAL { $node orexis:about ?about }
             OPTIONAL { $node orexis:metWhen ?shape . ?shape sh:targetNode ?target } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:WantGraph } }
GROUP BY ?desire ?target"""


def witnesses_of(engine: ox.Store, node: str) -> list[Witness]:
    """Every (instance, constraint) under which `node` was judged unmet at a FORESEEN instant,
    each at the earliest instant it was — read off the judgments, and off nothing else.

    ONLY THE JUDGE TAKES PREDICTIONS INTO ACCOUNT. `judge_desires` enumerates the states — the
    present, then every instant a prediction reaches — and judges the desire at each; what it
    read is written down, and this reads it. It used to re-run the compiled met-test at every
    prediction start on every call, which is the same question asked twice and answered by two
    paths. So a crossing is what the last judging found: during a pass that is what is true
    now, since `pursuit` judges before it asks, and whoever moves a premise says so — the
    ledger asks the road when a claim arrives and when a debt is paid.

    A WANT TAKES ITS DESIRE'S, NARROWED. A judgment is about a desire; a want is the desire
    instantiated at a cluster of its results, so the want's witnesses are exactly those rows —
    kept to what it is about and, where its met-test names one node, to that node. Which is
    what compiling the want's own narrowed shape used to compute, from the same facts.

    The present is excluded, as it always was: a desire unmet NOW is pursued as itself, and a
    crossing is a thing in the future.
    """
    narrowed = bindings(answer(engine, bind(_NARROWS_Q, node=node)))
    desire = narrowed[0]["desire"] if narrowed else node
    abouts = set(narrowed[0]["abouts"].split()) if narrowed and narrowed[0].get("abouts") else set()
    target = narrowed[0].get("target") if narrowed else None
    seen: dict[tuple[str, str], Witness] = {}
    for judged in find_judgments(engine).values():
        rows = [r for r in judged if r["desire"] == desire and r.get("at")
                and r["met"] != "true" and r.get("focus")
                and (target is None or r["focus"] == target)
                and (not abouts or not r.get("about") or r["about"] in abouts)]
        for r in sorted(rows, key=lambda r: r["at"]):
            seen.setdefault((r["focus"], r["k"]), Witness(
                instance=r["focus"], constraint=r["k"], about=r.get("about"),
                at=datetime.fromisoformat(r["at"])))
    return sorted(seen.values(), key=lambda w: (w.at, w.instance, w.constraint))


def _term(term) -> str | None:
    """The engine's term as the text that writes it back, or None for a blank node, which no
    other graph could point at."""
    if term is None or isinstance(term, ox.BlankNode):
        return None
    return str(term)                                        # its N-Triples form
