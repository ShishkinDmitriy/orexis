"""The speech package's own words, and the name it spells for eyes.

WHAT IS SAID AND WHAT IS BELIEVED OF IT ARE TWO GRAPHS. An utterance is kept as it was said, in a kind
no reader of the mind is handed; what the agent believes of it is what the extractions it holds
conclude, a belief graph derived from the utterance (`ontology.ttl` beside this file,
knowledge/domain/speech/utterance.md).

THE NAME IS FOR EYES. What was believed of an utterance is spelled from the utterance's own name; every
reader asks the catalogue by class, and renaming it here would change nothing a reader sees.
"""

from __future__ import annotations

SPEECH = "http://example.org/orexis/speech#"

UTTERANCE_GRAPH = SPEECH + "UtteranceGraph"
EXTRACTION = SPEECH + "Extraction"


def believed_graph(utterance: str) -> str:
    """Where what the extractions conclude of `utterance` is kept: a belief derived from it."""
    return utterance.rstrip("/") + "/believed"
