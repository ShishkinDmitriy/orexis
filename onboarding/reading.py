"""The world as onboarding reads it: what an agent reads of it, and then the kinds no agent does.

**A document's kind says who reads it, and every reader loads only the kinds it reads**
(knowledge/decisions/a-documents-kind-says-who-reads-it.md). An agent's boot passes over a graph
whose kind its T-Box does not declare. Onboarding's own kinds — the hardware `orexis-firmware`
interpolates into a board's config.h, and the deployment — are declared in `ontology.ttl` beside
this module and outside `agent/`, so no agent's vocabulary can say what they are and the import
direction holds: onboarding may import the agent, never the reverse.

So onboarding does not borrow the agent's boot whole, which is what once made the hardware public
to every agent: `world` reads the world as an agent does (`agent.runtime.world_of`), then its own
vocabulary, then every graph in the world's directory of a kind that vocabulary declares.

**A kind no reader declares is refused here, because nowhere else can.** Passing over an unknown
kind makes a misspelled one silent in every reader; onboarding knows every reader's vocabulary, so
`unread` names the graphs none of them reads, and `orexis-onboard` refuses a world that has any.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

from agent.runtime import documents, known, read_with_imports, world_of
from agent.store import close_catalogue, closed, document, kinds_in, put_document

from .worlds import DOCUMENTS

VOCABULARY = Path(__file__).resolve().parent / "ontology.ttl"
ONBOARDING = "http://example.org/orexis/onboarding#"
HARDWARE = ONBOARDING + "HardwareGraph"
DEPLOYMENT = ONBOARDING + "DeploymentGraph"

_CLASS = ox.NamedNode("http://www.w3.org/2002/07/owl#Class")
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def _files(world: Path) -> list[Path]:
    return sorted(p for p in world.iterdir() if p.is_file() and p.suffix in DOCUMENTS)


def world(here: Path) -> ox.Store:
    """The world in `here` as onboarding reads it: its public graphs as an agent reads them, and
    every graph in its directory whose kind onboarding's vocabulary declares, closed."""
    here = Path(here).resolve()
    store = world_of(here)
    vocabulary = document(VOCABULARY)
    put_document(store, vocabulary)
    ours = {q.subject.value for q in vocabulary.quads_for_pattern(None, _TYPE, _CLASS, None)}
    for path in _files(here):
        doc = document(path)
        graphs = {g for g, kinds in kinds_in(doc).items() if any(ours & set(closed(store, k)) for k in kinds)}
        if graphs:
            put_document(store, doc, graphs=graphs)
    close_catalogue(store)
    return store


def unread(here: Path) -> list[str]:
    """Every graph the world in `here` holds — in its directory, in every agent's own documents
    under `beliefs/`, and in whatever they import — whose kind no reader declares, as
    `document: graph (kinds)`. Empty for a world every one of whose graphs somebody reads."""
    here = Path(here).resolve()
    store = world(here)
    beliefs = sorted(p for p in (here / "beliefs").glob("*") if p.suffix in DOCUMENTS)
    out = []
    for path, doc in read_with_imports([*documents(here), *beliefs]):
        for graph, kinds in sorted(kinds_in(doc).items()):
            if not known(store, kinds):
                out.append(f"{path.name}: {graph} ({', '.join(sorted(kinds))})")
    return out
