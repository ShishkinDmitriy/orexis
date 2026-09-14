"""PREDICTIONS: what the drifts say a reading will be, written as graphs holding during windows
(the-drift-is-sensings-and-its-result-is-predictions, #642).

A drift is a package's rule over `$elapsed` — what the world does to a reading while nobody
acts — and a reading is sensing's word, so what the drifts predict is sensing's to write. After
every reading, for each subject and property, this runs every drift the loaded packages declare
at the horizons they list beside it (`sensing:atHorizon`), the next reading's window first, and
writes one PREDICTION per horizon: a graph holding during its window — `orexis:PredictionGraph`
in the classification, its period in the periods table, as a round's is — carrying the
predicted reading keyed exactly as the present's reading is, typed with every band it may be
in, a centre where the package has one. The rate, the spread and the instrument's noise are
inside the package's text; what leaves it is bands, and where a rule types none the vocabulary
entails the one the centre falls in. A property no drift moves is predicted to stay as it reads.

The FIRST prediction is the expected next observation: its window is the freshness horizon the
module already keeps — due when the cadence in force makes it so, closed when the grace runs
out — and the window closing with no reading is what stale means, said once. The next reading
of the key rewrites the whole ladder; the first is dropped by the staleness timer when it
closes unreplaced; the sweep of #645 drops the rest once their ends have occurred, and the door
hides them before that.

The kernel still runs the same drifts at every fork for this one step (#643 is where the search
reads predictions instead), so nothing here changes a plan.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import (CLASSIFICATION_GRAPH, GRAPH_PREFIX, PERIODS_GRAPH,
                                               STATE_GRAPH, beliefs_graph)
from orexis_agent_progression.store import Raw, bind, bindings

from .sensed_writer import _slug

log = logging.getLogger("sensing.predictions")

_SOSA = "http://www.w3.org/ns/sosa/"
_PREDICTION_GRAPH = "http://example.org/orexis#PredictionGraph"
_RECORDED = "http://example.org/orexis#Recorded"
_XSD = "http://www.w3.org/2001/XMLSchema#"

#  Every drift the loaded packages declare, with the horizons each lists — `orexis:Drift` is the
#  kernel's word until #643 moves the drift's vocabulary here with its runner.
_DRIFTS_Q = """
SELECT ?drift ?construct (GROUP_CONCAT(STR(?h); SEPARATOR=" ") AS ?horizons) WHERE {
  ?drift a orexis:Drift ; sh:construct ?construct .
  OPTIONAL { ?drift sensing:atHorizon ?h }
} GROUP BY ?drift ?construct"""


def graph_of(agent_id: str, feature_id: str, observed_property: str, n: int) -> str:
    """The n-th prediction of one (feature, property) — named from the one id a process is
    handed and the key the reading is written under, as the sensed writer names its node."""
    return f"{GRAPH_PREFIX}predicted/{agent_id}/{_slug(feature_id)}_{_slug(observed_property)}/{n}"


def graphs_of(store, agent_id: str, feature_id: str, observed_property: str) -> list[str]:
    """Every prediction written for this key, first window first — asked of the classification."""
    stem = graph_of(agent_id, feature_id, observed_property, 0)[:-1]
    rows = bindings(store.query(f"""
SELECT ?g WHERE {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ ?g a <{_PREDICTION_GRAPH}> }}
  FILTER(STRSTARTS(STR(?g), "{stem}")) }}"""))
    return sorted((r["g"] for r in rows), key=lambda g: int(g.rsplit("/", 1)[-1]))


def drop(store, graphs) -> None:
    """A prediction is gone with its classification and its period — as a round is."""
    for graph in graphs:
        store.update(f"""
DELETE {{
  GRAPH <{graph}> {{ ?s ?p ?o }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> ?cp ?co }}
  GRAPH <{PERIODS_GRAPH}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }}
