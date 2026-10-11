"""`utterances`: a document as what was said — every graph an utterance, a kind it said kept only where it
is a kind of utterance, and every other row it states of its graph kept as said."""

from __future__ import annotations

import pyoxigraph as ox

from agent.ontology import ACTION, CATALOGUE_GRAPH
from agent.speech.ontology import UTTERANCE_GRAPH as UTTERANCE
from agent.speech.utterances import utterances
from agent.store import update

T = "http://example.org/test#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def test_a_kind_of_utterance_is_kept_and_any_other_is_not_and_the_period_stays():
    vocabulary = ox.Store()
    update(vocabulary, f"""INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph . <{T}vocabulary> a orexis:OntologyGraph . }}
  GRAPH <{T}vocabulary> {{ <{T}RoundGraph> rdfs:subClassOf <{UTTERANCE}> , orexis:Graph . }} }}""")
    doc = ox.Store()
    doc.load(f"""<{T}round> {{ <{T}round> <{T}lot> 40 }}
<{T}tool> {{ <{T}tool> <{T}does> "anything" }}
<{T}round> a <{T}RoundGraph> ; <http://purl.org/dc/terms/temporal> [ <{T}until> "noon" ] .
<{T}tool> a <{ACTION}> .""".encode(), format=ox.RdfFormat.TRIG)
    out = utterances(vocabulary, doc)
    kinds = {(q.subject.value, q.object.value) for q in out.quads_for_pattern(None, _TYPE, None, ox.DefaultGraph())}
    assert kinds == {(T + "round", T + "RoundGraph"), (T + "round", UTTERANCE), (T + "tool", UTTERANCE)}
    assert len(list(out.quads_for_pattern(None, ox.NamedNode(T + "until"), None, ox.DefaultGraph()))) == 1, "its period"
    assert len(list(out.quads_for_pattern(None, None, None, ox.NamedNode(T + "tool")))) == 1, "what it said, kept"
