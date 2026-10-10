"""`believe`: what the agent holds true of a subject, written of the state an observation was judged
in — its subject belief, replacing the one before it whole (knowledge/domain/sensing/subject-belief.md,
#944).

**THE RULE JUDGES, AND THIS WRITES.** Which state a subject is in is one rule's of this layer
(`rules.ttl`), concluded as a revision of the observation, `sensing:judged`, beside the subject belief
it will replace, which the deliberator hands it as a conclusion the agent drew of the present. So the
hold is written once, and nothing here compares a number with a bound. What is written here is that
judgment in the words of the domain that owns the property: for the subject — the observation's
feature of interest, or what that is a sample of, whichever states the operating range judged — its
state in the predicate the property's `sensing:stateAs` names: `:bed climate:soil climate:Dry`. The
state alone: the number is the observation's, and the readers of a number — prediction, and a
command sizing its step when it is taken — read it there. One graph per subject and property, a `sensing:SubjectBeliefGraph`, derived and the
agent's, holding over the observation's own period, so it ends with the observation — a silence
included — and lasts in a volume lived in.

**REPLACED WHOLE, NEVER RE-DERIVED.** A rule concludes and never deletes, and a subject belief is a
conclusion one of whose premises is the subject belief before it: so it is written rather than
derived, kept beside testimony because a premise of it is gone, and replacing it is this writer's act
and nobody else's — the graph holding the key's subject belief before, found by its content and never
by its name, is forgotten and the new one written. One made of a LATER observation is never replaced
by one of an earlier: the readings one message carries are judged and written in turn, each beside
the subject belief the one before it made, and a revision a budget cut short, continued after a later
reading of the key was believed, writes nothing.

**ONLY OF AN OBSERVATION.** A graph that is no `sensing:ObservationGraph` makes no subject belief — a
prediction carrying the observation in hand forward carries its judgment too, and a predicted number
is not believed here.

**CALLED, NOT CALLING.** Sensing's part calls it for every graph the deliberator says it revised; a
test calls it after `revise`. The graphs written are answered, and the part says them to nobody, as a
silence is said to nobody: nothing in the mind reads a subject belief yet.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import PUBLIC, local_of
from agent.store import NAMESPACES, Raw, catalogue_of, entry, forget_graph, graphs_of, revisions_of, rows, update

from .ontology import DERIVED, SUBJECT_BELIEF_GRAPH, subject_belief_graph

log = logging.getLogger("believe")

#  THE OBSERVATION'S PERIOD, off its row — and no row where the graph is no observation.
_OBSERVATION_Q = """
SELECT ?start ?end WHERE {
  GRAPH $cat { $graph a sensing:ObservationGraph ; dcterms:temporal ?p .
               OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } LIMIT 1"""

#  WHAT THE OBSERVATION WAS JUDGED, read over the graph, its revisions and what the world states: the
#  subject whose operating range was judged, the property, the domain's two predicates, the state and
#  the reading.
_JUDGED_Q = """
SELECT DISTINCT ?subject ?property ?stateAs ?state WHERE {
  ?obs sensing:judged ?state ; sosa:observedProperty ?property ;
       sosa:hasFeatureOfInterest/(sosa:isSampleOf)? ?subject .
  ?subject ssn-system:hasOperatingRange/ssn-system:inCondition/ssn:forProperty ?property .
  ?property sensing:stateAs ?stateAs .
  FILTER EXISTS { ?property sensing:belowAs|sensing:insideAs|sensing:aboveAs ?state } }
ORDER BY ?subject ?property"""

#  THE KEY'S SUBJECT BELIEF BEFORE: every graph of the kind saying the subject's state in the
#  property's word, found by its content, with when it began and the state it holds.
_HELD_Q = """
SELECT ?g ?start ?before WHERE {
  GRAPH $cat { ?g a sensing:SubjectBeliefGraph OPTIONAL { ?g dcterms:temporal/orexis:start ?start } }
  GRAPH ?g { $subject $stateAs ?before } }"""


def believe(store, me: str, graph: str) -> list[str]:
    """Write the subject belief of each subject the observation `graph` was judged of — its state in its
    domain's words, holding over the observation's period — replacing the key's
    subject belief before it whole. The graphs written: none where `graph` is no observation, was
    judged of nothing, or a later observation of the key is believed already.

    `me` is who holds it — the one identifier a process is handed — and is written as the graph's owner.
    """
    cat = catalogue_of(store)
    observed = next(iter(rows(store, _OBSERVATION_Q, (), cat=Raw(f"<{cat}>"), graph=graph)), None)
    if observed is None or not observed.get("start"):
        return []
    starts = datetime.fromisoformat(observed["start"])
    read = [ox.NamedNode(g) for g in (graph, *revisions_of(store, graph), *graphs_of(store, PUBLIC))]
    judged: dict[tuple, list] = {}
    for r in store.query(_JUDGED_Q, prefixes=NAMESPACES, default_graph=read):
        judged.setdefault((r["subject"], r["property"]), []).append(r)
    written = []
    for (subject, observed_property), found in judged.items():
        if len({(r["stateAs"], r["state"]) for r in found}) != 1:
            #  TWO STATES FOR ONE SUBJECT: a feature and what it is a sample of each stating an operating
            #  range for the property, so the observation's judgments cannot be told apart. No world does.
            log.error("%s: %s was judged %s for %s at once; no subject belief is written of it",
                      local_of(me), local_of(subject.value), ", ".join(sorted(local_of(r["state"].value) for r in found)),
                      local_of(observed_property.value))
            continue
        r = found[0]
        held = rows(store, _HELD_Q, (), cat=Raw(f"<{cat}>"), subject=subject.value, stateAs=r["stateAs"].value)
        if any(h.get("start") and datetime.fromisoformat(h["start"]) > starts for h in held):
            log.debug("%s: %s is believed of a later observation than %s; nothing written", local_of(me),
                      local_of(subject.value), graph)
            continue
        for h in held:
            forget_graph(store, h["g"])
        into = subject_belief_graph(local_of(me), subject.value, observed_property.value)
        named = ox.NamedNode(into)
        store.extend([ox.Quad(subject, r["stateAs"], r["state"], named)])
        update(store, f"INSERT DATA {{ {entry(store, into, SUBJECT_BELIEF_GRAPH, DERIVED, me, observed['start'], observed.get('end'))} }}")
        before = {h["before"] for h in held}
        (log.info if before != {r["state"].value} else log.debug)(
            "%s: %s believed %s of %s", local_of(me), local_of(subject.value), local_of(r["state"].value),
            local_of(observed_property.value))
        written.append(into)
    return written