WHERE  {{
  {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}
  UNION {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> ?cp ?co }} }}
  UNION {{ GRAPH <{PERIODS_GRAPH}> {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }} }}""")


def write(agent, me_uri: str, subject_uri: str, observed_property: str, reading,
          horizon: float, grace: float) -> list[str]:
    """Rewrite the ladder of predictions for one key from the reading in hand. Returns the
    graphs written, first window first."""
    store = agent.beliefs
    taken = reading.result_time
    feature_id = subject_uri.rsplit("#", 1)[-1]
    drop(store, graphs_of(store, agent.id, feature_id, observed_property))
    rules = bindings(store.query(_DRIFTS_Q))
    ladder = sorted({float(h) for r in rules for h in (r.get("horizons") or "").split()
                     if float(h) > horizon})
    #  THE FIRST WINDOW is the freshness horizon: due when the cadence in force makes the next
    #  reading so, closed when the grace runs out; a device that keeps its own clock (no grace)
    #  may report any time until its age runs out.
    opens = taken + timedelta(seconds=max(0.0, horizon - grace)) if grace > 0 else taken
    windows = [(opens, taken + timedelta(seconds=horizon))]
    for h in ladder:
        windows.append((windows[-1][1], taken + timedelta(seconds=h)))
    present = [q for q in store.quads(STATE_GRAPH)
               if _is_key(q, store, subject_uri, observed_property)]
    node = str(present[0].subject) if present else None
    written = []
    for n, (opens, closes) in enumerate(windows):
        elapsed = (closes - taken).total_seconds()
        tokens = {"me": me_uri, "subject": subject_uri, "about": observed_property,
                  "want": "urn:nothing", "via": "urn:nothing", "claim": Raw('"urn:nobody"'),
                  "beliefs": beliefs_graph(agent.id), "state": STATE_GRAPH, "litres": 0.0,
                  "lands": Raw(f'"{closes.isoformat()}"^^xsd:dateTime'), "elapsed": elapsed}
        triples: list[str] = []
        for rule in rules:
            try:
                added = list(store.construct(bind(rule["construct"], **tokens), at=closes))
            except Exception as exc:                                    # noqa: BLE001
                log.error("drift %s would not run for a prediction: %s", rule["drift"], exc)
                continue
            by_node: dict[str, list] = {}
            for t in added:
                by_node.setdefault(str(t[0]), []).append(t)
            for subj, ts in by_node.items():
                facts = {t[1].value: t[2].value for t in ts if hasattr(t[2], "value")}
                if (facts.get(_SOSA + "hasFeatureOfInterest") == subject_uri
                        and facts.get(_SOSA + "observedProperty") == observed_property):
                    triples.extend(f"{t[0]} {t[1]} {t[2]} ." for t in ts)
                    node = subj
        if not triples and n > 0:
            #  A HORIZON NO DRIFT REACHES for this key — a package's ladder is its own property's,
            #  and a reading nothing moves is predicted at the next window alone.
            continue
        if not triples and node is not None:
            #  NO DRIFT MOVES IT: the reading is predicted to stay as it reads, stamped at the
            #  window's far end, its bands as the vocabulary entailed them on the present.
            for q in present:
                p = q.predicate.value
                if p in (_SOSA + "resultTime", "http://example.org/orexis/sensing#staleSince"):
                    continue
                triples.append(f"{q.subject} {q.predicate} {q.object} .")
            triples.append(f'{node} <{_SOSA}resultTime> "{closes.isoformat()}"^^<{_XSD}dateTime> .')
        if not triples:
            continue
        graph = graph_of(agent.id, feature_id, observed_property, n)
        store.update(f"""
INSERT DATA {{
  GRAPH <{graph}> {{
    {chr(10).join(triples)}
  }}
  GRAPH <{CLASSIFICATION_GRAPH}> {{ <{graph}> a <{_PREDICTION_GRAPH}> ; orexis:arrivedBy <{_RECORDED}> . }}
  GRAPH <{PERIODS_GRAPH}> {{
    <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ;
      orexis:start "{opens.isoformat()}"^^<{_XSD}dateTime> ;
      orexis:end "{closes.isoformat()}"^^<{_XSD}dateTime> ] . }} }}""")
        #  WHAT IT IS, where the rule said nothing: the band the centre falls in, entailed from
        #  the number by the vocabulary exactly as a written reading's is (#576).
        store.entail(graph, of=[node])
        written.append(graph)
    log.info("predicted the next %s of %s in %d window(s), the first closing %s",
             observed_property.rsplit("#", 1)[-1], feature_id, len(written),
             windows[0][1].isoformat(timespec="seconds"))
    return written


def drop_first(agent, subject_uri: str, observed_property: str) -> None:
    """The first prediction's window closed with no reading (#642): it is gone, and what remains
    predicts from a reading that is now stale, which the widening says honestly."""
    graphs = graphs_of(agent.beliefs, agent.id, subject_uri.rsplit("#", 1)[-1], observed_property)
    if graphs:
        drop(agent.beliefs, graphs[:1])


def _is_key(quad, store, subject_uri: str, observed_property: str) -> bool:
    """Whether a state-graph quad belongs to the reading of this subject and property."""
    subj = str(quad.subject)
    return subj in _nodes_of_key(store, subject_uri, observed_property)


_key_cache: dict = {}


def _nodes_of_key(store, subject_uri: str, observed_property: str) -> set[str]:
    rows = bindings(store.query(f"""
SELECT ?obs WHERE {{ GRAPH <{STATE_GRAPH}> {{
  ?obs sosa:hasFeatureOfInterest <{subject_uri}> ; sosa:observedProperty <{observed_property}> }} }}"""))
    return {f"<{r['obs']}>" for r in rows}
